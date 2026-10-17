
function [intersec, priceA, priceB] = ...
    compare_hist_prices(tickerA, tickerB, npoints)

% function [dates, priceA, priceB] = compare_hist_prices(tickerA, tickerB)
%
% DESCRIPTION:
%
%   This function will fetch historical price data from yahoo finance for
%   stocks described by tickerA and tickerB, convert dates to datenum and
%   find the intersection of the two time-series for further analysis.
%
%   tickerA: string containing stock ticker, e.g., 'aapl'
%   tickerB: string containing stick ticker, e.g., 'msft'
%   npoint:  number of data points to compare, if empty use all points 
%
%   intersec: list of datenum's that are common to stocks A and B
%   priceA: price of stock A corresponding to dates in intersec
%   priceB: price of stock B corresponding to dates in intersec
%
% NOTES:
%
%   Uses get_hist_stock_data
%   Written by J. Bortnik, 6/20/2012

PLOT_IT = 0;

if nargin<3,
    npoints=1e6;
end


% Download data
%
% This is the most fragile part of the code.  Need to loop over this
% several  times bc sometimes it doesn't work.



% Get priceA data
[dt_A,high_A,low_A,open_A,close_A,vol_A] = get_stock_data(tickerA);

% Get priceB data
[dt_B,high_B,low_B,open_B,close_B,vol_B] = get_stock_data(tickerB);







% convert date to numbers
dt_num_A = datenum(dt_A);
dt_num_B = datenum(dt_B);

% find intersection of dates
[intersec_all,ind_A,ind_B] = intersect(dt_num_A, dt_num_B);

% trim down to npoints
if numel(intersec_all)>npoints,
    ind2 = length(intersec_all);
    ind1 = ind2-npoints+1;
else,
    ind2 = length(intersec_all);
    ind1 = 1;
end
intersec = intersec_all(ind1:ind2);
priceA = close_A(ind_A(ind1:ind2));
priceB = close_B(ind_B(ind1:ind2));



if PLOT_IT,
    
    figure,
    subplot(2,1,1)
    plot(intersec, priceA, intersec, priceB)
    title(['Raw data plot, ',datestr(intersec(1)),'-',datestr(intersec(end))])
    ylabel('Price ($)')
    xlabel('Date number')
    legend(tickerA,tickerB,'location','northwest')

    subplot(2,1,2)
    day_num = [ind1:ind2]-ind1+1;
    priceA_norm = 100*(priceA/priceA(1));
    priceB_norm = 100*(priceB/priceB(1));
    plot(day_num, priceA_norm, day_num, priceB_norm)
    title('Scaled data plot')
    ylabel('Percent change')
    xlabel('Day')

end

