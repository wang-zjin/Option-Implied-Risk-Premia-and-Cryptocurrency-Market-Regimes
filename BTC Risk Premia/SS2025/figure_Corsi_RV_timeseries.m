%% Plot Corsi RV time series
% Corsi (2009) HAR model realized volatility forecast series
% Data: data_outputs/RV_forecast_BTC.mat (from data_prep/compute_RV_forecast_BTC.m)
% Style reference: fig_HAR_coefs.m

clear; close all; clc;

%% Load Corsi RV data
if isfile('data_outputs/RV_forecast_BTC.mat')
    load('data_outputs/RV_forecast_BTC', 'dates_RV_forecast', 'RV_forecast_OOS');
else
    error(['data_outputs/RV_forecast_BTC.mat not found. Run data_prep/compute_RV_forecast_BTC.m ', ...
           'or data_prep/compute_RV_forecast_BTC_record_coefs.m first.']);
end

% Convert dates to datenum for plotting
datesNum = datenum(num2str(dates_RV_forecast), 'yyyymmdd');

%% Plot Corsi RV (HAR forecast) time series
ff = figure('Position', [100, 100, 700, 400]);
set(ff, 'Units', 'Inches');
pos = get(ff, 'Position');
set(ff, 'PaperPositionMode', 'Auto', 'PaperUnits', 'Inches');

hold on;
plot(datesNum, RV_forecast_OOS, 'Color', 0.8*[.24 .69 .59], 'LineWidth', 1.2);
hold off;
grid on; box on;
set(gca, 'FontSize', 12);
xlim([min(datesNum), max(datesNum)]);
datetick('x', 'yyyy', 'keeplimits');
%xlabel('Date', 'FontSize', 14);
ylabel('Corsi RV (HAR forecast, \%)', 'FontSize', 14, 'Interpreter', 'tex');
title('Corsi RV time series (BTC, HAR realized volatility forecast)', 'FontSize', 14);

% Save
saveas(ff, 'figure_Corsi_RV_timeseries.png');
fprintf('Saved: figure_Corsi_RV_timeseries.png\n');
