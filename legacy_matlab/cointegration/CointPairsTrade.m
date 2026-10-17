function Out = CointPairsTrade(PriceMat,Symbols)
% CointPairsTrade: This function tests for cointegration of pairs of stocks.
% It also gives out the half Life of the Cointegrated Pairs and 
% also how far the current spread is to the standard deviation
% Inputs:
% 1. PriceMat- A  Ndays X NumStocks  matrix of Prices
% 2. Symbols-- A  NumStocks X 1 Cell matrix of Symbols
% Outputs:
% A structure with the following fields
% FinalMatML and FinalMatLS---Maximum Likelihood and Least Squares Approach
% ---Cell matrix with the following columns:
%                1. Stock Symbol 1
%                2. Stock Symnbol 2
%                3. Half Life
%                4. Beta
%                5. Ratio of the current Spread and Std(spread)
% The results will also be written to an EXCEL sheet named CointPairs.xls
% Please Note that I assume that the Close Prices are already cleaned
% This function depends on functions provided by James P. LeSage in
% Spatial-Econometrics ToolBox. For convenience sake I have attached only
% the relevant files.
% Author: Tradingwithmatlab.blogspot.com

Out = [];
NumStocks = size(PriceMat,2);
CointMatrix = zeros(NumStocks);
% create a Cointegration matrix
% Go through the list of stocks and test for cointegration.
for idx = 1:NumStocks;
    for jdx=idx+1:NumStocks
        CointMatrix(idx,jdx)=TestForCoint(PriceMat(:,idx),PriceMat(:,jdx));
    end
    
end
[rows,cols]=find(CointMatrix);
CointPairs = [rows cols];
cf=(CointPairs(:,1)-CointPairs(:,2))==0;
CointPairs(cf,:)=[];

if(isempty(CointPairs))
    warning('No Cointegrated Pairs Found') %#ok<WNTAG>
    return
end
% Pre-define variables
Hlife = zeros(size(CointPairs,1),1);
HlifeLS = Hlife;
betas = Hlife;
spread = Hlife;

for idx1 = 1:size(CointPairs,1)
    X = PriceMat(:,CointPairs(idx1,1));
    Y = PriceMat(:,CointPairs(idx1,2));
    % Calculate Beta
    beta = X\Y;%[ones(length(X),1),X]\Y;
    % Calculate Residuals
    res = Y - X*beta;%[ones(length(X),1),X]*beta;
    % Calculate Half Life Maximum Likelihood Approach
    [mu,sigma,lambda] = OU_Calibrate_ML(res,1);
    Hlife(idx1,1)=log(2)/lambda;
    % Calculate Half life Least Squares Approach
    [mu,sigma,lambda] = OU_Calibrate_LS(res,1);
    HlifeLS(idx1,1)=log(2)/lambda;
    % Store the Betas for later use
    betas(idx1,1) = beta;%beta(2);
    % Calculate and Store how far is the Spread currently
    stdres = std(res(1:end-1));
    % Calculate the ratio of how far is the current spread from average
    spread(idx1,1) = res(end)/stdres;
end
% Sort them and output the Final Matrix
% Maximum Likelihood
[Hlife,sortidx]=sort(Hlife,1,'ascend');
Out.FinalMatML = [Symbols(CointPairs(sortidx,:)) num2cell(Hlife) num2cell([betas(sortidx,:) spread(sortidx,:)])];
% Least Squares
[HlifeLS,sortidx]=sort(HlifeLS,1,'ascend');
Out.FinalMatLS = [Symbols(CointPairs(sortidx,:)) num2cell(HlifeLS) num2cell([betas(sortidx,:) spread(sortidx,:)])];
% Write to Excel
xlswrite('CointPairs.xls',Out.FinalMatML,'CointPairsML');
xlswrite('CointPairs.xls',Out.FinalMatLS,'CointPairsLS');

% Test For Cointegration
    function H = TestForCoint(X,Y)
        H = 0;
        nlagsX = 1;%Get_Max_Lags(X,0);
        nlagsY = 1;%Get_Max_Lags(Y,0);
        % First Test if both X and Y are I(1) variables
        resX = adf(X,0,nlagsX);
        resY = adf(Y,0,nlagsY);
        % If the Trace is Less than Crtical, then it is I(1) process
        if(abs(resX.adf) < abs(resX.crit(2)))
            Hx = 1;
        else
            Hx = 0;
        end
        if(abs(resY.adf) < abs(resY.crit(2)))
            Hy = 1;
        else
            Hy= 0;
        end
        
        % If they are I(1) processes, now test for Cointegration
        % using Engle Granger and johansen Procedures
        if(Hx==1 && Hy==1)
            reseg = cadf(X,Y,0,1);
            %resj = johansen([X,Y],0,max(nlagsX,nlagsY));
            if((abs(reseg.adf) > abs(reseg.crit(2))))% ||( resj.lr1(2) > resj.cvt(5) ...
                %&& resj.lr2(2) > resj.cvm(5)))
                H = 1;
            else
                H = 0;
            end
        end
    end % TestForCoint

% OU Process to find Lambda or in some papers THETA
% Maximum Likelihood

    function [mu,sigma,lambda] = OU_Calibrate_ML(S,delta)
        n = length(S)-1;
        Sx  = sum( S(1:end-1) );
        Sy  = sum( S(2:end) );
        Sxx = sum( S(1:end-1).^2 );
        Sxy = sum( S(1:end-1).*S(2:end) );
        Syy = sum( S(2:end).^2 );
        mu  = (Sy*Sxx - Sx*Sxy) / ( n*(Sxx - Sxy) - (Sx^2 - Sx*Sy) );
        lambda = -log( (Sxy - mu*Sx - mu*Sy + n*mu^2) / (Sxx -2*mu*Sx + n*mu^2) ) / delta;
        a = exp(-lambda*delta);
        sigmah2 = (Syy - 2*a*Sxy + a^2*Sxx - 2*mu*(1-a)*(Sy - a*Sx) + n*mu^2*(1-a)^2)/n;
        sigma = sqrt(sigmah2*2*lambda/(1-a^2));
    end %OU_Calibrate_ML

% OU Process to find Lambda or in some papers THETA
% Least Squares

    function [mu,sigma,lambda] = OU_Calibrate_LS(S,delta)
        n = length(S)-1;
        Sx  = sum( S(1:end-1) );
        Sy  = sum( S(2:end) );
        Sxx = sum( S(1:end-1).^2 );
        Sxy = sum( S(1:end-1).*S(2:end) );
        Syy = sum( S(2:end).^2 );
        a  = ( n*Sxy - Sx*Sy ) / ( n*Sxx -Sx^2 );
        b  = ( Sy - a*Sx ) / n;
        sd = sqrt( (n*Syy - Sy^2 - a*(n*Sxy - Sx*Sy) )/n/(n-2) );
        lambda = -log(a)/delta;
        mu     = b/(1-a);
        sigma  =  sd * sqrt( -2*log(a)/delta/(1-a^2) );
    end %OU_Calibrate_LS

end % CointPairsTrade
