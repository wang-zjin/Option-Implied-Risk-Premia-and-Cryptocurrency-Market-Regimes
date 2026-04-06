



% Bitcoin Premium (BP) Analysis
% The script plots ePDF (Kernel Density Estimation) with different bandwidths (BW) for Bitcoin Premium 
% It creates a 4x3 subplot for different Time to Maturity (TTM) values, each with multiple ePDF plots using different bandwidths.
%% load data
clear,clc
addpath("m_Files_Color")                 % Add directory to MATLAB's search path for custom color files
addpath("m_Files_Color/colormap")        % Add subdirectory for colormap files
[~,~,~]=mkdir("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/"); % Create directory for output, if it doesn't exist

% Read Bitcoin Premium data from Excel files for different TTM (Time to Maturity) values
BP_overall_ttm27=readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/BP_SCA_ePDF_backward_onlyVR_OA_differentNB_ttm27.xlsx");
BP_c0_ttm27=readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/BP_SCA_ePDF_backward_onlyVR_HV_differentNB_ttm27.xlsx");
BP_c1_ttm27=readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/BP_SCA_ePDF_backward_onlyVR_LV_differentNB_ttm27.xlsx");

% Read Q and P density from Excel files for different TTM (Time to Maturity) values
Q_P_c0_ttm27=readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/Q_P_ePDF_backward_onlyVR_HV_differentNB_ttm27.xlsx");
Q_P_c1_ttm27=readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/Q_P_ePDF_backward_onlyVR_LV_differentNB_ttm27.xlsx");
Q_P_overall_ttm27=readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/Q_P_ePDF_backward_onlyVR_OA_differentNB_ttm27.xlsx");

ret_simple=BP_c0_ttm27.Returns; % Extract simple returns for plotting

%% Plot BP overall
shadow_x_negative = [-0.6, -0.2];
shadow_x_positive = [0.2, 0.6];

BP = BP_overall_ttm27.BP_NB12;
Q_density = Q_P_overall_ttm27.Q_overall;
P_density = Q_P_overall_ttm27.P_NB12;
PK = Q_density ./ P_density;

BP_sub1 = BP(ret_simple>=shadow_x_negative(1) & ret_simple<=shadow_x_negative(2));
BP_sub2 = BP(ret_simple>=shadow_x_positive(1) & ret_simple<=shadow_x_positive(2));
ret_sub1 = ret_simple(ret_simple>=shadow_x_negative(1) & ret_simple<=shadow_x_negative(2));
ret_sub2 = ret_simple(ret_simple>=shadow_x_positive(1) & ret_simple<=shadow_x_positive(2));
P_density_sub1 = P_density(ret_simple>=shadow_x_negative(1) & ret_simple<=shadow_x_negative(2));
P_density_sub2 = P_density(ret_simple>=shadow_x_positive(1) & ret_simple<=shadow_x_positive(2));
Q_density_sub1 = Q_density(ret_simple>=shadow_x_negative(1) & ret_simple<=shadow_x_negative(2));
Q_density_sub2 = Q_density(ret_simple>=shadow_x_positive(1) & ret_simple<=shadow_x_positive(2));
P_integral_sub1 = trapz(ret_sub1, P_density_sub1);
P_integral_sub2 = trapz(ret_sub2, P_density_sub2);
Q_integral_sub1 = trapz(ret_sub1, Q_density_sub1);
Q_integral_sub2 = trapz(ret_sub2, Q_density_sub2);

PK_sub1 = PK(ret_simple>=shadow_x_negative(1) & ret_simple<=shadow_x_negative(2));
PK_sub2 = PK(ret_simple>=shadow_x_positive(1) & ret_simple<=shadow_x_positive(2));
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

disp("Overall, BP between -80% and -50% is:")
BP_sub = BP(ret_simple>=-0.8 & ret_simple<=-0.5);
disp(BP_sub(end)-BP_sub(1))

disp("Overall, BP between -80% and -60% is:")
BP_sub = BP(ret_simple>=-0.8 & ret_simple<=-0.6);
disp(BP_sub(end)-BP_sub(1))

%% Plot BP for HV cluster 
shadow_x_negative = [-0.6, -0.2];
shadow_x_positive = [0.2, 0.6];

BP = BP_c0_ttm27.BP_NB12;
Q_density = Q_P_c0_ttm27.Q_cluster0;
P_density = Q_P_c0_ttm27.P_NB12;
PK = Q_density ./ P_density;

BP_sub1 = BP(ret_simple>=shadow_x_negative(1) & ret_simple<=shadow_x_negative(2));
BP_sub2 = BP(ret_simple>=shadow_x_positive(1) & ret_simple<=shadow_x_positive(2));
ret_sub1 = ret_simple(ret_simple>=shadow_x_negative(1) & ret_simple<=shadow_x_negative(2));
ret_sub2 = ret_simple(ret_simple>=shadow_x_positive(1) & ret_simple<=shadow_x_positive(2));
P_density_sub1 = P_density(ret_simple>=shadow_x_negative(1) & ret_simple<=shadow_x_negative(2));
P_density_sub2 = P_density(ret_simple>=shadow_x_positive(1) & ret_simple<=shadow_x_positive(2));
Q_density_sub1 = Q_density(ret_simple>=shadow_x_negative(1) & ret_simple<=shadow_x_negative(2));
Q_density_sub2 = Q_density(ret_simple>=shadow_x_positive(1) & ret_simple<=shadow_x_positive(2));
P_integral_sub1 = trapz(ret_sub1, P_density_sub1);
P_integral_sub2 = trapz(ret_sub2, P_density_sub2);
Q_integral_sub1 = trapz(ret_sub1, Q_density_sub1);
Q_integral_sub2 = trapz(ret_sub2, Q_density_sub2);

PK_sub1 = PK(ret_simple>=shadow_x_negative(1) & ret_simple<=shadow_x_negative(2));
PK_sub2 = PK(ret_simple>=shadow_x_positive(1) & ret_simple<=shadow_x_positive(2));
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

disp("For HV, BP between -80% and -50% is:")
BP_sub = BP(ret_simple>=-0.8 & ret_simple<=-0.5);
disp(BP_sub(end)-BP_sub(1))

disp("For HV, BP between -80% and -60% is:")
BP_sub = BP(ret_simple>=-0.8 & ret_simple<=-0.6);
disp(BP_sub(end)-BP_sub(1))

%% Plot BP for LV cluster
shadow_x_negative = [-0.6, -0.2];
shadow_x_positive = [0.2, 0.6];

BP = BP_c1_ttm27.BP_NB12;
Q_density = Q_P_c1_ttm27.Q_cluster1;
P_density = Q_P_c1_ttm27.P_NB12;
PK = Q_density ./ P_density;

BP_sub1 = BP(ret_simple>=shadow_x_negative(1) & ret_simple<=shadow_x_negative(2));
BP_sub2 = BP(ret_simple>=shadow_x_positive(1) & ret_simple<=shadow_x_positive(2));
ret_sub1 = ret_simple(ret_simple>=shadow_x_negative(1) & ret_simple<=shadow_x_negative(2));
ret_sub2 = ret_simple(ret_simple>=shadow_x_positive(1) & ret_simple<=shadow_x_positive(2));
P_density_sub1 = P_density(ret_simple>=shadow_x_negative(1) & ret_simple<=shadow_x_negative(2));
P_density_sub2 = P_density(ret_simple>=shadow_x_positive(1) & ret_simple<=shadow_x_positive(2));
Q_density_sub1 = Q_density(ret_simple>=shadow_x_negative(1) & ret_simple<=shadow_x_negative(2));
Q_density_sub2 = Q_density(ret_simple>=shadow_x_positive(1) & ret_simple<=shadow_x_positive(2));
P_integral_sub1 = trapz(ret_sub1, P_density_sub1);
P_integral_sub2 = trapz(ret_sub2, P_density_sub2);
Q_integral_sub1 = trapz(ret_sub1, Q_density_sub1);
Q_integral_sub2 = trapz(ret_sub2, Q_density_sub2);

PK_sub1 = PK(ret_simple>=shadow_x_negative(1) & ret_simple<=shadow_x_negative(2));
PK_sub2 = PK(ret_simple>=shadow_x_positive(1) & ret_simple<=shadow_x_positive(2));
% PK_integral_sub1 = abs(trapz(ret_sub1, log(PK_sub1)));
% PK_integral_sub2 = abs(trapz(ret_sub2, log(PK_sub2)));
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

disp("For LV, BP between -80% and -50% is:")
BP_sub = BP(ret_simple>=-0.8 & ret_simple<=-0.5);
disp(BP_sub(end)-BP_sub(1))

disp("For LV, BP between -80% and -60% is:")
BP_sub = BP(ret_simple>=-0.8 & ret_simple<=-0.6);
disp(BP_sub(end)-BP_sub(1))

%% Report
Influential_return_state_table = [OA;HV;LV];
info.rnames = strvcat('.','OA','HV','LV');
info.cnames = strvcat('BP(-0.2)-BP(-0.6)','int_-0.6^-0.2p','q/p','BP(0.6)-BP(0.2)','int_0.2^0.6p','q/p');
info.fmt    = '%10.3f';
disp('Influential return state table')
mprint(Influential_return_state_table,info)

%% Report
Influential_return_state_table = [OA1;HV1;LV1];
info.rnames = strvcat('.','OA','HV','LV');
info.cnames = strvcat('BP(-0.2)-BP(-0.6)','int_-0.6^-0.2p','int_-0.6^-0.2q','q/p','BP(0.6)-BP(0.2)','int_0.2^0.6p','int_-0.6^-0.2q','q/p');
info.fmt    = '%10.3f';
disp('Influential return state table')
mprint(Influential_return_state_table,info)

%% Report
Influential_return_state_table = [OA2;HV2;LV2];
info.rnames = strvcat('.','OA','HV','LV');
% info.cnames = strvcat('BP(-0.2)-BP(-0.6)','|int_log(pk)|','BP(0.6)-BP(0.2)','|int_log(pk)|');
info.cnames = strvcat('BP(-0.2)-BP(-0.6)','|int_pk|','|int_pk|/0.3','BP(0.6)-BP(0.2)','|int_pk|','|int_pk|/0.4');
info.fmt    = '%10.6f';
disp('Influential return state table')
mprint(Influential_return_state_table,info)
