from __future__ import annotations

import csv
from datetime import date
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen
import pandas as pd


SP500_CSV_URL = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"

# Long-only, unleveraged, liquid families with economically comparable exposures.
ETF_GROUPS: dict[str, list[tuple[str, str]]] = {
    "US Large Cap": [("SPY", "SPDR S&P 500 ETF Trust"), ("IVV", "iShares Core S&P 500 ETF"), ("VOO", "Vanguard S&P 500 ETF"), ("SPYM", "State Street SPDR Portfolio S&P 500 ETF")],
    "US Total Market": [("VTI", "Vanguard Total Stock Market ETF"), ("ITOT", "iShares Core S&P Total US Stock Market ETF"), ("SCHB", "Schwab US Broad Market ETF"), ("SPTM", "SPDR Portfolio S&P 1500 Composite Stock Market ETF")],
    "US Large Growth": [("VUG", "Vanguard Growth ETF"), ("IWF", "iShares Russell 1000 Growth ETF"), ("SCHG", "Schwab US Large-Cap Growth ETF"), ("SPYG", "SPDR Portfolio S&P 500 Growth ETF")],
    "US Large Value": [("VTV", "Vanguard Value ETF"), ("IWD", "iShares Russell 1000 Value ETF"), ("SCHV", "Schwab US Large-Cap Value ETF"), ("SPYV", "SPDR Portfolio S&P 500 Value ETF")],
    "US Mid Cap": [("IJH", "iShares Core S&P Mid-Cap ETF"), ("VO", "Vanguard Mid-Cap ETF"), ("MDY", "SPDR S&P MidCap 400 ETF Trust")],
    "US Small Cap": [("IWM", "iShares Russell 2000 ETF"), ("IJR", "iShares Core S&P Small-Cap ETF"), ("VB", "Vanguard Small-Cap ETF"), ("SCHA", "Schwab US Small-Cap ETF")],
    "Developed ex-US": [("EFA", "iShares MSCI EAFE ETF"), ("VEA", "Vanguard FTSE Developed Markets ETF"), ("IEFA", "iShares Core MSCI EAFE ETF"), ("SCHF", "Schwab International Equity ETF")],
    "Emerging Markets": [("EEM", "iShares MSCI Emerging Markets ETF"), ("VWO", "Vanguard FTSE Emerging Markets ETF"), ("IEMG", "iShares Core MSCI Emerging Markets ETF"), ("SPEM", "SPDR Portfolio Emerging Markets ETF")],
    "Global ex-US": [("VXUS", "Vanguard Total International Stock ETF"), ("IXUS", "iShares Core MSCI Total International Stock ETF")],
    "Technology Sector": [("XLK", "Technology Select Sector SPDR Fund"), ("VGT", "Vanguard Information Technology ETF"), ("IYW", "iShares US Technology ETF"), ("FTEC", "Fidelity MSCI Information Technology Index ETF")],
    "Financial Sector": [("XLF", "Financial Select Sector SPDR Fund"), ("VFH", "Vanguard Financials ETF"), ("IYF", "iShares US Financials ETF"), ("FNCL", "Fidelity MSCI Financials Index ETF")],
    "Health Care Sector": [("XLV", "Health Care Select Sector SPDR Fund"), ("VHT", "Vanguard Health Care ETF"), ("IYH", "iShares US Healthcare ETF"), ("FHLC", "Fidelity MSCI Health Care Index ETF")],
    "Energy Sector": [("XLE", "Energy Select Sector SPDR Fund"), ("VDE", "Vanguard Energy ETF"), ("IYE", "iShares US Energy ETF"), ("FENY", "Fidelity MSCI Energy Index ETF")],
    "Industrials Sector": [("XLI", "Industrial Select Sector SPDR Fund"), ("VIS", "Vanguard Industrials ETF"), ("IYJ", "iShares US Industrials ETF"), ("FIDU", "Fidelity MSCI Industrials Index ETF")],
    "Consumer Staples Sector": [("XLP", "Consumer Staples Select Sector SPDR Fund"), ("VDC", "Vanguard Consumer Staples ETF"), ("IYK", "iShares US Consumer Staples ETF"), ("FSTA", "Fidelity MSCI Consumer Staples Index ETF")],
    "Consumer Discretionary Sector": [("XLY", "Consumer Discretionary Select Sector SPDR Fund"), ("VCR", "Vanguard Consumer Discretionary ETF"), ("IYC", "iShares US Consumer Discretionary ETF"), ("FDIS", "Fidelity MSCI Consumer Discretionary Index ETF")],
    "Utilities Sector": [("XLU", "Utilities Select Sector SPDR Fund"), ("VPU", "Vanguard Utilities ETF"), ("IDU", "iShares US Utilities ETF"), ("FUTY", "Fidelity MSCI Utilities Index ETF")],
    "Materials Sector": [("XLB", "Materials Select Sector SPDR Fund"), ("VAW", "Vanguard Materials ETF"), ("IYM", "iShares US Basic Materials ETF"), ("FMAT", "Fidelity MSCI Materials Index ETF")],
    "Communication Services Sector": [("XLC", "Communication Services Select Sector SPDR Fund"), ("VOX", "Vanguard Communication Services ETF"), ("IYZ", "iShares US Telecommunications ETF"), ("FCOM", "Fidelity MSCI Communication Services Index ETF")],
    "US Real Estate": [("VNQ", "Vanguard Real Estate ETF"), ("SCHH", "Schwab US REIT ETF"), ("IYR", "iShares US Real Estate ETF"), ("USRT", "iShares Core US REIT ETF")],
    "Semiconductors": [("SOXX", "iShares Semiconductor ETF"), ("SMH", "VanEck Semiconductor ETF"), ("XSD", "SPDR S&P Semiconductor ETF")],
    "Biotechnology": [("IBB", "iShares Biotechnology ETF"), ("XBI", "SPDR S&P Biotech ETF")],
    "Gold": [("GLD", "SPDR Gold Shares"), ("IAU", "iShares Gold Trust"), ("GLDM", "SPDR Gold MiniShares Trust"), ("SGOL", "abrdn Physical Gold Shares ETF")],
    "Silver": [("SLV", "iShares Silver Trust"), ("SIVR", "abrdn Physical Silver Shares ETF")],
    "US Aggregate Bonds": [("AGG", "iShares Core US Aggregate Bond ETF"), ("BND", "Vanguard Total Bond Market ETF"), ("SCHZ", "Schwab US Aggregate Bond ETF")],
    "Long US Treasury": [("TLT", "iShares 20+ Year Treasury Bond ETF"), ("VGLT", "Vanguard Long-Term Treasury ETF"), ("SPTL", "SPDR Portfolio Long Term Treasury ETF")],
    "Intermediate US Treasury": [("IEF", "iShares 7-10 Year Treasury Bond ETF"), ("VGIT", "Vanguard Intermediate-Term Treasury ETF"), ("SCHR", "Schwab Intermediate-Term US Treasury ETF")],
    "Short US Treasury": [("SHY", "iShares 1-3 Year Treasury Bond ETF"), ("VGSH", "Vanguard Short-Term Treasury ETF"), ("SCHO", "Schwab Short-Term US Treasury ETF")],
    "US TIPS": [("TIP", "iShares TIPS Bond ETF"), ("SCHP", "Schwab US TIPS ETF")],
    "US High Yield Bonds": [("HYG", "iShares iBoxx High Yield Corporate Bond ETF"), ("JNK", "SPDR Bloomberg High Yield Bond ETF"), ("USHY", "iShares Broad USD High Yield Corporate Bond ETF")],
}


def fetch_sp500() -> pd.DataFrame:
    request = Request(SP500_CSV_URL, headers={"User-Agent": "pairs-scanner/1.0 research"})
    with urlopen(request, timeout=45) as response:
        text = response.read().decode("utf-8-sig")
    records = list(csv.DictReader(io.StringIO(text)))
    rows = []
    for record in records:
        # Yahoo uses dashes for class shares (BRK-B, BF-B).
        symbol = record["Symbol"].replace(".", "-")
        rows.append(
            {
                "symbol": symbol,
                "name": record["Security"],
                "asset_type": "STK",
                "group": record["GICS Sub-Industry"],
                "broad_group": record["GICS Sector"],
                "shortable": True,
                "source": "S&P 500 constituents dataset",
            }
        )
    return pd.DataFrame(rows)


def etf_universe() -> pd.DataFrame:
    rows = []
    for group, funds in ETF_GROUPS.items():
        for symbol, name in funds:
            rows.append(
                {
                    "symbol": symbol,
                    "name": name,
                    "asset_type": "ETF",
                    "group": group,
                    "broad_group": "ETF",
                    "shortable": True,
                    "source": "curated unleveraged ETF families",
                }
            )
    return pd.DataFrame(rows)


def build_universe(output: str | Path) -> tuple[pd.DataFrame, Path]:
    stocks = fetch_sp500()
    etfs = etf_universe()
    frame = pd.concat([stocks, etfs], ignore_index=True).drop_duplicates("symbol", keep="last")
    frame = frame.sort_values(["asset_type", "group", "symbol"])
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False)
    metadata = destination.with_suffix(".metadata.json")
    metadata.write_text(
        json.dumps(
            {
                "generated_on": date.today().isoformat(),
                "stock_source": SP500_CSV_URL,
                "stock_count": int((frame.asset_type == "STK").sum()),
                "etf_count": int((frame.asset_type == "ETF").sum()),
                "note": "Shortable is a research-universe placeholder; verify live borrow before any trade.",
            }, indent=2
        ) + "\n"
    )
    return frame, metadata

