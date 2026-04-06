

%% Volatility risk prermium
% 1. Q variance: VIX
% 2. P estimated by empirical density
%% load data
clear,clc
addpath("m_Files_Color")                  % Add directory to MATLAB's search path for custom color files
addpath("m_Files_Color/colormap")         % Add subdirectory for colormap files
[~,~,~]=mkdir("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Variance_Risk_Premium/");  % Create directory for output, if it doesn't exist
% daily_price = readtable("data/BTC_USD_Quandl_2015_2022.csv"); % Reading daily price data

ttm = 27;

opts = detectImportOptions("data/BTC_USD_Quandl_2011_2023.csv", "Delimiter",",");
opts = setvartype(opts,1,"char");
daily_price = readtable("data/BTC_USD_Quandl_2011_2023.csv",opts);
daily_price.Date = datetime(daily_price.Date,"Format","uuuu-MM-dd HH:mm:ss","InputFormat","uuuu/MM/dd");
daily_price = sortrows(daily_price,"Date");
daily_price = daily_price(daily_price.Date <= datetime("2022-12-31"),:);
daily_price = daily_price(daily_price.Date >= datetime("2014-01-01"),:);

%% Load cluster
common_dates = readtable('Clustering/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/common_dates_cluster.csv');
dates = string(common_dates.Date);
dates_list = datetime(dates, "InputFormat","uuuu-MM-dd");

index0 = common_dates.Cluster==0;
index1 = common_dates.Cluster==1;
dates_Q{1,1} = dates_list(index0);
dates_Q{1,2} = dates_list(index1);
tb_date_cluster0 = table(dates_Q{1,1},'VariableNames',"Date");
tb_date_cluster1 = table(dates_Q{1,2},'VariableNames',"Date");
tb_date_overall = table(dates_list,'VariableNames',"Date");

%% Generate P moments table
ret = (-1:0.01:1)';

% Read Bitcoin Premium data from Excel files for different TTM (Time to Maturity) values
Q_P_PK_overall_ttm27=readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/Q_P_ePDF_backward_onlyVR_OA_differentNB_ttm27.xlsx");
Q_P_PK_c0_ttm27=readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/Q_P_ePDF_backward_onlyVR_HV_differentNB_ttm27.xlsx");
Q_P_PK_c1_ttm27=readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/Q_P_ePDF_backward_onlyVR_LV_differentNB_ttm27.xlsx");

P_overall = Q_P_PK_overall_ttm27.P_NB12;

Moments_P_OA = zeros(1,7);
Moments_P_OA(1,1) = trapz(ret,P_overall);
Moments_P_OA(1,2) = trapz(ret,P_overall.*repmat(ret,1,size(P_overall,2)));% 1th moment
Moments_P_OA(1,3) = trapz(ret,P_overall.*(repmat(ret,1,size(P_overall,2))-repmat(Moments_P_OA(:,2)',size(P_overall,1),1)).^2);% 2th central moment
Moments_P_OA(1,4) = trapz(ret,P_overall.*(repmat(ret,1,size(P_overall,2))-repmat(Moments_P_OA(:,2)',size(P_overall,1),1)).^3);% 3th central moment
Moments_P_OA(1,5) = trapz(ret,P_overall.*(repmat(ret,1,size(P_overall,2))-repmat(Moments_P_OA(:,2)',size(P_overall,1),1)).^4);% 4th central moment
Moments_P_OA(1,6) = Moments_P_OA(:,4)./(Moments_P_OA(:,3).^1.5);  % Skewness
Moments_P_OA(1,7) = Moments_P_OA(:,5)./(Moments_P_OA(:,3).^2)-3;  % Kurtosis

P_cluster1= Q_P_PK_c1_ttm27.P_NB12;

Moments_P_c1 = zeros(1,7);
Moments_P_c1(:,1) = trapz(ret,P_cluster1);
Moments_P_c1(:,2) = trapz(ret,P_cluster1.*repmat(ret,1,size(P_cluster1,2)));% 1th moment
Moments_P_c1(:,3) = trapz(ret,P_cluster1.*(repmat(ret,1,size(P_cluster1,2))-repmat(Moments_P_c1(:,2)',size(P_cluster1,1),1)).^2);% 2th central moment
Moments_P_c1(:,4) = trapz(ret,P_cluster1.*(repmat(ret,1,size(P_cluster1,2))-repmat(Moments_P_c1(:,2)',size(P_cluster1,1),1)).^3);% 3th central moment
Moments_P_c1(:,5) = trapz(ret,P_cluster1.*(repmat(ret,1,size(P_cluster1,2))-repmat(Moments_P_c1(:,2)',size(P_cluster1,1),1)).^4);% 4th central moment
Moments_P_c1(:,6) = Moments_P_c1(:,4)./(Moments_P_c1(:,3).^1.5);  % Skewness
Moments_P_c1(:,7) = Moments_P_c1(:,5)./(Moments_P_c1(:,3).^2)-3;  % Kurtosis

P_cluster0= Q_P_PK_c0_ttm27.P_NB12;

Moments_P_c0 = zeros(1,7);
Moments_P_c0(:,1) = trapz(ret,P_cluster0);
Moments_P_c0(:,2) = trapz(ret,P_cluster0.*repmat(ret,1,size(P_cluster0,2)));% 1th moment
Moments_P_c0(:,3) = trapz(ret,P_cluster0.*(repmat(ret,1,size(P_cluster0,2))-repmat(Moments_P_c0(:,2)',size(P_cluster0,1),1)).^2);% 2th central moment
Moments_P_c0(:,4) = trapz(ret,P_cluster0.*(repmat(ret,1,size(P_cluster0,2))-repmat(Moments_P_c0(:,2)',size(P_cluster0,1),1)).^3);% 3th central moment
Moments_P_c0(:,5) = trapz(ret,P_cluster0.*(repmat(ret,1,size(P_cluster0,2))-repmat(Moments_P_c0(:,2)',size(P_cluster0,1),1)).^4);% 4th central moment
Moments_P_c0(:,6) = Moments_P_c0(:,4)./(Moments_P_c0(:,3).^1.5);  % Skewness
Moments_P_c0(:,7) = Moments_P_c0(:,5)./(Moments_P_c0(:,3).^2)-3;  % Kurtosis

tb_Pdensity_cluster0 = [tb_date_cluster0, table(Moments_P_c0(1,3)*ones(size(tb_date_cluster0)),'VariableNames',"P_variance_Pdensity"),table(zeros(size(tb_date_cluster0)),'VariableNames',"Cluster")];
tb_Pdensity_cluster1 = [tb_date_cluster1, table(Moments_P_c1(1,3)*ones(size(tb_date_cluster1)),'VariableNames',"P_variance_Pdensity"),table(ones(size(tb_date_cluster1)),'VariableNames',"Cluster")];
tb_Pdensity_overall = [tb_date_overall, table(Moments_P_OA(1,3)*ones(size(tb_date_overall)),'VariableNames',"P_variance_Pdensity"),table(common_dates.Cluster,'VariableNames',"Cluster")];

% Annualize
tb_Pdensity_cluster0.P_variance_Pdensity = tb_Pdensity_cluster0.P_variance_Pdensity * 365/ttm;
tb_Pdensity_cluster1.P_variance_Pdensity = tb_Pdensity_cluster1.P_variance_Pdensity * 365/ttm;
tb_Pdensity_overall.P_variance_Pdensity = tb_Pdensity_overall.P_variance_Pdensity * 365/ttm;

%% Introduce VIX
VIX = readtable(['Data/VIX/update_20231211/btc_vix_EWA_',num2str(ttm),'.csv']);
Q_vola_VIX_cluster0=VIX.EMA((ismember(VIX.Date,dates_list(index0))))/100;
Q_vola_VIX_cluster1=VIX.EMA((ismember(VIX.Date,dates_list(index1))))/100;
Q_vola_VIX_overall=VIX.EMA((ismember(VIX.Date,dates_list)))/100;
tb_Q_variance_VIX_cluster0 = array2table(Q_vola_VIX_cluster0.^2,'VariableNames',"Q_variance_VIX");
tb_Q_variance_VIX_cluster1 = array2table(Q_vola_VIX_cluster1.^2,'VariableNames',"Q_variance_VIX");
tb_Q_variance_VIX_overall = array2table(Q_vola_VIX_overall.^2,'VariableNames',"Q_variance_VIX");
tb_Q_date_VIX_cluster0 = table(VIX.Date((ismember(VIX.Date,dates_list(index0)))),'VariableNames',"Date");
tb_Q_date_VIX_cluster1 = table(VIX.Date((ismember(VIX.Date,dates_list(index1)))),'VariableNames',"Date");
tb_Q_date_VIX_overall = table(VIX.Date((ismember(VIX.Date,dates_list))),'VariableNames',"Date");
tb_Q_variance_VIX_cluster0 = [tb_Q_date_VIX_cluster0, tb_Q_variance_VIX_cluster0];
tb_Q_variance_VIX_cluster1 = [tb_Q_date_VIX_cluster1, tb_Q_variance_VIX_cluster1];
tb_Q_variance_VIX_overall = [tb_Q_date_VIX_overall, tb_Q_variance_VIX_overall];

%% Generate table "tb_VIX_Pdensity_VRP"
tb_VIX_Pdensity_VRP_cluster0 = innerjoin(tb_Q_variance_VIX_cluster0, tb_Pdensity_cluster0,"Key","Date");
tb_VIX_Pdensity_VRP_cluster1 = innerjoin(tb_Q_variance_VIX_cluster1, tb_Pdensity_cluster1,"Key","Date");
tb_VIX_Pdensity_VRP_overall = innerjoin(tb_Q_variance_VIX_overall, tb_Pdensity_overall,"Key","Date");
tb_VIX_Pdensity_VRP_cluster0 = addvars(tb_VIX_Pdensity_VRP_cluster0, tb_VIX_Pdensity_VRP_cluster0.Q_variance_VIX-tb_VIX_Pdensity_VRP_cluster0.P_variance_Pdensity, 'NewVariableNames',"VRP");
tb_VIX_Pdensity_VRP_cluster1 = addvars(tb_VIX_Pdensity_VRP_cluster1, tb_VIX_Pdensity_VRP_cluster1.Q_variance_VIX-tb_VIX_Pdensity_VRP_cluster1.P_variance_Pdensity, 'NewVariableNames',"VRP");
tb_VIX_Pdensity_VRP_overall = addvars(tb_VIX_Pdensity_VRP_overall, tb_VIX_Pdensity_VRP_overall.Q_variance_VIX-tb_VIX_Pdensity_VRP_overall.P_variance_Pdensity, 'NewVariableNames',"VRP");

%% Save tb_VIX_Pdensity_VRP_HV, tb_VIX_Pdensity_VRP_LV
writetable(tb_VIX_Pdensity_VRP_cluster0,"RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Variance_Risk_Premium/VRP_VIX_Pdensity_HV.csv");
writetable(tb_VIX_Pdensity_VRP_cluster1,"RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Variance_Risk_Premium/VRP_VIX_Pdensity_LV.csv");