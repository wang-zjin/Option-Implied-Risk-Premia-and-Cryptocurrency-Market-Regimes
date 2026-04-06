

% This file is to plot upper bounds in MATLAB to be consistent with other
% plots format

%% load data
% clear,clc
addpath("m_Files_Color")                 % Add directory to MATLAB's search path for custom color files
addpath("m_Files_Color/colormap")        % Add subdirectory for colormap files
[~,~,~]=mkdir("Upper_Bound/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/"); % Create directory for output, if it doesn't exist

% Read lower bounds of Martin's bounds, Chabi-Yo and Loudis's restricted
% lower bounds and unrestricted lower bounds (based on preference)
UUB = readtable("data_prep/data_BTC/Upper_Bound/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Chabi-Yo_UUB2_restricted.csv");
RUB = readtable("data_prep/data_BTC/Upper_Bound/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Chabi-Yo_RUB2.csv");

tb_VIX_Pdensity_VRP_cluster0 = readtable("data_prep/data_BTC/RiskPremia/multivariate_clustering_9_27_45/Variance_Risk_Premium/VRP_VIX_Pdensity_HV.csv");
tb_VIX_Pdensity_VRP_cluster1 = readtable("data_prep/data_BTC/RiskPremia/multivariate_clustering_9_27_45/Variance_Risk_Premium/VRP_VIX_Pdensity_LV.csv");
tb_VIX_Pdensity_VRP_overall = [tb_VIX_Pdensity_VRP_cluster0;tb_VIX_Pdensity_VRP_cluster1];
tb_VIX_Pdensity_VRP_overall = sortrows(tb_VIX_Pdensity_VRP_overall,"Date");
tb_VIX_Pdensity_VRP_overall.Date = datetime(tb_VIX_Pdensity_VRP_overall.Date, 'ConvertFrom', 'yyyymmdd');

VRP_decomp = readtable("data_prep/data_BTC/Lower_Bound/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/BP_and_VRP_decomposition.xlsx", Sheet='VRP');


%% PLot VRP with MB, UUB and RLB (CL20), CL24, SS2025
% Focus on TTM 27

% Create the figure
figure('Position', [100, 100, 800, 600]);

% plot(MB.Date, MB.Lower_Bound * 100,'-','Color','r','LineWidth',2);hold on
% plot(RLB.Date,RLB.Lower_Bound * 100,'-','Color','g','LineWidth',2);
% plot(tb_VIX_RV_VRP_overall.Date, tb_VIX_RV_VRP_overall.VRP * 100,'-','Color',[0.6941    0.3490    0.1569],'LineWidth',2);hold on 
% plot(tb_VIX_Pdensity_VRP_overall.Date, tb_VIX_Pdensity_VRP_overall.VRP * 100,'-','Color',0.8*[.24 .69 .59],'LineWidth',2); 

plot(tb_VIX_Pdensity_VRP_overall.Date, tb_VIX_Pdensity_VRP_overall.VRP * 100,'-','Color',0.8*[.24 .69 .59],'LineWidth',2); hold on
plot(UUB.Date,-UUB.Upper_Bound * 100,'-','Color',[0.2745    0.5098    0.7059],'LineWidth',2);
plot(RUB.Date,-RUB.Upper_Bound * 100,'-','Color',[0.6196    0.7922    0.8824],'LineWidth',2);
plot(VRP_decomp.date, VRP_decomp.rp_global_sum * 100,'-','Color',[0.6941    0.3490    0.1569],'LineWidth',2);

% plot(ULB.Date,ULB.Lower_Bound * 100,'-','Color',0.8*[.24 .69 .59],'LineWidth',2);
% plot(RLB.Date,RLB.Lower_Bound * 100,'-','Color',[0.2745    0.5098    0.7059],'LineWidth',1.5);

hold off
% grid on
legend(["SS25","CL20U", "CL20R",  "CL24"],'FontSize',15,'Location','northeast','Interpreter','latex','Box','on')

% Formatting the x-axis with yearly intervals (explicit English labels; avoids locale e.g. 2018年)
years = datetime(2017:2022, 1, 1);
xticks(years);
xticklabels(arrayfun(@(y) sprintf('%d', y), 2017:2022, 'UniformOutput', false));

% years = datetime(2017:2022, 1, 1);
% ax = gca;                           % 取当前坐标轴
% ax.XTick = years;                   % 直接给 datetime
% ax.XTickFormat = 'yyyy';            % 只显示年份

% yrs = datenum(2017:2022, 1, 1);
% xticks(yrs);

% Set x-axis limits
xlim([datetime(2017, 07, 01) datetime(2022, 12, 17)]);

% Set y-axis limits
ylim([-120, 350])

% Add labels and title
% xlabel('Date', 'FontSize', 18);
ylabel('Annualized VRP (%)', 'FontSize', 18);
title('Time-Varying Bitcoin VRP', 'FontSize', 18);

% Rotate x-tick labels for better readability
xtickangle(0);

% Add a legend
% legend('Martin (2017) Lower Bound', 'Chabi-Yo & Loudis (2020) Unrestricted Lower Bound', ...
%     'Chabi-Yo & Loudis (2020) Restricted Lower Bound', 'FontSize', 12);

% xlabel('Return','FontSize',15)
% ylabel('PK','FontSize',15)
set(gcf,'Position',[0,0,450,300]);  
ax = gca;
ax.FontSize = 15;
% ax.YAxis.FontWeight = 'bold'; % Make Y-axis tick labels bold
ax.YAxis.LineWidth = 1; % Increase the line width of the Y-axis
ax.XAxis.LineWidth = 1; % Increase the line width of the Y-axis
saveas(gcf,"Upper_Bound/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/VRP_Martin_CL20_CL24_SS25_MATLAB.png")

disp(-mean(UUB.Upper_Bound))

%% PLot VRP with MB, UUB and RLB (CL20), SS2025
% Focus on TTM 27

% Create the figure
figure('Position', [100, 100, 800, 600]);

% plot(MB.Date, MB.Lower_Bound * 100,'-','Color','r','LineWidth',2);hold on
% plot(RLB.Date,RLB.Lower_Bound * 100,'-','Color','g','LineWidth',2);
% plot(tb_VIX_RV_VRP_overall.Date, tb_VIX_RV_VRP_overall.VRP * 100,'-','Color',[0.6941    0.3490    0.1569],'LineWidth',2);hold on 
% plot(tb_VIX_Pdensity_VRP_overall.Date, tb_VIX_Pdensity_VRP_overall.VRP * 100,'-','Color',0.8*[.24 .69 .59],'LineWidth',2); 

plot(tb_VIX_Pdensity_VRP_overall.Date, tb_VIX_Pdensity_VRP_overall.VRP * 100,'-','Color',0.8*[.24 .69 .59],'LineWidth',3); hold on
plot(UUB.Date,-UUB.Upper_Bound * 100,'-','Color',[0.2745    0.5098    0.7059],'LineWidth',3);
plot(RUB.Date,-RUB.Upper_Bound * 100,'-','Color',[0.6196    0.7922    0.8824],'LineWidth',2);

% plot(ULB.Date,ULB.Lower_Bound * 100,'-','Color',0.8*[.24 .69 .59],'LineWidth',2);
% plot(RLB.Date,RLB.Lower_Bound * 100,'-','Color',[0.2745    0.5098    0.7059],'LineWidth',1.5);

hold off
% grid on
legend(["SS25","CL20U", "CL20R"],'FontSize',15,'Location','best','Interpreter','latex','Box','on')

% Formatting the x-axis with yearly intervals (explicit English labels; avoids locale e.g. 2018年)
years = datetime(2017:2022, 1, 1);
xticks(years);
xticklabels(arrayfun(@(y) sprintf('%d', y), 2017:2022, 'UniformOutput', false));

% years = datetime(2017:2022, 1, 1);
% ax = gca;                           % 取当前坐标轴
% ax.XTick = years;                   % 直接给 datetime
% ax.XTickFormat = 'yyyy';            % 只显示年份

% yrs = datenum(2017:2022, 1, 1);
% xticks(yrs);

% Set x-axis limits
xlim([datetime(2017, 07, 01) datetime(2022, 12, 17)]);

% Set y-axis limits
ylim([-120, 350])

% Add labels and title
% xlabel('Date', 'FontSize', 18);
ylabel('Annualized VRP (%)', 'FontSize', 18);
title('Time-Varying Bitcoin VRP', 'FontSize', 18);

% Rotate x-tick labels for better readability
xtickangle(0);

% Add a legend
% legend('Martin (2017) Lower Bound', 'Chabi-Yo & Loudis (2020) Unrestricted Lower Bound', ...
%     'Chabi-Yo & Loudis (2020) Restricted Lower Bound', 'FontSize', 12);

% xlabel('Return','FontSize',15)
% ylabel('PK','FontSize',15)
set(gcf,'Position',[0,0,450,300]);  
ax = gca;
ax.FontSize = 15;
% ax.YAxis.FontWeight = 'bold'; % Make Y-axis tick labels bold
ax.YAxis.LineWidth = 1; % Increase the line width of the Y-axis
ax.XAxis.LineWidth = 1; % Increase the line width of the Y-axis
saveas(gcf,"Upper_Bound/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/VRP_Martin_CL20_SS25_MATLAB.png")

disp(-mean(UUB.Upper_Bound))

