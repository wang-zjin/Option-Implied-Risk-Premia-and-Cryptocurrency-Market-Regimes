



%% Volatility risk prermium
% 1. Q estimated from interpolated IV
% 2. P estimated by kernel density
% 3. P realised volatility
% 4. P forward-looking volatility
%% load data
clear,clc
[~,~,~]=mkdir("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/");
addpath("m_Files_Color/colormap/")

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
%% Realized volatility
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

%% Generate time varying Q moments table
ret = (-1:0.01:1)';
% Q-density
Q_cluster0 = Q_density_cluster(dates(index0),ttm);
Q_cluster1 = Q_density_cluster(dates(index1),ttm);
Q_overall = [Q_cluster0 Q_cluster1];

Moments_Q_t = zeros(size(Q_overall,2),7);
Moments_Q_t(:,1) = trapz(ret,Q_overall);
Moments_Q_t(:,2) = trapz(ret,Q_overall.*repmat(ret,1,size(Q_overall,2)));% 1th moment
Moments_Q_t(:,3) = trapz(ret,Q_overall.*(repmat(ret,1,size(Q_overall,2))-repmat(Moments_Q_t(:,2)',size(Q_overall,1),1)).^2);% 2th central moment
Moments_Q_t(:,4) = trapz(ret,Q_overall.*(repmat(ret,1,size(Q_overall,2))-repmat(Moments_Q_t(:,2)',size(Q_overall,1),1)).^3);% 3th central moment
Moments_Q_t(:,5) = trapz(ret,Q_overall.*(repmat(ret,1,size(Q_overall,2))-repmat(Moments_Q_t(:,2)',size(Q_overall,1),1)).^4);% 4th central moment
Moments_Q_t(:,6) = Moments_Q_t(:,4)./(Moments_Q_t(:,3).^1.5);  % Skewness
Moments_Q_t(:,7) = Moments_Q_t(:,5)./(Moments_Q_t(:,3).^2)-3;  % Kurtosis

Moments_Q_c1_t = zeros(size(Q_cluster1,2),7);
Moments_Q_c1_t(:,1) = trapz(ret,Q_cluster1);
Moments_Q_c1_t(:,2) = trapz(ret,Q_cluster1.*repmat(ret,1,size(Q_cluster1,2)));% 1th moment
Moments_Q_c1_t(:,3) = trapz(ret,Q_cluster1.*(repmat(ret,1,size(Q_cluster1,2))-repmat(Moments_Q_c1_t(:,2)',size(Q_cluster1,1),1)).^2);% 2th central moment
Moments_Q_c1_t(:,4) = trapz(ret,Q_cluster1.*(repmat(ret,1,size(Q_cluster1,2))-repmat(Moments_Q_c1_t(:,2)',size(Q_cluster1,1),1)).^3);% 3th central moment
Moments_Q_c1_t(:,5) = trapz(ret,Q_cluster1.*(repmat(ret,1,size(Q_cluster1,2))-repmat(Moments_Q_c1_t(:,2)',size(Q_cluster1,1),1)).^4);% 4th central moment
Moments_Q_c1_t(:,6) = Moments_Q_c1_t(:,4)./(Moments_Q_c1_t(:,3).^1.5);  % Skewness
Moments_Q_c1_t(:,7) = Moments_Q_c1_t(:,5)./(Moments_Q_c1_t(:,3).^2)-3;  % Kurtosis

Moments_Q_c0_t = zeros(size(Q_cluster0,2),7);
Moments_Q_c0_t(:,1) = trapz(ret,Q_cluster0);
Moments_Q_c0_t(:,2) = trapz(ret,Q_cluster0.*repmat(ret,1,size(Q_cluster0,2)));% 1th moment
Moments_Q_c0_t(:,3) = trapz(ret,Q_cluster0.*(repmat(ret,1,size(Q_cluster0,2))-repmat(Moments_Q_c0_t(:,2)',size(Q_cluster0,1),1)).^2);% 2th central moment
Moments_Q_c0_t(:,4) = trapz(ret,Q_cluster0.*(repmat(ret,1,size(Q_cluster0,2))-repmat(Moments_Q_c0_t(:,2)',size(Q_cluster0,1),1)).^3);% 3th central moment
Moments_Q_c0_t(:,5) = trapz(ret,Q_cluster0.*(repmat(ret,1,size(Q_cluster0,2))-repmat(Moments_Q_c0_t(:,2)',size(Q_cluster0,1),1)).^4);% 4th central moment
Moments_Q_c0_t(:,6) = Moments_Q_c0_t(:,4)./(Moments_Q_c0_t(:,3).^1.5);  % Skewness
Moments_Q_c0_t(:,7) = Moments_Q_c0_t(:,5)./(Moments_Q_c0_t(:,3).^2)-3;  % Kurtosis

tb_Moments_Q_t = [[tb_date_cluster0;tb_date_cluster1], array2table(Moments_Q_t(:,[2,3,6,7]),'VariableNames',["Mean","Variance","Skewness","Kurtosis"])];
tb_Moments_Q_c0_t = [tb_date_cluster0, array2table(Moments_Q_c0_t(:,[2,3,6,7]),'VariableNames',["Mean","Variance","Skewness","Kurtosis"])];
tb_Moments_Q_c1_t = [tb_date_cluster1, array2table(Moments_Q_c1_t(:,[2,3,6,7]),'VariableNames',["Mean","Variance","Skewness","Kurtosis"])];

%% Generate table "tb_Qdensity_RV_VRP"
tb_Q_variance_Qdensity_overall = tb_Moments_Q_t(:,["Date","Variance"]);
tb_Q_variance_Qdensity_cluster0 = tb_Moments_Q_c0_t(:,["Date","Variance"]);
tb_Q_variance_Qdensity_cluster1 = tb_Moments_Q_c1_t(:,["Date","Variance"]);

tb_Q_variance_Qdensity_overall.Variance = tb_Q_variance_Qdensity_overall.Variance*365/ttm;
tb_Q_variance_Qdensity_cluster0.Variance = tb_Q_variance_Qdensity_cluster0.Variance*365/ttm;
tb_Q_variance_Qdensity_cluster1.Variance = tb_Q_variance_Qdensity_cluster1.Variance*365/ttm;

tb_Q_variance_Qdensity_overall.Properties.VariableNames("Variance") = "Q_variance_Qdensity";
tb_Q_variance_Qdensity_cluster0.Properties.VariableNames("Variance") = "Q_variance_Qdensity";
tb_Q_variance_Qdensity_cluster1.Properties.VariableNames("Variance") = "Q_variance_Qdensity";

tb_Qdensity_RV_VRP_overall = innerjoin(tb_Q_variance_Qdensity_overall, tb_RV_overall,"Key","Date");
tb_Qdensity_RV_VRP_cluster0 = innerjoin(tb_Q_variance_Qdensity_cluster0, tb_RV_cluster0,"Key","Date");
tb_Qdensity_RV_VRP_cluster1 = innerjoin(tb_Q_variance_Qdensity_cluster1, tb_RV_cluster1,"Key","Date");
tb_Qdensity_RV_VRP_overall = addvars(tb_Qdensity_RV_VRP_overall, tb_Qdensity_RV_VRP_overall.Q_variance_Qdensity-tb_Qdensity_RV_VRP_overall.RV, 'NewVariableNames',"VRP");
tb_Qdensity_RV_VRP_cluster0 = addvars(tb_Qdensity_RV_VRP_cluster0, tb_Qdensity_RV_VRP_cluster0.Q_variance_Qdensity-tb_Qdensity_RV_VRP_cluster0.RV, 'NewVariableNames',"VRP");
tb_Qdensity_RV_VRP_cluster1 = addvars(tb_Qdensity_RV_VRP_cluster1, tb_Qdensity_RV_VRP_cluster1.Q_variance_Qdensity-tb_Qdensity_RV_VRP_cluster1.RV, 'NewVariableNames',"VRP");

%% Save tb_Qdensity_RV_VRP_cluster0, tb_Qdensity_RV_VRP_cluster1
VRP_folder = "RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Variance_Risk_Premium/";
[~,~,~]=mkdir(VRP_folder);
writetable(tb_Qdensity_RV_VRP_cluster0,strcat(VRP_folder, "VRP_Qdensity_logRV_HV.csv"));
writetable(tb_Qdensity_RV_VRP_cluster1,strcat(VRP_folder, "VRP_Qdensity_logRV_LV.csv"));

%% Functions
function Q_matrix = Q_density_cluster(dates_strings,ttm)
raw_header = readcell(strcat("Q_matrix/Tau-independent/unique/moneyness_step_0d01/Q_matrix_", num2str(ttm), "day.csv"), 'FileType', 'text');
header_names = string(raw_header(1, :));  % First row contains column names
% Replace MATLAB-assigned names with actual headers
Q_table = readtable(strcat("Q_matrix/Tau-independent/unique/moneyness_step_0d01/Q_matrix_",num2str(ttm),"day.csv"), ...
    "VariableNamesRow",1, "VariableNamingRule","preserve");
Q_table_new = Q_table(2:end,:);
Q_table_new.Properties.VariableNames = header_names;

% Step 1: Identify common columns between common_dates and Q_table
common_columns = intersect(Q_table_new.Properties.VariableNames, dates_strings);

% Step 2: Initialize a new matrix to store the filtered data
Q_matrix = table2array(Q_table_new(:, common_columns));
end
