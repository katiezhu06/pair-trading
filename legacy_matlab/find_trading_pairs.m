% find_trading_pairs
%
% DESCRIPTION:
%
%   This script will go through a list of stock tickers and apply the 
%   trade_pairs2 function to check for tradeability   
%

tic,

filename = 'sp500.xls';

[num, data_full] = xlsread(filename);

% select sector
inds = find( strcmp(data_full(:,4),'Financials'));
data = data_full(inds,:);

[len, rows] = size(data);

nstocks = len;
levels  = [1 5 10 90 95 99]';
lookback= 20;
MEDIAN  = 1;
delta   = 2;
abort   = 25;
P       = ones(nstocks,nstocks,7);



for s1=1:(nstocks-1),
    for s2= (s1+1):nstocks,
        
        disp(['Comparing stocks ',num2str(s1),' and ',num2str(s2)]);
        stockA = char( data(s1,1) );
        stockB = char( data(s2,1) );
        
        
        [CAGR, sharpe, max_dd, max_ddd, n_trades, success, mean_adf] = ...
            trade_pair_v2(stockA, stockB, lookback, MEDIAN, delta, abort);
        
        P(s1, s2, 1) = CAGR;
        P(s1, s2, 2) = sharpe;
        P(s1, s2, 3) = max_dd;
        P(s1, s2, 4) = max_ddd;
        P(s1, s2, 5) = n_trades;
        P(s1, s2, 6) = success;
        P(s1, s2, 7) = mean_adf;
        


        
    end     % s2 loop
end         % s1 loop
        
toc        
        
