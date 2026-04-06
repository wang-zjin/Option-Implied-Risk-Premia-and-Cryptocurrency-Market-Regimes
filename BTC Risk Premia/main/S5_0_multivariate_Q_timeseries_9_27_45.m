clear, clc

ttm = 27;

%% Load common dates and clusters
common_dates = readtable('Clustering/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/common_dates_cluster.csv');
dates = string(common_dates.Date);
dates_list = datetime(dates, "InputFormat", "yyyy-MM-dd");

% Identify clusters (assume: Cluster==0 => Blue, Cluster==1 => Red)
index0 = common_dates.Cluster == 0;  % Blue
index1 = common_dates.Cluster == 1;  % Red

dates_Q{1,1} = dates_list(index0); % Blue cluster dates
dates_Q{1,2} = dates_list(index1); % Red cluster dates

%% Load Q matrix and assign date labels
raw_header = readcell(sprintf("Q_matrix/Tau-independent/unique/moneyness_step_0d01/Q_matrix_%dday.csv", ttm), 'FileType', 'text');
header_names = string(raw_header(1, :));  % First row contains column names

Q_table = readtable(sprintf("Q_matrix/Tau-independent/unique/moneyness_step_0d01/Q_matrix_%dday.csv", ttm), ...
    "VariableNamesRow",1, "VariableNamingRule","preserve");
Q_table_new = Q_table(2:end,:); % Remove duplicated header row if needed
Q_table_new.Properties.VariableNames = header_names; % Set correct headers

% Date headers: second column onward
date_headers = Q_table_new.Properties.VariableNames(2:end);
date_headers_dt = datetime(date_headers, "InputFormat", "yyyy-MM-dd");

% Assign cluster label for each date in Q_table:
% 1 = Blue, 2 = Red, 0 = Not assigned
cluster_labels = zeros(size(date_headers_dt)); 
for i = 1:length(date_headers_dt)
    if ismember(date_headers_dt(i), dates_Q{1,1})
        cluster_labels(i) = 1; % Blue
    elseif ismember(date_headers_dt(i), dates_Q{1,2})
        cluster_labels(i) = 2; % Red
    else
        cluster_labels(i) = 0; % No cluster assignment
    end
end

%% Compute Q density range for each date
% Q_density matrix: rows = moneyness, columns = dates
Q_density = Q_table_new{:, 2:end};
num_dates = size(Q_density, 2);
Q_range = NaN(1, num_dates);
for i = 1:num_dates
    density = Q_density(:, i);
    if ~isempty(density) && all(~isnan(density))
        Q_range(i) = max(density) - min(density);
    else
        Q_range(i) = NaN;
    end
end

%% Build full daily timeline and assign Q_range for each cluster
start_date = min(date_headers_dt);
end_date   = max(date_headers_dt);
full_dates = (start_date:end_date)';  % Daily timeline

% Initialize full arrays for each cluster with NaNs (so missing dates remain empty)
blue_full = NaN(size(full_dates));
red_full = NaN(size(full_dates));

% Map computed Q_range values to corresponding full_dates based on cluster labels
for i = 1:num_dates
    idx = find(full_dates == date_headers_dt(i));
    if cluster_labels(i) == 1
        blue_full(idx) = Q_range(i);
    elseif cluster_labels(i) == 2
        red_full(idx) = Q_range(i);
    end
end

%% Plot the time series as bars for each cluster
figure;
hold on;
bar(full_dates, blue_full, 'FaceColor', 'blue', 'EdgeColor', 'blue');
bar(full_dates, red_full, 'FaceColor', 'red', 'EdgeColor', 'red');
xlim(datetime([min(full_dates), '2022-12-31']))
xticks_position = [datetime([min(full_dates), '2018-01-01', '2019-01-01', '2020-01-01', '2021-01-01', ...
    '2022-01-01', '2022-12-31'])];
xticks(xticks_position)
xticklabels(datestr(xticks_position, 'mmm-yyyy'))
xlabel('Date');
ylabel('Q Density Range');
title(sprintf('Time Varying Q Density Side View of Multivariate Clustering \nHV (Blue), LV (Red)', ttm));
%datetick('x', 'yyyy-mm-dd', 'keeplimits'); % Format x-axis as dates
grid off;
hold off;
set(gcf,'Position',[0,0,900,300]);

% Optionally, save the plot
saveas(gcf, sprintf("Clustering/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Q_density_timeseries_%dday.png", ttm))