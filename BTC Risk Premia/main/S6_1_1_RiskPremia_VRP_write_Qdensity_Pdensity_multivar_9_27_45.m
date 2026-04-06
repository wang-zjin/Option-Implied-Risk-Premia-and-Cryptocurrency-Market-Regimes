



%% Volatility risk prermium
% 1. Q estimated from interpolated IV
% 2. P estimated by empirical density
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

%% Generate table "tb_Qdensity_Pdensity_VRP"
tb_Q_variance_Qdensity_overall = tb_Moments_Q_t(:,["Date","Variance"]);
tb_Q_variance_Qdensity_cluster0 = tb_Moments_Q_c0_t(:,["Date","Variance"]);
tb_Q_variance_Qdensity_cluster1 = tb_Moments_Q_c1_t(:,["Date","Variance"]);

% Rename Q variance variable
tb_Q_variance_Qdensity_overall.Properties.VariableNames("Variance") = "Q_variance_Qdensity";
tb_Q_variance_Qdensity_cluster0.Properties.VariableNames("Variance") = "Q_variance_Qdensity";
tb_Q_variance_Qdensity_cluster1.Properties.VariableNames("Variance") = "Q_variance_Qdensity";

% Annualize
tb_Q_variance_Qdensity_overall.Q_variance_Qdensity = tb_Q_variance_Qdensity_overall.Q_variance_Qdensity * 365/ttm;
tb_Q_variance_Qdensity_cluster0.Q_variance_Qdensity = tb_Q_variance_Qdensity_cluster0.Q_variance_Qdensity * 365/ttm;
tb_Q_variance_Qdensity_cluster1.Q_variance_Qdensity = tb_Q_variance_Qdensity_cluster1.Q_variance_Qdensity * 365/ttm;

tb_Qdensity_Pdensity_VRP_overall = innerjoin(tb_Q_variance_Qdensity_overall, tb_Pdensity_overall,"Key","Date");
tb_Qdensity_Pdensity_VRP_cluster0 = innerjoin(tb_Q_variance_Qdensity_cluster0, tb_Pdensity_cluster0,"Key","Date");
tb_Qdensity_Pdensity_VRP_cluster1 = innerjoin(tb_Q_variance_Qdensity_cluster1, tb_Pdensity_cluster1,"Key","Date");
tb_Qdensity_Pdensity_VRP_overall = addvars(tb_Qdensity_Pdensity_VRP_overall, tb_Qdensity_Pdensity_VRP_overall.Q_variance_Qdensity-tb_Qdensity_Pdensity_VRP_overall.P_variance_Pdensity, 'NewVariableNames',"VRP");
tb_Qdensity_Pdensity_VRP_cluster0 = addvars(tb_Qdensity_Pdensity_VRP_cluster0, tb_Qdensity_Pdensity_VRP_cluster0.Q_variance_Qdensity-tb_Qdensity_Pdensity_VRP_cluster0.P_variance_Pdensity, 'NewVariableNames',"VRP");
tb_Qdensity_Pdensity_VRP_cluster1 = addvars(tb_Qdensity_Pdensity_VRP_cluster1, tb_Qdensity_Pdensity_VRP_cluster1.Q_variance_Qdensity-tb_Qdensity_Pdensity_VRP_cluster1.P_variance_Pdensity, 'NewVariableNames',"VRP");

%% Save tb_Qdensity_Pdensity_VRP_cluster0, tb_Qdensity_Pdensity_VRP_cluster1
VRP_folder = "RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Variance_Risk_Premium/";
[~,~,~]=mkdir(VRP_folder);
writetable(tb_Qdensity_Pdensity_VRP_cluster0,strcat(VRP_folder, "VRP_Qdensity_Pdensity_HV.csv"));
writetable(tb_Qdensity_Pdensity_VRP_cluster1,strcat(VRP_folder, "VRP_Qdensity_Pdensity_LV.csv"));

%% Functions
function Q_matrix = Q_density_cluster(dates_strings,ttm)
raw_header = readcell(strcat("Q_matrix/Tau-independent/unique/moneyness_step_0d01/Q_matrix_", num2str(ttm), "day.csv"), 'FileType', 'text');
header_names = string(raw_header(1, :));  % First row contains column names
header_names(1,2:end) = datestr(datetime(header_names(1,2:end), "Format","uuuu-MM-dd"), "yyyy-mm-dd"); % Adjust date format
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
