function varargout = my_pairs(series2, M, N, cadence, spread, scaling, cost)

% my_pairs
%
% Function my_pairs is a direct copy of pairs.m from the matlab webinar,
% but adapted very slightly to work with my_cadf insted of egcitest.
%
% J. Bortnik, 7/29/2012
% 
%
% ORIGINAL COMMENTS:
% PAIRS returns a trading signal for a simple pairs trading strategy



%%
% Copyright 2010, The MathWorks, Inc.
% All rights reserved.

%% Process input args
if ~exist('scaling','var')
    scaling = 1;
end

if ~exist('cost','var')
    cost = 0;
end

if ~exist('spread', 'var')
    spread = 1;
end

if ~exist('cadence','var')
    cadence = 390;  % cadence of observations in minutes
end

if nargin == 1
    % default values
    M = 420;
    N = 60;
elseif nargin == 2
    error('The rebalancing period must also be defined')
end



%% Sweep across the entire time series
% Every N periods, we use the previous M periods' worth of information to
% estimate the cointegrating relationship (if it exists).
%
% We then use this estimated relationship to identify trading opportunities
% until the next rebalancing date.

s = zeros(size(series2));
indicate = zeros(length(series2),1);

for i = max(M,N) : N : length(s)-N
    % Calibrate cointegration model by looking back.
    %[h,~,~,~,reg1] = egcitest(series2(i-M+1:i, :));
    ind1    = i-M+1;
    ind2    = i;
    results     = my_cadf(series2(ind1:ind2,1),series2(ind1:ind2,2),0,1); 
    
    
    if results.adf_level < 10,
        % Only engage in trading if we reject the null hypothesis that no
        % cointegrating relationship exists.
        
        % The strategy:
        % 1. Compute residuals over next N days
        res = series2(i:i+N-1, 1) ...
            - (results.P(2) + results.P(1).*series2(i:i+N-1, 2));
        
        % 2. If the residuals are large and positive, then the first series
        % is likely to decline vs. the second series.  Short the first
        % series by a scaled number of shares and long the second series by
        % 1 share.  If the residuals are large and negative, do the
        % opposite.
        indicate(i:i+N-1) = res/results.RMSE;
        
        s(i:i+N-1, 2) = (res/results.RMSE > spread) ...
            - (res/results.RMSE < -spread);
        s(i:i+N-1, 1) = -results.P(1) .* s(i:i+N-1, 2);
    end
end

%% Calculate performance statistics

r  = sum([0 0; s(1:end-1, :) .* diff(series2) - abs(diff(s))*cost/2] ,2);
%sh = scaling*sharpe(r,0); 

% sharpe ratio (risk-free rate=0 for $ neutral strategy)
%daily_return = (r(2:end)-r(1:(end-1)))./r(1:(end-1));
daily_return = r;
minute_scaling = 390/cadence; % this is 3-minute data
sh = sqrt(252*minute_scaling)*mean(daily_return)/std(daily_return);


if nargout == 0
    %% Plot results
    ax(1) = subplot(3,1,1);
    plot(series2), grid on
    legend('LCO','WTI')
    title(['Pairs trading results, Sharpe Ratio = ',num2str(sh,3)])
    ylabel('Price (USD)')
    
    ax(2) = subplot(3,1,2);
    plot([indicate,spread*ones(size(indicate)),-spread*ones(size(indicate))])
    grid on
    legend(['Indicator'],'LCO: Over bought','LCO: Over sold',...
        'Location','NorthWest')
    title(['Pairs indicator: rebalance every ' num2str(N)...
        ' minutes with previous ' num2str(M) ' minutes'' prices.'])
    ylabel('Indicator')
    
    ax(3) = subplot(3,1,3);
    plot([s,cumsum(r)]), grid on
    legend('Position for LCO','Position for WTI','Cumulative Return',...
        'Location', 'NorthWest')
    title(['Final Return = ',num2str(sum(r),3),' (',num2str(sum(r)/mean(series2(1,:))*100,3),'%)'])
    ylabel('Return (USD)')
    xlabel('Serial time number')
    linkaxes(ax,'x')
else
    %% Return values
    for i = 1:nargout
        switch i
            case 1
                varargout{1} = s; % signal
            case 2
                varargout{2} = sum(r)/mean(series2(:,1))*100; % return (pnl)
            case 3
                varargout{3} = sh; % sharpe ratio
            case 4
                varargout{4} = indicate; % indicator
            otherwise
                warning('PAIRS:OutputArg',...
                    'Too many output arguments requested, ignoring last ones');
        end 
    end
end