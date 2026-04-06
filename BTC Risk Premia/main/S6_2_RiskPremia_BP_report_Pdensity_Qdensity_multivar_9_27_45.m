% This version is what we use in the draft




% Density analysis
% The script plots Q and P density, P by ePDF (Kernel Density Estimation) with different bandwidths (NB) for Bitcoin Premium 
% It creates a 2x2 subplot for different Time to Maturity (TTM) values, each with multiple ePDF plots using different bandwidths.
%% load data
clear,clc
addpath("m_Files_Color")                 % Add directory to MATLAB's search path for custom color files
addpath("m_Files_Color/colormap")        % Add subdirectory for colormap files
[~,~,~]=mkdir("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/"); % Create directory for output, if it doesn't exist
[~,~,~]=mkdir("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Variance_Risk_Premium/"); % Create directory for output, if it doesn't exist

% Read Bitcoin Premium data from Excel files for different TTM (Time to Maturity) values
Q_P_c0_ttm27=readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/Q_P_ePDF_backward_onlyVR_HV_differentNB_ttm27.xlsx");
Q_P_c1_ttm27=readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/Q_P_ePDF_backward_onlyVR_LV_differentNB_ttm27.xlsx");
Q_P_overall_ttm27=readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/Q_P_ePDF_backward_onlyVR_OA_differentNB_ttm27.xlsx");

ret_simple=Q_P_overall_ttm27.Returns; % Extract simple returns for plotting

IR = readtable("Data/IR_daily.csv");
IR.index=datetime(IR.index);
IR.DTB3=IR.DTB3/100;
IR = renamevars(IR,"index","Date");


tb_VIX_RV_VRP_HV = readtable('RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Variance_Risk_Premium/VRP_VIX_logRV_HV.csv');
tb_VIX_RV_VRP_LV = readtable('RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Variance_Risk_Premium/VRP_VIX_logRV_LV.csv');
dates_HV = tb_VIX_RV_VRP_HV.Date;
dates_LV = tb_VIX_RV_VRP_LV.Date;

IR_HV = innerjoin(IR, tb_VIX_RV_VRP_HV(:,1),"Keys","Date");
IR_LV = innerjoin(IR, tb_VIX_RV_VRP_LV(:,1),"Keys","Date");

%% BP table

% BP: Pdensity - Qdensity

E_P_OA=trapz(ret_simple,ret_simple.*Q_P_overall_ttm27.P_NB12)*365/27;
E_P_HV=trapz(ret_simple,ret_simple.*Q_P_c0_ttm27.P_NB12)*365/27;
E_P_LV=trapz(ret_simple,ret_simple.*Q_P_c1_ttm27.P_NB12)*365/27;

E_Q_OA=trapz(ret_simple,ret_simple.*Q_P_overall_ttm27.Q_overall)*365/27;
E_Q_HV=trapz(ret_simple,ret_simple.*Q_P_c0_ttm27.Q_cluster0)*365/27;
E_Q_LV=trapz(ret_simple,ret_simple.*Q_P_c1_ttm27.Q_cluster1)*365/27;

BP_density_cluster=nan(3,3);
BP_density_cluster(1,:)=[E_P_OA,E_P_HV,E_P_LV];
BP_density_cluster(2,:)=[E_Q_OA,E_Q_HV,E_Q_LV];
BP_density_cluster(3,:)=BP_density_cluster(1,:)-BP_density_cluster(2,:);
BP_density_cluster = BP_density_cluster([3,1,2],:);
clear info;
info.rnames = strvcat('.','E_P-E_Q','E_P: P density','E_Q: Q density');
info.cnames = strvcat('Overall','Cluster 0','Cluster 1');
info.fmt    = '%10.2f';
mprint(BP_density_cluster,info)

%% Price of Risk: \int_{shadow}q / \int_{shadow}p
shadow_x_negative = [-0.6, -0.2];
shadow_x_positive = [0.2, 0.6];
% left shadow
index = (ret_simple>=shadow_x_negative(1) & ret_simple<=shadow_x_negative(2));
ret_subinterval = ret_simple(index, :);
q_subinterval = Q_P_overall_ttm27.Q_overall(index, :);
p_subinterval = Q_P_overall_ttm27.P_NB12(index, :);
q_int_nega = trapz(ret_subinterval,ret_subinterval.*q_subinterval);
p_int_nega = trapz(ret_subinterval,ret_subinterval.*p_subinterval);
Price_of_Risk_nega = q_int_nega / p_int_nega;

% right shadow
index = (ret_simple>=shadow_x_positive(1) & ret_simple<=shadow_x_positive(2));
ret_subinterval = ret_simple(index, :);
q_subinterval = Q_P_overall_ttm27.Q_overall(index, :);
p_subinterval = Q_P_overall_ttm27.P_NB12(index, :);
q_int_posi = trapz(ret_subinterval,ret_subinterval.*q_subinterval);
p_int_posi = trapz(ret_subinterval,ret_subinterval.*p_subinterval);
Price_of_Risk_posi = q_int_posi / p_int_posi;

Risk_Price_cluster=nan(4,2);
Risk_Price_cluster(1,:)=[q_int_nega,q_int_posi];
Risk_Price_cluster(2,:)=[p_int_nega,p_int_posi];
Risk_Price_cluster(3,:)=[Price_of_Risk_nega,Price_of_Risk_posi];

%% Another Price of Risk: |\int_{shadow}PK|
% left shadow
index = (ret_simple>=shadow_x_negative(1) & ret_simple<=shadow_x_negative(2));
ret_subinterval = ret_simple(index, :);
q_subinterval = Q_P_overall_ttm27.Q_overall(index, :);
p_subinterval = Q_P_overall_ttm27.P_NB12(index, :);
PK = log(q_subinterval./p_subinterval);
Price_of_Risk_nega = abs(trapz(ret_subinterval,ret_subinterval.*PK));

% right shadow
index = (ret_simple>=shadow_x_positive(1) & ret_simple<=shadow_x_positive(2));
ret_subinterval = ret_simple(index, :);
q_subinterval = Q_P_overall_ttm27.Q_overall(index, :);
p_subinterval = Q_P_overall_ttm27.P_NB12(index, :);
PK = log(q_subinterval./p_subinterval);
Price_of_Risk_posi = abs(trapz(ret_subinterval,ret_subinterval.*PK));

% Risk_Price_cluster=nan(1,2);
Risk_Price_cluster(4,:)=[Price_of_Risk_nega,Price_of_Risk_posi];
clear info;
% info.rnames = strvcat('.','\int_{shadow}log(PK)dR');
info.rnames = strvcat('.','\int_{shadow}q(R)dR','\int_{shadow}p(R)dR','\int_{shadow}q(R)dR / \int_{shadow}p(R)dR','|\int_{shadow}log(PK)dR|');
info.cnames = strvcat('Negative [-0.6,-0.2]','Positive [0.2,0.6]');
info.fmt    = '%10.2f';
mprint(Risk_Price_cluster,info)

%% Plot PK of OA, HV, LV in the same figure
% Focus on TTM 27
figure;

plot(nan,nan,'-.','Color','k','LineWidth',2);hold on
plot(nan,nan,'-.','Color','b','LineWidth',2);
plot(nan,nan,'-.','Color','r','LineWidth',2);

plot(ret_simple,Q_P_overall_ttm27.Q_overall./Q_P_overall_ttm27.P_NB12,'-.','Color','k','LineWidth',2);
plot(ret_simple,Q_P_c0_ttm27.Q_cluster0./Q_P_c0_ttm27.P_NB12,'-.','Color','b','LineWidth',2);
plot(ret_simple,Q_P_c1_ttm27.Q_cluster1./Q_P_c1_ttm27.P_NB12,'-.','Color','r','LineWidth',2);

hold off
% grid on
legend(["$\widehat{PK}_{OA}$","$\widehat{PK}_{HV}$","$\widehat{PK}_{LV}$"],'FontSize',15,'Location','northeast','Interpreter','latex','Box','off')
ylim([0,4])
xlim([-1,1])
xticks([-1,-0.8,-0.6,-0.4,-0.2,0,0.2,0.4,0.6,0.8,1])
xlabel('Return','FontSize',15)
% ylabel('PK','FontSize',15)
set(gcf,'Position',[0,0,450,300]);  
ax = gca;
ax.FontSize = 15;
% ax.YAxis.FontWeight = 'bold'; % Make Y-axis tick labels bold
ax.YAxis.LineWidth = 1; % Increase the line width of the Y-axis
ax.XAxis.LineWidth = 1; % Increase the line width of the Y-axis
saveas(gcf,"RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/PK_ePDF_backward_onlyVR_NB12_OAc0c1_ttm27_1-by-1.png")

%% Plot P of OA, HV, LV in the same figure
% Focus on TTM 27
figure;

plot(nan,nan,'-.','Color','k','LineWidth',2);hold on
plot(nan,nan,'-.','Color','b','LineWidth',2);
plot(nan,nan,'-.','Color','r','LineWidth',2);

plot(ret_simple,Q_P_overall_ttm27.P_NB12,'-.','Color','k','LineWidth',2);
plot(ret_simple,Q_P_c0_ttm27.P_NB12,'-.','Color','b','LineWidth',2);
plot(ret_simple,Q_P_c1_ttm27.P_NB12,'-.','Color','r','LineWidth',2);

hold off
% grid on
legend(["$\widehat{P}_{OA}$","$\widehat{P}_{HV}$","$\widehat{P}_{LV}$"],'FontSize',15,'Location','northeast','Interpreter','latex','Box','off')
ylim([0,4])
xlim([-1,1])
xticks([-1,-0.8,-0.6,-0.4,-0.2,0,0.2,0.4,0.6,0.8,1])
xlabel('Return','FontSize',15)
% ylabel('PK','FontSize',15)
set(gcf,'Position',[0,0,450,300]);  
ax = gca;
ax.FontSize = 15;
% ax.YAxis.FontWeight = 'bold'; % Make Y-axis tick labels bold
ax.YAxis.LineWidth = 1; % Increase the line width of the Y-axis
ax.XAxis.LineWidth = 1; % Increase the line width of the Y-axis

%% Plot Q of OA, HV, LV in the same figure
% Focus on TTM 27
figure;

plot(nan,nan,'-.','Color','k','LineWidth',2);hold on
plot(nan,nan,'-.','Color','b','LineWidth',2);
plot(nan,nan,'-.','Color','r','LineWidth',2);

plot(ret_simple,Q_P_overall_ttm27.Q_overall,'-.','Color','k','LineWidth',2);
plot(ret_simple,Q_P_c0_ttm27.Q_cluster0,'-.','Color','b','LineWidth',2);
plot(ret_simple,Q_P_c1_ttm27.Q_cluster1,'-.','Color','r','LineWidth',2);

hold off
% grid on
legend(["$\widehat{Q}_{OA}$","$\widehat{Q}_{HV}$","$\widehat{Q}_{LV}$"],'FontSize',15,'Location','northeast','Interpreter','latex','Box','off')
ylim([0,4])
xlim([-1,1])
xticks([-1,-0.8,-0.6,-0.4,-0.2,0,0.2,0.4,0.6,0.8,1])
xlabel('Return','FontSize',15)
% ylabel('PK','FontSize',15)
set(gcf,'Position',[0,0,450,300]);  
ax = gca;
ax.FontSize = 15;
% ax.YAxis.FontWeight = 'bold'; % Make Y-axis tick labels bold
ax.YAxis.LineWidth = 1; % Increase the line width of the Y-axis
ax.XAxis.LineWidth = 1; % Increase the line width of the Y-axis