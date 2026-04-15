clc; clear; close all;

% ---------- Step 0: Load clustering dates ----------
common_dates_path = "Clustering/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/common_dates_cluster.csv";
T_cluster = readtable(common_dates_path);

dates_Q = containers.Map('KeyType', 'double', 'ValueType', 'any');
dates_Q(0) = datetime(T_cluster.Date(T_cluster.Cluster == 0)); % HV
dates_Q(1) = datetime(T_cluster.Date(T_cluster.Cluster == 1)); % LV
dates_Q(2) = sort([dates_Q(0); dates_Q(1)]);                   % overall

% ---------- Input Data ----------
ttm_to_plot = 27;
q_path = strcat("Q_from_pure_SVI/Tau-independent/unique/moneyness_step_0d01/tau_",num2str(ttm_to_plot));
file_list = dir(fullfile(q_path, '*.csv'));
file_list = sort({file_list.name});

% ---------- Output path ----------
plot_save_path = "Clustering/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Q_density_average_plot/";
if ~exist(plot_save_path, 'dir')
    mkdir(plot_save_path);
end

% ---------- Loop over all Q density files ----------
for cid = [0, 1, 2]  % 0=HV, 1=LV, 2=overall

    Q_density_curves = [];

    for k = 1:length(file_list)
        filename = fullfile(q_path, file_list(k));

        parts = filename.split('_');

        if length(parts) < 3, continue; end
        date_str = erase(parts{end}, ".csv");
        date_str = datetime(date_str);

        if ~ismember(date_str, dates_Q(cid))
            continue;
        end

        T = readtable(filename);

        % Check that required columns are present
        if ~ismember('m', T.Properties.VariableNames) || ~ismember('spdy', T.Properties.VariableNames)
            continue;
        end

        % Get moneyness and Q density values
        moneyness_vals = T.m;
        Q_density_vals = T.spdy;

        % Ensure the values are sorted by moneyness
        [moneyness_vals, sort_idx] = sort(moneyness_vals);
        Q_density_vals = Q_density_vals(sort_idx);

        % Save the density curve
        Q_density_curves = [Q_density_curves, Q_density_vals];

    end

    % ---------- Plot the density curve ----------
    figure;
    % Plot all individual Q density curves in gray and the average Q density curve in black (overall), blue (HV), red (LV)
    plot(nan, nan, 'Color', [0.8 0.8 0.8], 'LineWidth', 1);
    hold on;
    if cid == 0
        plot(nan, nan, 'Color', 'b', 'LineWidth', 2);
    elseif cid == 1
        plot(nan, nan, 'Color', 'r', 'LineWidth', 2);
    else
        plot(nan, nan, 'Color', 'k', 'LineWidth', 2);
    end
    plot(moneyness_vals, Q_density_curves, 'Color', [0.8 0.8 0.8], 'LineWidth', 1);
    if cid == 0
        plot(moneyness_vals, mean(Q_density_curves, 2), 'Color', 'b', 'LineWidth', 2);
    elseif cid == 1
        plot(moneyness_vals, mean(Q_density_curves, 2), 'Color', 'r', 'LineWidth', 2);
    else
        plot(moneyness_vals, mean(Q_density_curves, 2), 'Color', 'k', 'LineWidth', 2);
    end
    hold off;
    xlim([-1, 1]);
    ylim([0, 5]);
    % title(sprintf('Q Density Curve for Cluster %d', cid));
    % xlabel('Moneyness');
    % ylabel('Q Density');
    if cid == 0
        legend('$q_{HV}$', 'Average $q_{HV}$', 'FontSize', 15, 'Location', 'northwest', 'Interpreter', 'latex', 'box', 'off');
    elseif cid == 1
        legend('$q_{LV}$', 'Average $q_{LV}$', 'FontSize', 15, 'Location', 'northwest', 'Interpreter', 'latex', 'box', 'off');
    else
        legend('$q_{OA}$', 'Average $q_{OA}$', 'FontSize', 15, 'Location', 'northwest', 'Interpreter', 'latex', 'box', 'off');
    end
    set(gcf,'Position',[0,0,450,300])
    % file name
    if cid == 0
        file_name = "HV";
    elseif cid == 1
        file_name = "LV";
    else
        file_name = "Overall";
    end
    ax = gca;
    ax.FontSize = 15;
    ax.YAxis.LineWidth = 1; % Increase the line width of the Y-axis
    ax.XAxis.LineWidth = 1; % Increase the line width of the Y-axis
    
    saveas(gcf, sprintf('%s/Q_density_curve_%s.png', plot_save_path, file_name));

end