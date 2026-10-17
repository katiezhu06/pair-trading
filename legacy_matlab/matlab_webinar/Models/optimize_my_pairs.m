% optimize my_pairs
stockA = 'xle'; %dfs-fdx
stockB = 'uso';
cadence= 3; % minutes



if ~exist(stockA),
    a     = getHistoricalIntraDayStockPrice(stockA,[],num2str(cadence*60),'100d');
end

if ~exist(stockB)
    b     = getHistoricalIntraDayStockPrice(stockB,[],num2str(cadence*60),'100d');
end


[c, ia, ib] = intersect(a.date , b.date);

A = a.close(ia);
B = b.close(ib);

series2 = [A,B];
t = 1:length(A);





M = 25:25:600;
lenM = length(M);

N = 10:10:100;
lenN = length(N);

S = zeros(lenM, lenN);
Sh = zeros(lenM, lenN);

tic
for Mi=1:lenM,
    for Ni=1:lenN,
        
        disp(['Mi=',num2str(Mi),' of ',num2str(lenM),', Ni=', ...
            num2str(Ni),' of ',num2str(lenN)]);
 
        [s,r,sh] = my_pairs(series2,M(Mi),N(Ni),cadence,2);
        S(Mi,Ni) = r;
        Sh(Mi,Ni) = sh;
        
        
    end %Ni
    
end %Mi
toc        
        

figure,
subplot(2,2,1)
imagesc(N,M,S), axis xy, colorbar
title(['Return: ',stockA,'-',stockB])
xlabel('Period')
ylabel('Lookback')

        
subplot(2,2,2),
imagesc(N,M,Sh), axis xy, colorbar
title('Sharpe')       
xlabel('Period')
ylabel('Lookback')

subplot(2,2,3),
imagesc(N,M,S./Sh), axis xy, colorbar
title('return over Sharpe')  
xlabel('Period')
ylabel('Lookback')





