

% This file is to save BP and BVRP time series produced by SS25 method

%% load data
%clear,clc
addpath("m_Files_Color")                 % Add directory to MATLAB's search path for custom color files
addpath("m_Files_Color/colormap")        % Add subdirectory for colormap files
outDir = "RiskPremia/SS25/ttm_27/";
[~, ~, ~] = mkdir(outDir);

%% Add SS25

[~,~,~,~,fP] = LL(theta_0(2,1:3),2,ln_fQ,r30,log(sig_t),r_vec,ln_fQ_t,del); % normalized density on every day
ER_P   = fP*R_vec*del;
var_P  = fP*R_vec.^2*del-ER_P.^2;
std_P  = sqrt(var_P);
skew_P = sum(fP.*((R_vec'-ER_P)./std_P).^3,2)*del;
kurt_P = sum(fP.*((R_vec'-ER_P)./std_P).^4,2)*del;

ER_Q   = fQ*R_vec*del;
var_Q  = fQ*R_vec.^2*del-ER_Q.^2;
std_Q  = sqrt(var_Q);
skew_Q = sum(fQ.*((R_vec'-ER_Q)./std_Q).^3,2)*del;
kurt_Q = sum(fQ.*((R_vec'-ER_Q)./std_Q).^4,2)*del;

if isdatetime(dates)
    dates_datetime = dates;
elseif isnumeric(dates)
    dates_datetime = datetime(dates, 'ConvertFrom', 'yyyymmdd', 'Format', 'uuuu-MM-dd');
else
    dates_datetime = datetime(dates, 'InputFormat', 'yyyyMMdd', 'Format', 'uuuu-MM-dd');
end
datesNum = datenum(dates_datetime);
%% Load BP and BVRP

BP = 365/27*(ER_P-ER_Q);

tb_VIX_Pdensity_VRP_cluster0 = readtable("data_prep/data_BTC/RiskPremia/multivariate_clustering_9_27_45/Variance_Risk_Premium/VRP_VIX_Pdensity_HV.csv");
tb_VIX_Pdensity_VRP_cluster1 = readtable("data_prep/data_BTC/RiskPremia/multivariate_clustering_9_27_45/Variance_Risk_Premium/VRP_VIX_Pdensity_LV.csv");
tb_VIX_Pdensity_VRP_overall = [tb_VIX_Pdensity_VRP_cluster0;tb_VIX_Pdensity_VRP_cluster1];
tb_VIX_Pdensity_VRP_overall = sortrows(tb_VIX_Pdensity_VRP_overall, 'Date');
tb_VIX_Pdensity_VRP_overall.Date = datetime(tb_VIX_Pdensity_VRP_overall.Date, 'ConvertFrom', 'yyyymmdd');

BVRP = tb_VIX_Pdensity_VRP_overall(:, {'Date', 'VRP'});

%% Merge BP and BVRP, save under RiskPremia/SS25/ttm_27/

tb_BP = table(dates_datetime(:), BP(:), 'VariableNames', {'Date', 'BP'});
tb_merged = innerjoin(tb_BP, BVRP, 'Keys', 'Date');
tb_merged = sortrows(tb_merged, 'Date');

tb_merged_csv = tb_merged;
tb_merged_csv.Date = yyyymmdd(tb_merged_csv.Date);

outFile = outDir + "BP_BVRP_SS25_ttm27.csv";
writetable(tb_merged_csv, outFile);