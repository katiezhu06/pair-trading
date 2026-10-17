% get_multiple_hist_data
%
% DESCRIPTION:
%
%   This script will go through a list of stock tickers and simply 
%   download them to the 'daiy' subdirectoy.
%

tic,

filename = 'sp500.xls';

[num, data_full] = xlsread(filename);

% select sector
%inds = find( strcmp(data_full(:,4),'Financials'));
inds = 1: length(data_full(:,1));
data = data_full(inds,:);

[len, rows] = size(data);

nstocks = len;
levels  = [1 5 10 90 95 99]';




for s1=1:nstocks,
    
    stockA = char( data(s1,1) );
    stockA(regexp(stockA,' ')) = [];
    [dt_A,high_A,low_A,open_A,close_A,vol_A] = get_stock_data(stockA);
    disp(['Downloaded: ',stockA,', #' num2str(s1) ,' of ',num2str(nstocks),', ',num2str(length(dt_A)),' days']);

end         % s1 loop
        
toc        
        
