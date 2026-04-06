

%% Volatility risk prermium
% 1. Q estimated from interpolated IV
% 2. P estimated by kernel density
% 3. P realised volatility
% 4. P forward-looking volatility
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

%% Realized variance
realized_vola = zeros(numel(dates),2);
for i = 1:length(dates)

%     sp1=daily_price(end:-1:1,:);
    sp1=sortrows(daily_price,"Date");
    logret_before = price2ret(sp1.Adj_Close(datenum(sp1.Date)>=datenum(dates(i),"yyyy-mm-dd")-ttm-1 & datenum(sp1.Date)<=datenum(dates(i),"yyyy-mm-dd")-1));
    logret_after = price2ret(sp1.Adj_Close(datenum(sp1.Date)>=datenum(dates(i),"yyyy-mm-dd") & datenum(sp1.Date)<=datenum(dates(i),"yyyy-mm-dd")+ttm));
    realized_vola(i,1)=sqrt(sum(logret_before.^2)*365/ttm);
    realized_vola(i,2)=sqrt(sum(logret_after.^2)*365/ttm);
end

tb_RV_cluster0 = [tb_date_cluster0, table(realized_vola(index0,1).^2,'VariableNames',"RV"),table(zeros(size(tb_date_cluster0)),'VariableNames',"Cluster")];
tb_RV_cluster1 = [tb_date_cluster1, table(realized_vola(index1,1).^2,'VariableNames',"RV"),table(ones(size(tb_date_cluster1)),'VariableNames',"Cluster")];
tb_RV_overall = [tb_date_overall, table(realized_vola(:,1).^2,'VariableNames',"RV"),table(common_dates.Cluster,'VariableNames',"Cluster")];

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

%% Generate table "tb_VIX_RV_VRP"
tb_VIX_RV_VRP_cluster0 = innerjoin(tb_Q_variance_VIX_cluster0, tb_RV_cluster0,"Key","Date");
tb_VIX_RV_VRP_cluster1 = innerjoin(tb_Q_variance_VIX_cluster1, tb_RV_cluster1,"Key","Date");
tb_VIX_RV_VRP_overall = innerjoin(tb_Q_variance_VIX_overall, tb_RV_overall,"Key","Date");
tb_VIX_RV_VRP_cluster0 = addvars(tb_VIX_RV_VRP_cluster0, tb_VIX_RV_VRP_cluster0.Q_variance_VIX-tb_VIX_RV_VRP_cluster0.RV, 'NewVariableNames',"VRP");
tb_VIX_RV_VRP_cluster1 = addvars(tb_VIX_RV_VRP_cluster1, tb_VIX_RV_VRP_cluster1.Q_variance_VIX-tb_VIX_RV_VRP_cluster1.RV, 'NewVariableNames',"VRP");
tb_VIX_RV_VRP_overall = addvars(tb_VIX_RV_VRP_overall, tb_VIX_RV_VRP_overall.Q_variance_VIX-tb_VIX_RV_VRP_overall.RV, 'NewVariableNames',"VRP");

%% Save tb_VIX_RV_VRP_HV, tb_VIX_RV_VRP_LV
writetable(tb_VIX_RV_VRP_cluster0,"RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Variance_Risk_Premium/VRP_VIX_logRV_HV.csv");
writetable(tb_VIX_RV_VRP_cluster1,"RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Variance_Risk_Premium/VRP_VIX_logRV_LV.csv");