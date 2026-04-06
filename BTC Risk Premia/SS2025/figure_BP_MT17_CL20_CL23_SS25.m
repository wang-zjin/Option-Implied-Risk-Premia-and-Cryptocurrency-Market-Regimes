

% This file is to plot lower bounds in MATLAB to be consistent with other
% plots format

%% load data
%clear,clc
addpath("m_Files_Color")                 % Add directory to MATLAB's search path for custom color files
addpath("m_Files_Color/colormap")        % Add subdirectory for colormap files
[~,~,~]=mkdir("Lower_Bound/multivariate_clustering_9_27_45/"); % Create directory for output, if it doesn't exist

% Read lower bounds of Martin's bounds, Chabi-Yo and Loudis's restricted
% lower bounds and unrestricted lower bounds (based on preference)
MB = readtable("data_prep/data_BTC/Lower_Bound/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Martin_LB.csv");
RLB = readtable("data_prep/data_BTC/Lower_Bound/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Chabi-Yo_RLB.csv");
ULB = readtable("data_prep/data_BTC/Lower_Bound/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Chabi-Yo_ULB_restricted.csv");

BP_decomp = readtable("data_prep/data_BTC/Lower_Bound/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/BP_and_VRP_decomposition.xlsx", Sheet='BP');
VRP_decomp = readtable("data_prep/data_BTC/Lower_Bound/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/BP_and_VRP_decomposition.xlsx", Sheet='VRP');

% %% PLot lower bounds with only MB and RLB
% % Focus on TTM 27
% shadow_x_negative = [-0.6, -0.2];
% shadow_x_positive = [0.2, 0.6];
% 
% % Create the figure
% figure('Position', [100, 100, 800, 600]);
% 
% plot(MB.Date, MB.Lower_Bound * 100,'-','Color',[0.4667    0.5333    0.6000],'LineWidth',2);hold on
% plot(RLB.Date,RLB.Lower_Bound * 100,'-','Color',[0.2745    0.5098    0.7059],'LineWidth',2);
% hold off
% % grid on
% legend(["Martin","ULB","RLB"],'FontSize',15,'Location','northwest','Interpreter','latex','Box','off')
% 
% % Formatting the x-axis with yearly intervals
% years = datetime(2017:2022, 1, 1);
% xticks(years);
% 
% % years = datetime(2017:2022, 1, 1);
% % ax = gca;                           % 取当前坐标轴
% % ax.XTick = years;                   % 直接给 datetime
% % ax.XTickFormat = 'yyyy';            % 只显示年份
% 
% % yrs = datenum(2017:2022, 1, 1);
% % xticks(yrs);
% 
% % Set x-axis limits
% xlim([datetime(2017, 07, 01) datetime(2022, 12, 17)]);
% 
% % Set y-axis limits
% ylim([0, 349])
% 
% % Add labels and title
% % xlabel('Date', 'FontSize', 18);
% ylabel('Annualized Lower Bound (%)', 'FontSize', 18);
% % title('Time-Varying Lower Bound of Bitcoin Premium (BP)', 'FontSize', 18);
% 
% % % Rotate x-tick labels for better readability
% % xtickangle(45);
% 
% % Add a legend
% legend('Martin (2017)', 'Chabi-Yo and Loudis (2020)', 'FontSize', 12, 'box', 'on', 'location', 'northeast');
% 
% % ylabel('PK','FontSize',15)
% set(gcf,'Position',[0,0,450,300]);  
% ax = gca;
% ax.FontSize = 15;
% % ax.YAxis.FontWeight = 'bold'; % Make Y-axis tick labels bold
% ax.YAxis.LineWidth = 1; % Increase the line width of the Y-axis
% ax.XAxis.LineWidth = 1; % Increase the line width of the Y-axis
% saveas(gcf,"Lower_Bound/multivariate_clustering_9_27_45/Martin_Chabi-Yo_RLB_Preference_LB_MATLAB.png")

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

% Robust to numeric yyyymmdd, datetime, or char/string/cell (avoids num2str on non-numeric dates)
if isdatetime(dates)
    dates_datetime = dates;
elseif isnumeric(dates)
    dates_datetime = datetime(dates, 'ConvertFrom', 'yyyymmdd', 'Format', 'uuuu-MM-dd');
else
    dates_datetime = datetime(dates, 'InputFormat', 'yyyyMMdd', 'Format', 'uuuu-MM-dd');
end
datesNum = datenum(dates_datetime);
%% Plot BP using Martin2017 CL2020 CL2023 SS2025
shadow_x_negative = [-0.6, -0.2];
shadow_x_positive = [0.2, 0.6];

% Create the figure
figure('Position', [100, 100, 800, 600]);

% plot(dates_datetime,1200*(ER_P-ER_Q),'color',0.8*[.24 .69 .59],'LineWidth',2); hold on
plot(dates_datetime,365/27*(ER_P-ER_Q) * 100,'color',0.8*[.24 .69 .59],'LineWidth',2); hold on
plot(MB.Date, MB.Lower_Bound * 100,'-','Color',[0.4157    0.2392    0.6039],'LineWidth',2);
plot(ULB.Date,ULB.Lower_Bound * 100,'-','Color',[0.2745    0.5098    0.7059],'LineWidth',2);
plot(RLB.Date,RLB.Lower_Bound * 100,'-','Color',[0.6196    0.7922    0.8824],'LineWidth',1.5);
plot(BP_decomp.date,BP_decomp.rp_global_sum * 100,'-','Color',[0.6941    0.3490    0.1569],'LineWidth',1);
% 0.7412    0.7412    0.7412
%ylim([0,50]); 
hold off

% Formatting the x-axis with yearly intervals
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
ylim([0, 450])

% Add labels and title
% xlabel('Date', 'FontSize', 18);
ylabel('Annualized BP (%)', 'FontSize', 18);
title('Time-Varying Bitcoin Premium', 'FontSize', 18);

% % Rotate x-tick labels for better readability
% xtickangle(45);

% Add a legend
legend('SS25', 'MT17', 'CL20U', 'CL20R', 'CL24', 'FontSize', 12, 'box', 'on', 'location', 'northeast');

% ylabel('PK','FontSize',15)
set(gcf,'Position',[0,0,450,300]);  
ax = gca;
ax.FontSize = 15;
% ax.YAxis.FontWeight = 'bold'; % Make Y-axis tick labels bold
ax.YAxis.LineWidth = 1; % Increase the line width of the Y-axis
ax.XAxis.LineWidth = 1; % Increase the line width of the Y-axis
saveas(gcf,"Lower_Bound/multivariate_clustering_9_27_45/BP_Martin2017_CL2020_CL2023_SS2025.png")

%% Plot BP using Martin2017 CL2020 SS2025
shadow_x_negative = [-0.6, -0.2];
shadow_x_positive = [0.2, 0.6];

% Create the figure
figure('Position', [100, 100, 800, 600]);

% plot(dates_datetime,1200*(ER_P-ER_Q),'color',0.8*[.24 .69 .59],'LineWidth',2); hold on
plot(dates_datetime,365/27*(ER_P-ER_Q) * 100,'color',0.8*[.24 .69 .59],'LineWidth',2); hold on
plot(MB.Date, MB.Lower_Bound * 100,'-','Color',[0.4157    0.2392    0.6039],'LineWidth',2);
plot(ULB.Date,ULB.Lower_Bound * 100,'-','Color',[0.2745    0.5098    0.7059],'LineWidth',2);
plot(RLB.Date,RLB.Lower_Bound * 100,'-','Color',[0.6196    0.7922    0.8824],'LineWidth',1.5);
% 0.7412    0.7412    0.7412
%ylim([0,50]); 
hold off

% Formatting the x-axis with yearly intervals
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
ylim([0, 450])

% Add labels and title
% xlabel('Date', 'FontSize', 18);
ylabel('Annualized BP (%)', 'FontSize', 18);
title('Time-Varying Bitcoin Premium', 'FontSize', 18);

% % Rotate x-tick labels for better readability
% xtickangle(45);

% Add a legend
legend('SS25', 'MT17', 'CL20U', 'CL20R', 'FontSize', 12, 'box', 'on', 'location', 'northeast');

% ylabel('PK','FontSize',15)
set(gcf,'Position',[0,0,450,300]);  
ax = gca;
ax.FontSize = 15;
% ax.YAxis.FontWeight = 'bold'; % Make Y-axis tick labels bold
ax.YAxis.LineWidth = 1; % Increase the line width of the Y-axis
ax.XAxis.LineWidth = 1; % Increase the line width of the Y-axis
saveas(gcf,"Lower_Bound/multivariate_clustering_9_27_45/BP_Martin2017_CL2020_SS2025.png")