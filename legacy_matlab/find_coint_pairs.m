% find_coint_pairs
%
% DESCRIPTION:
%
%   This script will go through a list of stock tickers and apply the 
%   augmented Dickey-Fuller test to check for cointegration.   
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
P       = ones(nstocks,nstocks,4)*100;



for s1=1:(nstocks-1),
    for s2= (s1+1):nstocks,
        
        disp(['Comparing stocks ',num2str(s1),' and ',num2str(s2)]);
        stockA = char( data(s1,1) );
        stockB = char( data(s2,1) );
        
        [dt,A,B] = compare_hist_prices(stockA,stockB,252);
        
        results1 = cadf(A,B,0,3);
        results2 = cadf(B,A,0,3);
        results3 = cadf(log(A),log(B),0,3);
        results4 = cadf(log(B),log(A),0,3);
        
        % interpolate
        adf_level1 = interp1( results1.crit, levels, results1.adf, ...
            'pchip','extrap');

        adf_level2 = interp1( results2.crit, levels, results2.adf, ...
            'pchip','extrap');
        
        adf_level3 = interp1( results3.crit, levels, results3.adf, ...
            'pchip','extrap');
        
        adf_level4 = interp1( results4.crit, levels, results4.adf, ...
            'pchip','extrap');
        
        P(s1,s2,1) = adf_level1;
        P(s1,s2,2) = adf_level2;
        P(s1,s2,3) = adf_level3;
        P(s1,s2,4) = adf_level4;
        
    end     % s2 loop
end         % s1 loop
        
toc        
        
