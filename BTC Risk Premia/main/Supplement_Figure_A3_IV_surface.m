clc;clear; close all;

addpath("m_Files_Color/colormap/")

% Shared color axis limits for all plots
zmin = 0.5;
zmax = 1.2;

%% -------  Load data  -----------

% Load the common dates of the multivariate clustering
common_dates_path = "Clustering/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/common_dates_cluster.csv";
T = readtable(common_dates_path); % Read CSV file as table

% Extract dates for HV Cluster and LV Cluster
dates_Q = containers.Map('KeyType', 'double', 'ValueType', 'any');
dates_Q(0) = T.Date(T.Cluster == 0);
dates_Q(1) = T.Date(T.Cluster == 1);

% Merge and sort all dates
dates_Q_overall = [dates_Q(0); dates_Q(1)];
dates_Q_overall = datetime(dates_Q_overall);  % Convert to datetime format
dates_Q_overall = sort(dates_Q_overall);      % Sort by

%% Overall
IV_surface_path = "Clustering/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/IV_surface_average/IV_surface_average_overall.csv";
data = readmatrix(IV_surface_path);

X = data(:,1); % TTM
Y = -1:0.01:1; % Return
Z = data(:,2:end);

% Create a grid for x and y coordinates
[x, y] = meshgrid(Y, X);

% Plot the 3-D surface
figure;
surf(x, y, Z, 'FaceAlpha', 0.9);hold on % Creates the 3-D surface plot

% Apply lighting to the surface
%light; lighting phong; % Adjust the lighting to enhance surface visibility
%material shiny; % Adjust material properties to make the surface more reflective


% Apply a rainbow colormap
map = hsv;
colormap(map); % This produces a rainbow-like color scheme
clim([zmin zmax])  % Apply shared color scale
plot3(Y, ones(size(Y))*27, data(data(:,1)==27,2:end),'k','LineWidth',4)

% Add labels and title
xlabel('Return');
ylabel('\tau','Interpreter','tex');
zlabel('IV');
xlim([-0.15,0.15])
ylim([3,60])
zlim([0.5,1.2])
xticks([-0.15,0,0.15])
yticks([3,27,60])
zticks([0.6, 0.8, 1, 1.2])
% title('Overall');

ax = gca;
ax.FontSize = 15;
% ax.YAxis.FontWeight = 'bold'; % Make Y-axis tick labels bold
ax.YAxis.LineWidth = 1; % Increase the line width of the Y-axis
ax.XAxis.LineWidth = 1; % Increase the line width of the Y-axis

% Adjust the view angle for better visualization
view(45, 10); % Adjusts the viewing angle of the plot

set(gcf,'position',[0,0,450,300])
saveas(gcf,"Clustering/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/IV_surface_average//IV_surface_OA.png")
%% HV Cluster
IV_surface_path_HV = "Clustering/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/IV_surface_average/IV_surface_average_HV.csv";
data_HV = readmatrix(IV_surface_path_HV);

X = data_HV(:,1); % TTM
Y = -1:0.01:1;    % Moneyness / Return
Z = data_HV(:,2:end);

[x, y] = meshgrid(Y, X);

figure;
surf(x, y, Z, 'FaceAlpha', 0.9); hold on
colormap(hsv);
clim([zmin zmax])  % Apply shared color scale
plot3(Y, ones(size(Y))*27, data_HV(data_HV(:,1)==27,2:end), 'k', 'LineWidth', 4);

xlabel('Return');
ylabel('\tau','Interpreter','tex');
zlabel('IV');
xlim([-0.15,0.15]);
ylim([3,60]);
zlim([0.5,1.2]);
xticks([-0.15,0,0.15]);
yticks([3,27,60]);
zticks([0.6, 0.8, 1, 1.2]);

ax = gca;
ax.FontSize = 15;
ax.YAxis.LineWidth = 1;
ax.XAxis.LineWidth = 1;
view(45, 10);

set(gcf,'position',[0,0,450,300])
saveas(gcf,"Clustering/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/IV_surface_average/IV_surface_HV.png")

%% LV Cluster
IV_surface_path_LV = "Clustering/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/IV_surface_average/IV_surface_average_LV.csv";
data_LV = readmatrix(IV_surface_path_LV);

X = data_LV(:,1); % TTM
Y = -1:0.01:1;    % Moneyness / Return
Z = data_LV(:,2:end);

[x, y] = meshgrid(Y, X);

figure;
surf(x, y, Z, 'FaceAlpha', 0.9); hold on
colormap(hsv);
clim([zmin zmax])  % Apply shared color scale
plot3(Y, ones(size(Y))*27, data_LV(data_LV(:,1)==27,2:end), 'k', 'LineWidth', 4);

xlabel('Return');
ylabel('\tau','Interpreter','tex');
zlabel('IV');
xlim([-0.15,0.15]);
ylim([3,60]);
zlim([0.5,1.2]);
xticks([-0.15,0,0.15]);
yticks([3,27,60]);
zticks([0.6, 0.8, 1, 1.2]);

ax = gca;
ax.FontSize = 15;
ax.YAxis.LineWidth = 1;
ax.XAxis.LineWidth = 1;
view(45, 10);

set(gcf,'position',[0,0,450,300])
saveas(gcf,"Clustering/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/IV_surface_average/IV_surface_LV.png")