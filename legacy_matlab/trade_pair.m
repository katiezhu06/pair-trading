function [blah] = trade_pair(stockA, stockB, lookback, MEDIAN, delta)

% function [blah] = trade_pair(stockA, stockB, lookback, delta)

capital0 = 10000; % starting capital


[day_num, A, B] = compare_hist_prices(stockA, stockB);
len = length(A);
t = 1:len;

r = A./B;


% subscript s is 'smoothed'
ts = t(lookback+1:len);
rs = zeros( (len-lookback), 1);
lens = length(rs);

for si=1:lens,

 ind1 = si;
 ind2 = si+lookback-1;
 if MEDIAN,
     rs(si) = median( r(ind1:ind2) );
     med_tit = ['Ratio: ',num2str(lookback),' day median smoothing'];
 else
     rs(si) = mean( r(ind1:ind2) );
     med_tit = ['Ratio: ',num2str(lookback),' day mean smoothing'];

 end

end

resid = r(lookback+1:end)-rs;

zero_crosses = length((find( (resid(1:(end-1)).*resid(2:end))<=0 )));
zero_cross_rate = zero_crosses/lens*100; 


% ------------------------
%
% TRADE!!!
%
% we need to get a dynamic estimate of the std dev.  So we can only start
% trading 2 lookback periods after start.
tt = t(2*lookback+1:end);
stdv = zeros( len-2*lookback, 1); % standard deviation of r
lent = length(stdv);

capital = zeros(lent,1);
capital(1) = capital0; % set to initial capital


BUY = [];
SELL= [];

for ti=1:lent,

 % Calculate standard deviation of residual   
 ind1 = ti;
 ind2 = ti+lookback-1;
 if MEDIAN,
     stdv(ti) = sqrt(median( resid(ind1:ind2).^2 ));
 else
     stdv(ti) = sqrt(mean( resid(ind1:ind2).^2 ));
 end

 % change variables to avoid confusion
 this_A = A(ti+2*lookback);
 this_B = B(ti+2*lookback);
 this_r = r(ti+2*lookback);
 this_rs= rs(ti+lookback);
 this_resid = resid(ti+lookback);
 this_stdv = stdv(ti);
 
 % BUY signal
 if this_resid < (-delta*this_stdv),
     
     BUY = [BUY ti];
 
 end

 % SELL signal
 if this_resid > (delta*this_stdv),
     
    SELL = [SELL ti];
    
 end
 
end % if ti=1:lent


 
 
 % PLOTTING
  figure, 
  subplot(2,2,1)
  title('Prices')
  plot(day_num, A, day_num, B)
 
  subplot(2,2,2)
  plot(t, r);
  title(med_tit)
  hold on, plot(t(lookback+1:end), rs, 'r')
  
 subplot(2,2,3)
 plot(ts, resid), grid on
 hold on
 plot(ts(lookback+1:end), delta*stdv,'r')
 plot(ts(lookback+1:end), -delta*stdv,'r')
 
 plot(BUY+2*lookback, resid(BUY+lookback), 'kd');
 plot(SELL+2*lookback, resid(SELL+lookback), 'ms');

 title(['Zero crossing rate: ',num2str(zero_cross_rate)])
 
 
 
 
 
 