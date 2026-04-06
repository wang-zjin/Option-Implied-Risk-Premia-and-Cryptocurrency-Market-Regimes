%% Plot side-view of Q densities

clear,clc
addpath("m_Files_Color")
ttm=27;

% Load common dates and clusters
common_dates = readtable('Clustering/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/common_dates_cluster.csv');
dates = string(common_dates.Date);
dates_list = datetime(dates, "InputFormat", "yyyy-MM-dd");

% Identify clusters
index0 = common_dates.Cluster == 0;
index1 = common_dates.Cluster == 1;

dates_Q{1,1} = dates_list(index0); % Blue
dates_Q{1,2} = dates_list(index1); % Red

% Load Q array
raw_header = readcell(strcat("Q_matrix/Tau-independent/unique/moneyness_step_0d01/Q_matrix_", num2str(ttm), "day.csv"), 'FileType', 'text');
header_names = string(raw_header(1, :));  % First row contains column names
Q_table = readtable(strcat("Q_matrix/Tau-independent/unique/moneyness_step_0d01/Q_matrix_",num2str(ttm),"day.csv"), ...
    "VariableNamesRow",1, "VariableNamingRule","preserve");
Q_table_new = Q_table(2:end,:); % Remove first row if it contains headers
Q_table_new.Properties.VariableNames = header_names; % Assign correct headers

% Extract common dates
date_headers = Q_table_new.Properties.VariableNames(2:end); % Dates as column names
date_headers_datetime = datetime(date_headers, "InputFormat", "yyyy-MM-dd", "Format", "yyyy-MM-dd"); % Convert to datetime

% Define clusters as a categorical array
cluster_labels = zeros(size(date_headers_datetime)); % Initialize cluster labels

% Assign cluster values: 1=Blue, 2=Red
for i = 1:length(date_headers_datetime)
    if ismember(date_headers_datetime(i), dates_Q{1,1})
        cluster_labels(i) = 1; % Blue
    elseif ismember(date_headers_datetime(i), dates_Q{1,2})
        cluster_labels(i) = 2; % Red
    else
        cluster_labels(i) = 0; % Default (if not in clusters)
    end
end

% Dates that belong to clusters
date_cluster_index = cluster_labels > 0; 

x_vals = Q_table_new{:, 1};  % First column is moneyness
y_vals = date_headers_datetime(date_cluster_index);

Q_density = Q_table_new{:, 2:end}; % Q densities
Q_density = Q_density(:, date_cluster_index);

% Convert y_vals to numeric for plotting
y_numeric = datenum(y_vals);

% Define Y-axis limits
y_min = min(y_numeric);
y_max = max(y_numeric);

% Create color matrix (same shape as Q_density)
C = repmat(cluster_labels(date_cluster_index), length(x_vals), 1); 

% Create figure
figure;
hold on;

% Create surface plot with cluster-based colors
[X, Y] = meshgrid(x_vals, y_numeric);
surf(X, Y, Q_density', C', 'EdgeColor', 'none', 'FaceAlpha', 0.9);

% Define custom colormap (1=Blue, 2=Red)
cmap = [0 0 1;  % Blue (Cluster 0)
        1 0 0];  % Red (Cluster 1)

colormap(cmap); % Apply colormap
clim([1 2]); % Ensure colormap indexing matches clusters

% Formatting
datetick('y', 'yyyy-mm-dd', 'keepticks'); % Format y-axis as dates
ylim([min(y_numeric), max(y_numeric)]); % Adjust Y-axis limits
zlim([0 max(Q_density(:))]); % Ensures Q Density starts from 0


% Define custom tick positions (start, end, and intermediate values)
num_ticks = 6; % Adjust the number of intermediate ticks as needed
ytick_positions = linspace(min(y_numeric), max(y_numeric), num_ticks);
yticks(ytick_positions);
yticklabels(datestr(ytick_positions, 'mmm-yyyy')); % Format in Month-Year


xlabel('Moneyness');
ylabel('Time');
zlabel('Q Density');
title(sprintf('Q Density Surface Side View of Multivariate Clustering with Cluster-Based Coloring\nHV (Blue), LV (Red)'));
view(90,0)
grid on;
hold off;

set(gcf,'Position',[0,0,900,300])

saveas(gcf, "Clustering/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/sideview.png")