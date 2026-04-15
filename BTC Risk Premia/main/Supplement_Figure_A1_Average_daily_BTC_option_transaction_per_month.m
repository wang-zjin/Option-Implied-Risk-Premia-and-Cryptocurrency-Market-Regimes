%% Summary Statistics for BTC Options
clear, clc

% Load the processed options data, daily BTC prices and DVOL
option = readtable("data/processed/20172022_processed_1_3_4.csv");
daily_price = readtable("data/BTC_USD_Quandl_2011_2023.csv");
% BTC_Dvol = readtable("data/DVOL.csv");

% Ensure the Summary_stats directory exists for output
[~,~,~] = mkdir("Summary_stats/1_3_5/daily_observations/");

%% delete option if IV==0
option(option.IV<=0,:)=[];
option(option.tau<=0,:)=[];
%% delete options with price < 10
sum(option.option_price<=10)
option = option(option.option_price>10,:);
%% delete observations with extremely low BTC price (less than $2000)
sum(option.BTC_price<1500)
unique(option.date(option.BTC_price<1500))
option(option.BTC_price<1500,:)=[];
%% Exclude 2022-12
option(option.date>=datetime("20221201","Inputform","uuuuMMdd"),:) = [];
%% number of transaction, quantity and volume overtime
[unique_date, ~, idx_date] = unique(string(option.date));
volume_daily = accumarray(idx_date, option.option_price.*option.quantity, [], @sum);
quantity_daily = accumarray(idx_date, option.quantity, [], @sum);
transaction_daily = accumarray(idx_date, ones(size(option.option_price)), [], @sum);

% daily volume
figure;
plot(datetime(unique_date),volume_daily)
title('BTC options volume')
ylabel('Daily trading volume (quantity \times option price)')
xlim([datetime("2017-07-01"),datetime("2022-12-01")])
xticks([datetime("2017-07-01"),datetime("2018-08-01"),datetime("2019-09-01"),datetime("2020-10-01"), ...
    datetime("2021-11-01"),datetime("2022-12-01")]);
saveas(gcf,"Summary_stats/1_3_5/daily_observations/Daily_volume.png")
% daily quantity
plot(datetime(unique_date),quantity_daily)
title('BTC options quantity')
ylabel('Daily trading quantity')
xlim([datetime("2017-07-01"),datetime("2022-12-01")])
xticks([datetime("2017-07-01"),datetime("2018-08-01"),datetime("2019-09-01"),datetime("2020-10-01"), ...
    datetime("2021-11-01"),datetime("2022-12-01")]);
saveas(gcf,"Summary_stats/1_3_5/daily_observations/Daily_quantity.png")
% daily transaction
plot(datetime(unique_date),transaction_daily)
title('BTC options transaction')
ylabel('Daily number of transaction')
xlim([datetime("2017-07-01"),datetime("2022-12-01")])
xticks([datetime("2017-07-01"),datetime("2018-08-01"),datetime("2019-09-01"),datetime("2020-10-01"), ...
    datetime("2021-11-01"),datetime("2022-12-01")]);
saveas(gcf,"Summary_stats/1_3_5/daily_observations/Daily_transaction.png")

% unique month & days in each month
[unique_month, ~, idx_month] = unique(string(datestr(option.date,'yyyymm')));
daysInMonth = eomday(year(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd')), month(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd')));

% daily average volume
volume_average_daily = accumarray(idx_month, option.option_price.*option.quantity, [], @sum);
volume_average_daily = volume_average_daily ./ daysInMonth;
bar(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd'), volume_average_daily)
ylabel('Daily average option volume (quantity \times option price)')
title('BTC options volume')
xlim([datetime("2017-07-01"),datetime("2022-12-01")])
xticks([datetime("2017-07-01"),datetime("2018-08-01"),datetime("2019-09-01"),datetime("2020-10-01"), ...
    datetime("2021-11-01"),datetime("2022-12-01")]);
dateaxis('x',12)
saveas(gcf,"Summary_stats/1_3_5/daily_observations/Daily_average_volume.png")

% daily average quantity
quantity_average_daily = accumarray(idx_month, option.quantity, [], @sum);
quantity_average_daily = quantity_average_daily ./ daysInMonth;
bar(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd'), quantity_average_daily)
ylabel('Daily average option quantity')
title('BTC options quantity')
xlim([datetime("2017-07-01"),datetime("2022-12-01")])
xticks([datetime("2017-07-01"),datetime("2018-08-01"),datetime("2019-09-01"),datetime("2020-10-01"), ...
    datetime("2021-11-01"),datetime("2022-12-01")]);
dateaxis('x',12)
saveas(gcf,"Summary_stats/1_3_5/daily_observations/Daily_average_quantity.png")

% daily average transaction
transaction_average_daily = accumarray(idx_month, ones(size(option.option_price)), [], @sum);
transaction_average_daily = transaction_average_daily ./ daysInMonth;
bar(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd'), transaction_average_daily)
ylabel('Transaction')
% title('Average daily BTC option transactions per month')
xlim([datetime("2017-07-01"),datetime("2022-12-01")])
xticks([datetime("2017-07-01"),datetime("2018-08-01"),datetime("2019-09-01"),datetime("2020-10-01"), ...
    datetime("2021-11-01"),datetime("2022-12-01")]);
dateaxis('x',12)
set(gcf,'Position',[0,0,1500,600])
set(gca,'FontSize',20)
saveas(gcf,"Summary_stats/1_3_5/daily_observations/Daily_average_transaction.png")

mean(transaction_average_daily)
mean(transaction_average_daily(1:30))
mean(transaction_average_daily(31:end))

%% number of transaction, quantity and volume overtime  --  CALL OPTION
option_call = option(strcmp(option.putcall,'C'),:);

[unique_date_call, ~, idx_date_call] = unique(string(option_call.date));
volume_daily = accumarray(idx_date_call, option_call.option_price.*option_call.quantity, [], @sum);
quantity_daily = accumarray(idx_date_call, option_call.quantity, [], @sum);
transaction_daily = accumarray(idx_date_call, ones(size(option_call.option_price)), [], @sum);

% daily volume
figure;
plot(datetime(unique_date_call),volume_daily)
dateaxis('x',12)
title('BTC call options volume')
ylabel('Daily trading volume (quantity \times option price)')
xlim([datetime("2017-07-01"),datetime("2022-12-01")])
saveas(gcf,"Summary_stats/Daily_volume_call.png")
% daily quantity
plot(datetime(unique_date_call),quantity_daily)
dateaxis('x',12)
title('BTC call options quantity')
ylabel('Daily trading quantity')
xlim([datetime("2017-07-01"),datetime("2022-12-01")])
saveas(gcf,"Summary_stats/Daily_quantity_call.png")
% daily transaction
plot(datetime(unique_date_call),transaction_daily)
dateaxis('x',12)
title('BTC call options transaction')
ylabel('Daily number of transaction')
xlim([datetime("2017-07-01"),datetime("2022-12-01")])
saveas(gcf,"Summary_stats/Daily_transaction_call.png")

% unique month & days in each month
[unique_month, ~, idx_month] = unique(string(datestr(option_call.date,'yyyymm')));
daysInMonth = eomday(year(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd')), month(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd')));
daysInMonth(end)=17;

% daily average volume
volume_average_daily = accumarray(idx_month, option_call.option_price.*option_call.quantity, [], @sum);
volume_average_daily = volume_average_daily ./ daysInMonth;
bar(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd'), volume_average_daily)
ylabel('Daily average option volume (quantity \times option price)')
title('BTC call options volume')
xlim([datetime("2017-07-01"),datetime("2022-12-01")])
dateaxis('x',12)
saveas(gcf,"Summary_stats/Daily_average_volume_call.png")

% daily average quantity
quantity_average_daily = accumarray(idx_month, option_call.quantity, [], @sum);
quantity_average_daily = quantity_average_daily ./ daysInMonth;
bar(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd'), quantity_average_daily)
ylabel('Daily average option quantity')
title('BTC call options quantity')
xlim([datetime("2017-07-01"),datetime("2022-12-01")])
dateaxis('x',12)
saveas(gcf,"Summary_stats/Daily_average_quantity_call.png")

% daily average transaction
transaction_average_daily = accumarray(idx_month, ones(size(option_call.option_price)), [], @sum);
transaction_average_daily = transaction_average_daily ./ daysInMonth;
bar(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd'), transaction_average_daily)
ylabel('Daily average option transaction')
title('BTC call options transaction')
xlim([datetime("2017-07-01"),datetime("2022-12-01")])
dateaxis('x',12)
saveas(gcf,"Summary_stats/Daily_average_transaction_call.png")

%% numberof transaction, quantity and volume overtime  --  PUT OPTION
option_put = option(strcmp(option.putcall,'P'),:);

[unique_date_put, ~, idx_date_put] = unique(string(option_put.date));
volume_daily = accumarray(idx_date_put, option_put.option_price.*option_put.quantity, [], @sum);
quantity_daily = accumarray(idx_date_put, option_put.quantity, [], @sum);
transaction_daily = accumarray(idx_date_put, ones(size(option_put.option_price)), [], @sum);

% daily volumes
plot(datetime(unique_date_put),volume_daily)
dateaxis('x',12)
title('BTC put options volume')
ylabel('Daily trading volume (quantity \times option price)')
xticks(datetime(unique_date_put(round(linspace(1,1996,10)))));
xticklabels(datestr(unique_date_put(round(linspace(1,1996,10))),'mmmyy'))
saveas(gcf,"Summary_stats/Daily_volume_put.png")
% daily quantity
plot(datetime(unique_date_put),quantity_daily)
dateaxis('x',12)
title('BTC put options quantity')
ylabel('Daily trading quantity')
xticks(datetime(unique_date_put(round(linspace(1,1996,10)))));
xticklabels(datestr(unique_date_put(round(linspace(1,1996,10))),'mmmyy'))
saveas(gcf,"Summary_stats/Daily_quantity_put.png")
% daily transaction
plot(datetime(unique_date_put),transaction_daily)
dateaxis('x',12)
title('BTC put options transaction')
ylabel('Daily number of transaction')
xticks(datetime(unique_date_put(round(linspace(1,1996,10)))));
xticklabels(datestr(unique_date_put(round(linspace(1,1996,10))),'mmmyy'))
saveas(gcf,"Summary_stats/Daily_transaction_put.png")

% unique month & days in each month
[unique_month, ~, idx_month] = unique(string(datestr(option_put.date,'yyyymm')));
daysInMonth = eomday(year(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd')), month(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd')));
daysInMonth(end)=17;

% daily average volume
volume_average_daily = accumarray(idx_month, option_put.option_price.*option_put.quantity, [], @sum);
volume_average_daily = volume_average_daily ./ daysInMonth;
bar(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd'), volume_average_daily)
ylabel('Daily average option volume (quantity \times option price)')
title('BTC put options volume')
xticks(datetime(strcat(unique_month(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'));
xticklabels(datestr(datetime(strcat(unique_month(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'),'mmmyy'))
dateaxis('x',12)
saveas(gcf,"Summary_stats/Daily_average_volume_put.png")

% daily average quantity
quantity_average_daily = accumarray(idx_month, option_put.quantity, [], @sum);
quantity_average_daily = quantity_average_daily ./ daysInMonth;
bar(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd'), quantity_average_daily)
ylabel('Daily average option quantity')
title('BTC put options quantity')
xticks(datetime(strcat(unique_month(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'));
xticklabels(datestr(datetime(strcat(unique_month(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'),'mmmyy'))
dateaxis('x',12)
saveas(gcf,"Summary_stats/Daily_average_quantity_put.png")

% daily average transaction
transaction_average_daily = accumarray(idx_month, ones(size(option_put.option_price)), [], @sum);
transaction_average_daily = transaction_average_daily ./ daysInMonth;
bar(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd'), transaction_average_daily)
ylabel('Daily average option transaction')
title('BTC put options transaction')
xticks(datetime(strcat(unique_month(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'));
xticklabels(datestr(datetime(strcat(unique_month(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'),'mmmyy'))
dateaxis('x',12)
saveas(gcf,"Summary_stats/Daily_average_transaction_put.png")
