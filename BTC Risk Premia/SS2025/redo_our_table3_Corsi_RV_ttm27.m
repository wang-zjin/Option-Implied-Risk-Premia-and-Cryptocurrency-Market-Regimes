





%% Load cluster
common_dates = readtable('data_prep/data_BTC/common_dates_cluster.csv');
common_dates.Date = str2num(datestr(datetime(common_dates.Date, "Format","uuuuMMdd", "InputFormat", "uuuu-MM-dd"), 'yyyymmdd'));
dates = string(common_dates.Date);
dates_list = datetime(dates, "InputFormat","uuuuMMdd", "Format", "yyyymmdd");
index0 = common_dates.Cluster==0;
index1 = common_dates.Cluster==1;
dates_Q{1,1} = dates_list(index0);
dates_Q{1,2} = dates_list(index1);

IR = readtable("data_prep/data_BTC/IR_daily.csv");
IR.index=datetime(IR.index);
IR.DTB3=IR.DTB3/100;
IR = renamevars(IR,"index","Date");

index_IR = ismember(IR.Date, dates_list);
IR = IR.DTB3(index_IR);

%% Calculate BP
% Read Bitcoin Premium data from Excel files for different TTM (Time to Maturity) values
BP_overall_ttm27=readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/BP_ePDF_Corsi_RV_OA_differentNB_ttm27.xlsx");
BP_c0_ttm27=readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/BP_ePDF_Corsi_RV_HV_differentNB_ttm27.xlsx");
BP_c1_ttm27=readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/BP_ePDF_Corsi_RV_LV_differentNB_ttm27.xlsx");

ret_simple=BP_c0_ttm27.Returns; % Extract simple returns for plotting

BP_overall = BP_overall_ttm27.BP_NB12;
BP_HV = BP_c0_ttm27.BP_NB12;
BP_LV = BP_c1_ttm27.BP_NB12;

PQ_overall_ttm27 = readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/Q_P_ePDF_Corsi_RV_OA_differentNB_ttm27.xlsx");
PQ_HV_ttm27 = readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/Q_P_ePDF_Corsi_RV_HV_differentNB_ttm27.xlsx");
PQ_LV_ttm27 = readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/Q_P_ePDF_Corsi_RV_LV_differentNB_ttm27.xlsx");

% fQ_overall = mean(fQ, 1);
% fQ_HV = mean(fQ(index0,:), 1);
% fQ_LV = mean(fQ(index1,:), 1);

fQ_overall = PQ_overall_ttm27.Q_overall;
fQ_HV = PQ_HV_ttm27.Q_cluster0;
fQ_LV = PQ_LV_ttm27.Q_cluster1;

fP_overall = PQ_overall_ttm27.P_NB12;
fP_HV = PQ_HV_ttm27.P_NB10;
fP_LV = PQ_LV_ttm27.P_NB10;



%% Plot BP overall
shadow_x_negative = [-0.6, -0.2];
shadow_x_positive = [0.2, 0.6];

BP = BP_overall;
Q_density = fQ_overall;
P_density = fP_overall;
PK = Q_density ./ P_density;

BP_sub1 = BP(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
BP_sub2 = BP(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
ret_sub1 = R_vec(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
ret_sub2 = R_vec(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
P_density_sub1 = P_density(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
P_density_sub2 = P_density(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
Q_density_sub1 = Q_density(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
Q_density_sub2 = Q_density(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
P_integral_sub1 = trapz(ret_sub1, P_density_sub1);
P_integral_sub2 = trapz(ret_sub2, P_density_sub2);
Q_integral_sub1 = trapz(ret_sub1, Q_density_sub1);
Q_integral_sub2 = trapz(ret_sub2, Q_density_sub2);

PK_sub1 = PK(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
PK_sub2 = PK(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
PK_integral_sub1 = abs(trapz(ret_sub1, PK_sub1));
PK_integral_sub2 = abs(trapz(ret_sub2, PK_sub2));
PK_average_sub1 = PK_integral_sub1 / (shadow_x_negative(2)-shadow_x_negative(1));
PK_average_sub2 = PK_integral_sub2 / (shadow_x_positive(2)-shadow_x_positive(1));

OA = [BP_sub1(end)-BP_sub1(1), P_integral_sub1, Q_integral_sub1/P_integral_sub1,...
    BP_sub2(end)-BP_sub2(1), P_integral_sub2, Q_integral_sub2/P_integral_sub2];

OA1 = [BP_sub1(end)-BP_sub1(1), P_integral_sub1, Q_integral_sub1, Q_integral_sub1/P_integral_sub1,...
    BP_sub2(end)-BP_sub2(1), P_integral_sub2, Q_integral_sub2, Q_integral_sub2/P_integral_sub2];

OA2 = [BP_sub1(end)-BP_sub1(1), PK_integral_sub1,PK_average_sub1,...
    BP_sub2(end)-BP_sub2(1), PK_integral_sub2,PK_average_sub2];

PKlog_sub1 = log(PK_sub1);
PKlog_sub2 = log(PK_sub2);

AKA_sub1 = -gradient(PKlog_sub1, ret_sub1);
AKA_sub2 = -gradient(PKlog_sub2, ret_sub2);
disp([mean(AKA_sub1),mean(AKA_sub2)])

%% Plot BP for 2 HV cluster 
shadow_x_negative = [-0.6, -0.2];
shadow_x_positive = [0.2, 0.6];

BP = BP_HV;
Q_density = fQ_HV;
P_density = fQ_LV;
PK = Q_density ./ P_density;

BP_sub1 = BP(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
BP_sub2 = BP(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
ret_sub1 = R_vec(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
ret_sub2 = R_vec(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
P_density_sub1 = P_density(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
P_density_sub2 = P_density(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
Q_density_sub1 = Q_density(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
Q_density_sub2 = Q_density(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
P_integral_sub1 = trapz(ret_sub1, P_density_sub1);
P_integral_sub2 = trapz(ret_sub2, P_density_sub2);
Q_integral_sub1 = trapz(ret_sub1, Q_density_sub1);
Q_integral_sub2 = trapz(ret_sub2, Q_density_sub2);

PK_sub1 = PK(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
PK_sub2 = PK(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
% PK_integral_sub1 = abs(trapz(ret_sub1, log(PK_sub1)));
% PK_integral_sub2 = abs(trapz(ret_sub2, log(PK_sub2)));
PK_integral_sub1 = abs(trapz(ret_sub1, PK_sub1));
PK_integral_sub2 = abs(trapz(ret_sub2, PK_sub2));
PK_average_sub1 = PK_integral_sub1 / (shadow_x_negative(2)-shadow_x_negative(1));
PK_average_sub2 = PK_integral_sub2 / (shadow_x_positive(2)-shadow_x_positive(1));

HV = [BP_sub1(end)-BP_sub1(1), P_integral_sub1, Q_integral_sub1/P_integral_sub1,...
    BP_sub2(end)-BP_sub2(1), P_integral_sub2, Q_integral_sub2/P_integral_sub2];

HV1 = [BP_sub1(end)-BP_sub1(1), P_integral_sub1, Q_integral_sub1, Q_integral_sub1/P_integral_sub1,...
    BP_sub2(end)-BP_sub2(1), P_integral_sub2, Q_integral_sub2, Q_integral_sub2/P_integral_sub2];

HV2 = [BP_sub1(end)-BP_sub1(1), PK_integral_sub1,PK_average_sub1,...
    BP_sub2(end)-BP_sub2(1), PK_integral_sub2,PK_average_sub2];

PKlog_sub1 = log(PK_sub1);
PKlog_sub2 = log(PK_sub2);

AKA_sub1 = -gradient(PKlog_sub1, ret_sub1);
AKA_sub2 = -gradient(PKlog_sub2, ret_sub2);
disp([mean(AKA_sub1),mean(AKA_sub2)])

%% Plot BP for 2 LV cluster
shadow_x_negative = [-0.6, -0.2];
shadow_x_positive = [0.2, 0.6];

BP = BP_LV;
Q_density = fQ_LV;
P_density = fP_LV;
PK = Q_density ./ P_density;

BP_sub1 = BP(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
BP_sub2 = BP(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
ret_sub1 = R_vec(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
ret_sub2 = R_vec(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
P_density_sub1 = P_density(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
P_density_sub2 = P_density(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
Q_density_sub1 = Q_density(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
Q_density_sub2 = Q_density(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
P_integral_sub1 = trapz(ret_sub1, P_density_sub1);
P_integral_sub2 = trapz(ret_sub2, P_density_sub2);
Q_integral_sub1 = trapz(ret_sub1, Q_density_sub1);
Q_integral_sub2 = trapz(ret_sub2, Q_density_sub2);

PK_sub1 = PK(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
PK_sub2 = PK(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
PK_integral_sub1 = abs(trapz(ret_sub1, PK_sub1));
PK_integral_sub2 = abs(trapz(ret_sub2, PK_sub2));
PK_average_sub1 = PK_integral_sub1 / (shadow_x_negative(2)-shadow_x_negative(1));
PK_average_sub2 = PK_integral_sub2 / (shadow_x_positive(2)-shadow_x_positive(1));

LV = [BP_sub1(end)-BP_sub1(1), P_integral_sub1, Q_integral_sub1/P_integral_sub1,...
    BP_sub2(end)-BP_sub2(1), P_integral_sub2, Q_integral_sub2/P_integral_sub2];

LV1 = [BP_sub1(end)-BP_sub1(1), P_integral_sub1, Q_integral_sub1, Q_integral_sub1/P_integral_sub1,...
    BP_sub2(end)-BP_sub2(1), P_integral_sub2, Q_integral_sub2, Q_integral_sub2/P_integral_sub2];

LV2 = [BP_sub1(end)-BP_sub1(1), PK_integral_sub1,PK_average_sub1,...
    BP_sub2(end)-BP_sub2(1), PK_integral_sub2,PK_average_sub2];

PKlog_sub1 = log(PK_sub1);
PKlog_sub2 = log(PK_sub2);

AKA_sub1 = -gradient(PKlog_sub1, ret_sub1);
AKA_sub2 = -gradient(PKlog_sub2, ret_sub2);
disp([mean(AKA_sub1),mean(AKA_sub2)])

%% Report
Influential_return_state_table = [OA;HV;LV];
info.rnames = strvcat('.','OA','HV','LV');
info.cnames = strvcat('BP(-0.2)-BP(-0.6)','int_-0.6^-0.2p','q/p','BP(0.6)-BP(0.2)','int_0.2^0.6p','q/p');
info.fmt    = '%10.4f';
disp('Influential return state table')
mprint(Influential_return_state_table,info)