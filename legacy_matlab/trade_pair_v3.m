function [CAGR, sharpe, max_dd, max_ddd, trades, success, mean_adf]=...
    trade_pair_v3(stockA, stockB, lookback, MEDIAN, delta, abort)

% function [CAGR, sharpe, max_dd, max_ddd, n_trades, success, mean_adf]=...
%    trade_pair_v3(stockA, stockB, lookback, MEDIAN, delta, abort)
%
% DESCRIPTION
%   
%   trade_pair_v3 is a function that takes 2 stocks, fetches the price data
%   if it is not already downloaded, and pair-trades them using a lookback
%   period and a certain delta. In v3 we try to include a few extra 'bells 
%   and whistles' to try and improve our success rate.
%
% INOUTS:
%
%   stockA:     ticker symbol for first stock, e.g., 'aapl'
%   stockB:     ticker symbol for second stock, e.g., 'msft'
%   lookback:   loockback period in days, e.g., 20
%   MEDIAN:     either 1 or 0. If 1, use median filter of r to get rs over
%               the lookback period.
%   delta:      the number of standard deviations away from mean to enter
%               the trade, e.g., 2
%   abort:      the number of standard deviations away from the mean to
%               exit the trade in an emergency, e.g., 4.
%
% OUTPUTS:
%
%   CAGR:       Cumulative Annual Growth Rate
%   sharpe:     Sharpe ratio
%   max_dd:     maximum drawdown (as a fraction, not percent)
%   max_ddd:    maximum drawdown duration (in days)
%   trades:     list of trades made in the trading period
%   success:    percentage of successful (profitable) trades
%   mea_adf:    mean value of the augmented dickey fuller test averaged
%               over all lookback periods.
%
%
% NOTES
%
%   trade_pair_v2 differs from trade_pair in that the coding is a bit
%   simpler, the variables are all the same length (unlike trade_pair) such
%   as the ratio r, smoothed ratio rs,residual resid, etc. There is also an
%   abort condition built in to exit the pair if it deviates too much.
%
%   Written, J. Bortnik., June 24-25, 2012






PLOTIT  = 1;
capital0 = 10000;   % starting capital
commission = 5;     % cost per trade
slippage = 0.01/100; % fraction of price lost due to bid-ask spread
levels  = [1 5 10 90 95 99]';
min_len = 252/2;  % minimum length of common time period


[day_num, A, B] = compare_hist_prices(stockA, stockB);
len = length(A);

% initialize
CAGR=0; sharpe=0; max_dd=0; max_ddd=0; n_trades=0; success=0; mean_adf=0;
if len<min_len,
    return;
end
t = 1:len;


% define arrays
r       = zeros(len,1);
rs      = zeros(len,1);     % smoothed ratio of stock prices
resid   = zeros(len,1);     % residual:  ratio - smoothed_ratio
stdv    = zeros(len,1);     % standard deviation of residual
capital = ones(len,1)*capital0;     % accumulated profit/loss
buysell = zeros(len,1);     % the buy or sell signal
adf_level = zeros(len,1);   % the buy or sell signal
corr_f  = zeros(len,1);     % fast correlation coefficient (lookback period)
dcorr_f = zeros(len,1);     % difference in correlation coefficient
corr_s  = zeros(len,1);     % slow correlation coefficient (2xlookback)
trades  = [];

% calculate RSI's: prepend with the initial value
rsi_A = calc_RSI(A, lookback);
rsi_A = [ ones(lookback,1)*rsi_A(1) ; rsi_A' ];
rsi_B = calc_RSI(B, lookback);
rsi_B = [ ones(lookback,1)*rsi_B(1) ; rsi_B' ];



for si=1:len,
    
    r(si) = A(si)/B(si);    % ratio
    
    
    % Calculate smoothed ratio
    if si>(lookback+0.5),   % add .5 just to be certain
        ind1= si-lookback;
        ind2= si-1;
        
        % Test for coint
        results1 = cadf(A(ind1:ind2),B(ind1:ind2),0,3);
        adf_level(si) = interp1( results1.crit, levels, results1.adf, ...
            'pchip','extrap');
        
        
    else,
        ind1= 1;
        ind2= si;
    end

    if MEDIAN,
        rs(si) = median( r(ind1:ind2) );
        med_title = ['Ratio: ',num2str(lookback),' day median smoothing'];
    else
        rs(si) = mean( r(ind1:ind2) );
        med_title = ['Ratio: ',num2str(lookback),' day mean smoothing'];
    end
    
    
    % calculate residual
    resid(si) = r(si) - rs(si);
    
    % calculate correlation coefficient
    % fast
    corr_f(si) = corr(A(ind1:ind2),B(ind1:ind2),'type','spearman');
    % slow
    if si>(2*lookback+0.5),
        corr_s(si) = corr(A(ind1-lookback:ind2),B(ind1-lookback:ind2), ...
            'type','spearman');
    end
    if si>2,
        dcorr_f(si)= corr_f(si) - corr_f(si-1);
    end


    % calculate smoothed standard deviation
    if MEDIAN,
        stdv(si) = sqrt(median( resid(ind1:ind2).^2 ));
    else
        stdv(si) = sqrt(mean( resid(ind1:ind2).^2 ));    
    end
    
    
end % si=1:len
    
    

% Zero crossing rate
zero_crosses = length((find( (resid(1:(end-1)).*resid(2:end))<=0 )));
average_hold = len/zero_crosses;
zero_cross_rate = zero_crosses/len*100; 
    
    
    
% ---------------------------------------------------------------------        
%
%                               TRADE PAIRS
%
% ---------------------------------------------------------------------        

% begin trading only after lookback days
start_day = 1;

for ti=lookback+1:len,
    

    
    
    % ENTER TRANSACTION ---------------
    %
    if buysell(ti-1)==0,        
        
        capital(ti) = capital(ti-1);
        
        % determine number of shares of A and B now
        numA = floor(capital(ti-1)/A(ti));
        numB = floor(capital(ti-1)/B(ti));
        
        
        % Coint
        this_adf= adf_level(ti);
        
        % BUY
        if resid(ti)<-delta*stdv(ti) & resid(ti)>-abort*stdv(ti),

            buysell(ti) = 1;
            this_stdv = stdv(ti);
            this_Drsi = rsi_B(ti) - rsi_A(ti);
            this_corr_f = corr_f(ti);
            this_corr_s = corr_s(ti);
            this_dcorr_f= dcorr_f(ti);
            
            
            % sell B, get money in
            sellB = numB*B(ti)-commission-slippage*B(ti);
            
            % buy A, take money out
            buyA = -numA*A(ti)-commission-slippage*A(ti);
            
            capital(ti) = capital(ti-1) + sellB + buyA;
            start_day = ti;
            
        end


        % SELL
        if resid(ti)>delta*stdv(ti) & resid(ti)<abort*stdv(ti),

            buysell(ti) = -1;
            this_stdv = stdv(ti);
            this_Drsi = rsi_A(ti) - rsi_B(ti); 
            this_corr_f = corr_f(ti);
            this_corr_s = corr_s(ti);
            this_dcorr_f= dcorr_f(ti);
            
            % sell A, get money in
            sellA = numA*A(ti)-commission-slippage*A(ti);
            
            % buy B, take money out
            buyB = -numB*B(ti)-commission-slippage*B(ti);
            
            capital(ti) = capital(ti-1) + sellA + buyB;           
            sstart_day = ti;

        end
        
    
    end     % if buysell==0
        
    
        
    % EXIT TRANSACTION ------------------
    %
    % SELL
    if buysell(ti-1)>0.5,
        
        if resid(ti)>0 | resid(ti)<-abort*this_stdv | ti==len,
            buysell(ti) = 0;
            
            % sell A, get money in
            sellA = numA*A(ti)-commission-slippage*A(ti);
            
            % buy B, take money out
            buyB = -numB*B(ti)-commission-slippage*B(ti);
            
            
            capital(ti) = capital(ti-1) + sellA + buyB;
            stop_day = ti;
            profit = capital(stop_day)-capital(start_day);
            profit_percent = profit/capital(start_day)*100;
            trades= [trades; [start_day stop_day profit profit_percent ... 
                this_adf this_Drsi this_corr_f this_corr_s this_dcorr_f]];
            
        else
            buysell(ti) = buysell(ti-1);
            capital(ti) = capital(ti-1);
        end
        
    end
    
    
    % BUY
    if buysell(ti-1)<-0.5,
        
        if resid(ti)<0 | resid>abort*this_stdv | ti==len,
            buysell(ti) = 0;
            
            % sell B, get money in
            sellB = numB*B(ti)-commission-slippage*B(ti);
            
            % buy A, take money out
            buyA = -numA*A(ti)-commission-slippage*A(ti);
            
            capital(ti) = capital(ti-1) + sellB + buyA;
            stop_day = ti;
            profit = capital(stop_day)-capital(start_day);
            profit_percent = profit/capital(start_day)*100;
            trades= [trades; [start_day stop_day profit profit_percent ...
                this_adf this_Drsi this_corr_f this_corr_s this_dcorr_f]];

        else
            buysell(ti) = buysell(ti-1);
            capital(ti) = capital(ti-1);
        end
        
    end 
           
    
end




% ---------------------------------------------------------------------        
%
%                               METRICS
%
% ---------------------------------------------------------------------   


% Cumulative annual growth rate
CAGR = ((capital(ti)/capital(1))^(252/len)-1)*100;


% sharpe ratio (risk-free rate=0 for $ neutral strategy)
daily_return = (capital(2:end)-capital(1:(end-1)))./capital(1:(end-1));
sharpe = sqrt(252)*mean(daily_return)/std(daily_return);


% max_dd and max_ddd
cum_ret = cumprod(1+daily_return)-1;
highwatermark   = zeros(size(cum_ret));
drawdown        = zeros(size(cum_ret));
drawdownduration= zeros(size(cum_ret));

for ddi = 2:length(cum_ret),
    highwatermark(ddi)=max( highwatermark(ddi-1), cum_ret(ddi));
    drawdown(ddi) = (1+highwatermark(ddi))/(1+cum_ret(ddi))-1;
    if drawdown(ddi)==0,
        drawdownduration(ddi)=0;
    else
        drawdownduration(ddi)=drawdownduration(ddi-1)+1;
    end
end

max_dd = max(drawdown);
max_ddd = max(drawdownduration);


% winning trades
wins =  trades(  find(trades(:,4)>0)  , : );
n_wins = size(wins,1);

% losing trades
losses = trades(  find(trades(:,4)<=0)  , : );
n_losses = size(losses,1);

% ratio win/lose
win_to_loss = n_wins/n_losses;

% success rate
n_trades = n_wins+n_losses;
success = n_wins/n_trades*100;

% average $ in winnings
ave_win = mean( wins(:,3) );

% ave $ in loss
ave_loss = mean( losses(:,3) );

% mean augmented dickey fuller test results
mean_adf = mean(adf_level);

% implement: 
% - a failsafe level to exit trade
% - exit after n days if still hasn't converged
% - try to predict right level to exit?



disp( [num2str(ti),' days, CAGR: ',num2str(CAGR),...
    ' capital: ',num2str(capital(ti))] )



% ---------------------------------------------------------------------        
%
%                               PLOTTING
%
% ---------------------------------------------------------------------   
if PLOTIT,

figure, 

subplot(2,2,1)
title('Prices')
plot(day_num, A, day_num, B)


subplot(2,2,2)
plot(t, r);
title(med_title)
hold on, plot(t, rs, 'r')


subplot(2,2,3)
plot(t, resid), grid on
hold on
plot(t, delta*stdv,'r')
plot(t, -delta*stdv,'r')
plot(t, buysell, 'm');
title(['Zero crossing rate: ',num2str(zero_cross_rate)])

subplot(2,2,4)
plot(t, capital)
hold on
%plot(t, buysell*1000+capital0, 'r')
title('Equity curve')


end % IF PLOTIT

return;






 
 
 