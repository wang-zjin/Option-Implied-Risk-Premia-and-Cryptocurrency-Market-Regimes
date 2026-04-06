% The script plots BP (Bitcoin Premium) with different bandwidths (NB)

%% load data
clear,clc
addpath("m_Files_Color")                 % Add directory to MATLAB's search path for custom color files
addpath("m_Files_Color/colormap")        % Add subdirectory for colormap files
[~,~,~]=mkdir("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/"); % Create directory for output, if it doesn't exist

% Read Bitcoin Premium data from Excel files for different TTM (Time to Maturity) values
BP_overall_ttm27=readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/BP_SCA_ePDF_backward_onlyVR_OA_differentNB_ttm27.xlsx");
BP_c0_ttm27=readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/BP_SCA_ePDF_backward_onlyVR_HV_differentNB_ttm27.xlsx");
BP_c1_ttm27=readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/BP_SCA_ePDF_backward_onlyVR_LV_differentNB_ttm27.xlsx");

ret_simple=BP_c0_ttm27.Returns; % Extract simple returns for plotting

%% Plot BP overall with different NB

Colors = rainbow(5);

figure;
% Subplot for TTM 27 with multiple empirical PDF plots using different
% number of bins
plot(ret_simple,BP_overall_ttm27.BP_NB9,'Color',Colors(1,:),'LineWidth',2);hold on
plot(ret_simple,BP_overall_ttm27.BP_NB10,'Color',addcolor(260),'LineWidth',2);
plot(ret_simple,BP_overall_ttm27.BP_NB11,'Color',addcolor(49),'LineWidth',2);
plot(ret_simple,BP_overall_ttm27.BP_NB12,'Color',addcolor(257),'LineWidth',2);
plot(ret_simple,BP_overall_ttm27.BP_NB13,'Color',addcolor(185),'LineWidth',2);

hold off
xticks([-1,-0.8,-0.6,-0.4,-0.2,0,0.2,0.4,0.6,0.8,1])
xlabel('Return',FontSize=15)
ylim([0,1.2])
legend({'NB 9','NB 10','NB 11','NB 12','NB 13'},'FontSize',15,'Location','northwest')
grid on
% title("TTM 27, Red (NB=10) smoothest",'FontSize',20)
% Final adjustments and saving the figure
set(gcf,'Position',[0,0,450,300]);                                   % Set figure size  
set(gca,'FontSize',15)
% sgtitle(strcat('BP overall with different smoothing parameter'),'FontSize',30)  % Super title for the figure
saveas(gcf,"RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/BP_SCA_ePDF_backward_onlyVR_OA_different_NB_1by1_plot.png")






%% Plot BP overall with different NB: all black

shadow_x_negative = [-0.6, -0.2];
shadow_x_positive = [0.2, 0.6];

Colors = rainbow(5);

figure;
% Subplot for TTM 27 with multiple empirical PDF plots using different
% number of bins
plot(ret_simple,BP_overall_ttm27.BP_NB9,'.','Color','k','LineWidth',2);hold on
plot(ret_simple,BP_overall_ttm27.BP_NB10,'.-.','Color','k','LineWidth',2);
plot(ret_simple,BP_overall_ttm27.BP_NB11,'--','Color','k','LineWidth',2);
plot(ret_simple,BP_overall_ttm27.BP_NB12,'-','Color','k','LineWidth',2);
plot(ret_simple,BP_overall_ttm27.BP_NB13,'-.','Color','k','LineWidth',2);

x_shaded = [shadow_x_negative(1), shadow_x_negative(2), shadow_x_negative(2), shadow_x_negative(1)];% x-coordinates of the shaded area
y_shaded = [-1.5, -1.5, 8, 8];                                       % y-coordinates of the shaded area
fill(x_shaded, y_shaded, 'k', 'FaceAlpha', 0.05, 'EdgeColor','none'); % 'k' for black color, 10% transparent
x_shaded = [ shadow_x_positive(1), shadow_x_positive(2), shadow_x_positive(2), shadow_x_positive(1)]; % x-coordinates of the shaded area
y_shaded = [-1.5, -1.5, 8, 8];                                       % y-coordinates of the shaded area
fill(x_shaded, y_shaded, 'k', 'FaceAlpha', 0.05, 'EdgeColor','none'); % 'k' for black color, 10% transparent

hold off
xticks([-1,-0.8,-0.6,-0.4,-0.2,0,0.2,0.4,0.6,0.8,1])
xlabel('Return',FontSize=15)
ylim([0,1.2])
legend({'NB 9','NB 10','NB 11','NB 12','NB 13'},'FontSize',15,'Location','northwest')
grid off
% title("TTM 27, Red (NB=10) smoothest",'FontSize',20)
% Final adjustments and saving the figure
set(gcf,'Position',[0,0,450,300]);                                   % Set figure size  
set(gca,'FontSize',15)
% sgtitle(strcat('BP overall with different smoothing parameter'),'FontSize',30)  % Super title for the figure
saveas(gcf,"RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Bitcoin_Premium/BP_SCA_ePDF_backward_onlyVR_OA_different_NB_1by1_plot_black.png")
