%% summary statistics 1.3.5
% 1.option data "20172022_processed_1_3_4.csv"
% 2.Time span from 20170701 to 20221217
% 3.delete option with tau less than 1
% 4.delete option with prices less than $10
% 5.delete option with IV less or equal to 0
% 8.delete observations with extremely low BTC price (less than $2000)
%% load data
clear,clc
option1 = readtable("data/17Jul_18Dec/sampleall.csv");
option2 = readtable("data/deribit20192020/option1920clean.csv");
option3 = readtable("data/all_btc33.csv");
option = [option1;option2;option3];
clear option1 option2 option3
[~,~,~]=mkdir("Summary_stats/1_3_5");

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
%% volume
volume = option.BTC_price .* option.quantity;
moneyness = option.K ./ option.BTC_price;
option = addvars(option, volume, moneyness, 'NewVariableNames',{'volume', 'moneyness'});
volume = option.option_price .* option.quantity;
option = addvars(option, volume, 'NewVariableNames',{'volume_optionprice'});
tau_type = string(option.K);
% for i=1:numel(tau_type)
%     if option.tau(i)<=9
%         tau_type(i)='<=9';
%     elseif option.tau(i)<27
%         tau_type(i)='10_26';
%     elseif option.tau(i)<=33
%         tau_type(i)='27_33';
%     else
%         tau_type(i)='>33';
%     end
% end
tau_type(option.tau<=9)='<=9';
tau_type(option.tau>9 & option.tau<27)='10_26';
tau_type(option.tau>=27 & option.tau<=33)='27_33';
tau_type(option.tau>33)='>33';
option = addvars(option, tau_type, 'NewVariableNames',{'tau_range'});

moneyness_type = tau_type;
% for i=1:numel(moneyness_type)
%     if option.moneyness(i) < 0.9
%         moneyness_type(i)='<0d9';
%     elseif option.moneyness(i) <= 0.97
%         moneyness_type(i)='0d9_0d97';
%     elseif option.moneyness(i) < 1.03
%         moneyness_type(i)='0d97_1d03';
%     elseif option.moneyness(i) < 1.1
%         moneyness_type(i)='1d03_1d1';
%     else
%         moneyness_type(i)='g>1d1';
%     end
% end
moneyness_type(option.moneyness < 0.9)='<0d9';
moneyness_type(option.moneyness >= 0.9 & option.moneyness <= 0.97)='0d9_0d97';
moneyness_type(option.moneyness > 0.97 & option.moneyness < 1.03)='0d97_1d03';
moneyness_type(option.moneyness >= 1.03 & option.moneyness <= 1.1)='1d03_1d1';
moneyness_type(option.moneyness > 1.1)='g>1d1';
option = addvars(option, moneyness_type, 'NewVariableNames',{'moneyness_range'});
clear tau_type moneyness_type
%% Average IV of BTC call options
IV_table = nan(6,5);
IV_table(1,:) = [mean(option.IV(option.moneyness<0.9 & option.tau<=9 & strcmp(option.putcall,'C'),:)),...
    mean(option.IV(option.moneyness<0.9 & option.tau>9 & option.tau<=26 & strcmp(option.putcall,'C'),:)),...
    mean(option.IV(option.moneyness<0.9 & option.tau>=27 & option.tau<=33 & strcmp(option.putcall,'C'),:)),...
    mean(option.IV(option.moneyness<0.9 & option.tau>33 & strcmp(option.putcall,'C'),:)),...
    mean(option.IV(option.moneyness<0.9 & strcmp(option.putcall,'C'),:))];
IV_table(2,:) = [mean(option.IV(option.moneyness>=0.9 & option.moneyness<0.97 & option.tau<=9 & strcmp(option.putcall,'C'),:)),...
    mean(option.IV(option.moneyness>=0.9 & option.moneyness<0.97 & option.tau>9 & option.tau<=26 & strcmp(option.putcall,'C'),:)),...
    mean(option.IV(option.moneyness>=0.9 & option.moneyness<0.97 & option.tau>=27 & option.tau<=33 & strcmp(option.putcall,'C'),:)),...
    mean(option.IV(option.moneyness>=0.9 & option.moneyness<0.97 & option.tau>33 & strcmp(option.putcall,'C'),:)),...
    mean(option.IV(option.moneyness>=0.9 & strcmp(option.putcall,'C'),:))];
IV_table(3,:) = [mean(option.IV(option.moneyness>=0.97 & option.moneyness<1.03 & option.tau<=9 & strcmp(option.putcall,'C'),:)),...
    mean(option.IV(option.moneyness>=0.97 & option.moneyness<1.03 & option.tau>9 & option.tau<=26 & strcmp(option.putcall,'C'),:)),...
    mean(option.IV(option.moneyness>=0.97 & option.moneyness<1.03 & option.tau>=27 & option.tau<=33 & strcmp(option.putcall,'C'),:)),...
    mean(option.IV(option.moneyness>=0.97 & option.moneyness<1.03 & option.tau>33 & strcmp(option.putcall,'C'),:)),...
    mean(option.IV(option.moneyness>=0.97 & strcmp(option.putcall,'C'),:))];
IV_table(4,:) = [mean(option.IV(option.moneyness>=1.03 & option.moneyness<1.10 & option.tau<=9 & strcmp(option.putcall,'C'),:)),...
    mean(option.IV(option.moneyness>=1.03 & option.moneyness<1.10 & option.tau>9 & option.tau<=26 & strcmp(option.putcall,'C'),:)),...
    mean(option.IV(option.moneyness>=1.03 & option.moneyness<1.10 & option.tau>=27 & option.tau<=33 & strcmp(option.putcall,'C'),:)),...
    mean(option.IV(option.moneyness>=1.03 & option.moneyness<1.10 & option.tau>33 & strcmp(option.putcall,'C'),:)),...
    mean(option.IV(option.moneyness>=1.03 & strcmp(option.putcall,'C'),:))];
IV_table(5,:) = [mean(option.IV(option.moneyness>=1.10 & option.tau<=9 & strcmp(option.putcall,'C'),:)),...
    mean(option.IV(option.moneyness>=1.10 & option.tau>9 & option.tau<=26 & strcmp(option.putcall,'C'),:)),...
    mean(option.IV(option.moneyness>=1.10 & option.tau>=27 & option.tau<=33 & strcmp(option.putcall,'C'),:)),...
    mean(option.IV(option.moneyness>=1.10 & option.tau>33 & strcmp(option.putcall,'C'),:)),...
    mean(option.IV(option.moneyness>=1.10 & strcmp(option.putcall,'C'),:))];
IV_table(6,:) = [mean(option.IV(option.tau<=9 & strcmp(option.putcall,'C'),:)),...
    mean(option.IV(option.tau>9 & option.tau<=26 & strcmp(option.putcall,'C'),:)),...
    mean(option.IV(option.tau>=27 & option.tau<=33 & strcmp(option.putcall,'C'),:)),...
    mean(option.IV(option.tau>33 & strcmp(option.putcall,'C'),:)),...
    mean(option.IV(strcmp(option.putcall,'C'),:))];
IV_table = IV_table/100;
clear info;
info.rnames = strvcat('.','(0,0.9)','[0.9,0.97)','[0.97,1.03)','[1.03,1.10)','>1.10','Average');
info.cnames = strvcat('(0,9]','(9,26]','[27,33]','>33','Average');
info.fmt    = '%10.2f';
mprint(IV_table,info)
writetable(table(IV_table),"Summary_stats/1_3_5/Average_IV_call.csv")
%% Average IV of BTC put options
IV_table = nan(6,5);
IV_table(1,:) = [mean(option.IV(option.moneyness<0.9 & option.tau<=9 & strcmp(option.putcall,'P'),:)),...
    mean(option.IV(option.moneyness<0.9 & option.tau>9 & option.tau<=26 & strcmp(option.putcall,'P'),:)),...
    mean(option.IV(option.moneyness<0.9 & option.tau>=27 & option.tau<=33 & strcmp(option.putcall,'P'),:)),...
    mean(option.IV(option.moneyness<0.9 & option.tau>33 & strcmp(option.putcall,'P'),:)),...
    mean(option.IV(option.moneyness<0.9 & strcmp(option.putcall,'P'),:))];
IV_table(2,:) = [mean(option.IV(option.moneyness>=0.9 & option.moneyness<0.97 & option.tau<=9 & strcmp(option.putcall,'P'),:)),...
    mean(option.IV(option.moneyness>=0.9 & option.moneyness<0.97 & option.tau>9 & option.tau<=26 & strcmp(option.putcall,'P'),:)),...
    mean(option.IV(option.moneyness>=0.9 & option.moneyness<0.97 & option.tau>=27 & option.tau<=33 & strcmp(option.putcall,'P'),:)),...
    mean(option.IV(option.moneyness>=0.9 & option.moneyness<0.97 & option.tau>33 & strcmp(option.putcall,'P'),:)),...
    mean(option.IV(option.moneyness>=0.9 & strcmp(option.putcall,'P'),:))];
IV_table(3,:) = [mean(option.IV(option.moneyness>=0.97 & option.moneyness<1.03 & option.tau<=9 & strcmp(option.putcall,'P'),:)),...
    mean(option.IV(option.moneyness>=0.97 & option.moneyness<1.03 & option.tau>9 & option.tau<=26 & strcmp(option.putcall,'P'),:)),...
    mean(option.IV(option.moneyness>=0.97 & option.moneyness<1.03 & option.tau>=27 & option.tau<=33 & strcmp(option.putcall,'P'),:)),...
    mean(option.IV(option.moneyness>=0.97 & option.moneyness<1.03 & option.tau>33 & strcmp(option.putcall,'P'),:)),...
    mean(option.IV(option.moneyness>=0.97 & strcmp(option.putcall,'P'),:))];
IV_table(4,:) = [mean(option.IV(option.moneyness>=1.03 & option.moneyness<1.10 & option.tau<=9 & strcmp(option.putcall,'P'),:)),...
    mean(option.IV(option.moneyness>=1.03 & option.moneyness<1.10 & option.tau>9 & option.tau<=26 & strcmp(option.putcall,'P'),:)),...
    mean(option.IV(option.moneyness>=1.03 & option.moneyness<1.10 & option.tau>=27 & option.tau<=33 & strcmp(option.putcall,'P'),:)),...
    mean(option.IV(option.moneyness>=1.03 & option.moneyness<1.10 & option.tau>33 & strcmp(option.putcall,'P'),:)),...
    mean(option.IV(option.moneyness>=1.03 & strcmp(option.putcall,'P'),:))];
IV_table(5,:) = [mean(option.IV(option.moneyness>=1.10 & option.tau<=9 & strcmp(option.putcall,'P'),:)),...
    mean(option.IV(option.moneyness>=1.10 & option.tau>9 & option.tau<=26 & strcmp(option.putcall,'P'),:)),...
    mean(option.IV(option.moneyness>=1.10 & option.tau>=27 & option.tau<=33 & strcmp(option.putcall,'P'),:)),...
    mean(option.IV(option.moneyness>=1.10 & option.tau>33 & strcmp(option.putcall,'P'),:)),...
    mean(option.IV(option.moneyness>=1.10 & strcmp(option.putcall,'P'),:))];
IV_table(6,:) = [mean(option.IV(option.tau<=9 & strcmp(option.putcall,'P'),:)),...
    mean(option.IV(option.tau>9 & option.tau<=26 & strcmp(option.putcall,'P'),:)),...
    mean(option.IV(option.tau>=27 & option.tau<=33 & strcmp(option.putcall,'P'),:)),...
    mean(option.IV(option.tau>33 & strcmp(option.putcall,'P'),:)),...
    mean(option.IV(strcmp(option.putcall,'P'),:))];
IV_table = IV_table/100;
clear info;
info.rnames = strvcat('.','(0,0.9)','[0.9,0.97)','[0.97,1.03)','[1.03,1.10)','>1.10','Average');
info.cnames = strvcat('(0,9]','(9,26]','[27,33]','>33','Average');
info.fmt    = '%10.2f';
mprint(IV_table,info)
writetable(table(IV_table),"Summary_stats/1_3_5/Average_IV_put.csv")
%% summary statistics: number of transactions
[tbl,~,~,labels] = crosstab(option.moneyness_range,  option.tau_range);
tbl = tbl / sum(sum(tbl));
X_labels = labels(1:4,2)';
for i = 1:numel(X_labels)
    X_labels{i}=strcat('tau_',X_labels{i});
end
X_labels = X_labels(:,[4,3,1,2]);
tbl = tbl(:,[4,3,1,2]);

Y_labels = labels(:,1)';
for i = 1:numel(Y_labels)
    Y_labels{i}=strcat('m_',Y_labels{i});
end
Y_labels = Y_labels(:,[1,5,3,2,4]);
tbl = tbl([1,5,3,2,4],:);

tbl = [tbl;sum(tbl)];
Y_labels = [Y_labels,{'Total'}];
tbl = [tbl,sum(tbl,2)];
X_labels = [X_labels,{'Total'}];

Tbl = array2table(tbl,'VariableNames',X_labels,'RowNames',Y_labels);
writetable(Tbl,"Summary_stats/1_3_5/option_characteristics_transaction_overall.csv")

% call option
[tbl_call,~,~,labels_call] = crosstab(option.moneyness_range(strcmp(option.putcall,'C')),  option.tau_range(strcmp(option.putcall,'C')));
tbl_call = tbl_call / sum(sum(tbl_call));
tbl_call = tbl_call(:,[4,3,1,2]);
tbl_call = tbl_call([5,3,2,1,4],:);
tbl_call = [tbl_call;sum(tbl_call)];
tbl_call = [tbl_call,sum(tbl_call,2)];

Tbl_call = array2table(tbl_call,'VariableNames',X_labels,'RowNames',Y_labels);
writetable(Tbl_call,"Summary_stats/1_3_5/option_characteristics_transaction_call.csv")

% put option
[tbl_put,~,~,labels_put] = crosstab(option.moneyness_range(strcmp(option.putcall,'P')),  option.tau_range(strcmp(option.putcall,'P')));
tbl_put = tbl_put / sum(sum(tbl_put));
tbl_put = tbl_put(:,[4,3,1,2]);
tbl_put = tbl_put([1,4,3,5,2],:);
tbl_put = [tbl_put;sum(tbl_put)];
tbl_put = [tbl_put,sum(tbl_put,2)];

Tbl_put = array2table(tbl_put,'VariableNames',X_labels,'RowNames',Y_labels);
writetable(Tbl_put,"Summary_stats/1_3_5/option_characteristics_transaction_put.csv")

%% summary statistics: quantity

[unique_tau_range, ~, idx_tau_range] = unique(string(option.tau_range));
% volume_tau_range = accumarray(idx_tau_range, option.quantity, [], @sum);

[unique_m_range_1, ~, idx_m_range_1] = unique(string(option.moneyness_range(idx_tau_range==1)));
unique_m_range_1
quantity_m_range_1 = accumarray(idx_m_range_1, option.quantity(idx_tau_range==1), [], @sum);
[unique_m_range_2, ~, idx_m_range_2] = unique(string(option.moneyness_range(idx_tau_range==2)));
quantity_m_range_2 = accumarray(idx_m_range_2, option.quantity(idx_tau_range==2), [], @sum);
[unique_m_range_3, ~, idx_m_range_3] = unique(string(option.moneyness_range(idx_tau_range==3)));
quantity_m_range_3 = accumarray(idx_m_range_3, option.quantity(idx_tau_range==3), [], @sum);
[unique_m_range_4, ~, idx_m_range_4] = unique(string(option.moneyness_range(idx_tau_range==4)));
quantity_m_range_4 = accumarray(idx_m_range_4, option.quantity(idx_tau_range==4), [], @sum);

tbl = [quantity_m_range_1, quantity_m_range_2, quantity_m_range_3, quantity_m_range_4];
tbl = tbl/sum(sum(tbl));
tbl = tbl(:,[3,1,2,4]);
tbl = tbl([4,2,1,3,5],:);
tbl = [tbl;sum(tbl)];
tbl = [tbl,sum(tbl,2)];
Tbl = array2table(tbl,'VariableNames',X_labels,'RowNames',Y_labels);
writetable(Tbl,"Summary_stats/1_3_5/option_characteristics_quantity_overall.csv")

% call
option_call = option(strcmp(option.putcall,'C'),:);
[unique_tau_range_call, ~, idx_tau_range_call] = unique(string(option_call.tau_range));
unique_tau_range_call

[unique_m_range_call_1, ~, idx_m_range_call_1] = unique(string(option_call.moneyness_range(idx_tau_range_call==1)));
unique_m_range_call_1
quantity_m_range_call_1 = accumarray(idx_m_range_call_1, option_call.quantity(idx_tau_range_call==1), [], @sum);
[unique_m_range_call_2, ~, idx_m_range_call_2] = unique(string(option_call.moneyness_range(idx_tau_range_call==2)));
quantity_m_range_call_2 = accumarray(idx_m_range_call_2, option_call.quantity(idx_tau_range_call==2), [], @sum);
[unique_m_range_call_3, ~, idx_m_range_call_3] = unique(string(option_call.moneyness_range(idx_tau_range_call==3)));
quantity_m_range_call_3 = accumarray(idx_m_range_call_3, option_call.quantity(idx_tau_range_call==3), [], @sum);
[unique_m_range_call_4, ~, idx_m_range_call_4] = unique(string(option_call.moneyness_range(idx_tau_range_call==4)));
quantity_m_range_call_4 = accumarray(idx_m_range_call_4, option_call.quantity(idx_tau_range_call==4), [], @sum);

tbl_call = [quantity_m_range_call_1, quantity_m_range_call_2, quantity_m_range_call_3, quantity_m_range_call_4];
tbl_call = tbl_call/sum(sum(tbl_call));
tbl_call = tbl_call(:,[3,1,2,4]);
tbl_call = tbl_call([4,2,1,3,5],:);
tbl_call = [tbl_call;sum(tbl_call)];
tbl_call = [tbl_call,sum(tbl_call,2)];
Tbl_call = array2table(tbl_call,'VariableNames',X_labels,'RowNames',Y_labels);
writetable(Tbl_call,"Summary_stats/1_3_5/option_characteristics_quantity_call.csv")


% put
option_put = option(strcmp(option.putcall,'P'),:);
[unique_tau_range_put, ~, idx_tau_range_put] = unique(string(option_put.tau_range));
unique_tau_range_put
[unique_m_range_put_1, ~, idx_m_range_put_1] = unique(string(option_put.moneyness_range(idx_tau_range_put==1)));
quantity_m_range_put_1 = accumarray(idx_m_range_put_1, option_put.quantity(idx_tau_range_put==1), [], @sum);
[unique_m_range_put_2, ~, idx_m_range_put_2] = unique(string(option_put.moneyness_range(idx_tau_range_put==2)));
quantity_m_range_put_2 = accumarray(idx_m_range_put_2, option_put.quantity(idx_tau_range_put==2), [], @sum);
[unique_m_range_put_3, ~, idx_m_range_put_3] = unique(string(option_put.moneyness_range(idx_tau_range_put==3)));
quantity_m_range_put_3 = accumarray(idx_m_range_put_3, option_put.quantity(idx_tau_range_put==3), [], @sum);
[unique_m_range_put_4, ~, idx_m_range_put_4] = unique(string(option_put.moneyness_range(idx_tau_range_put==4)));
quantity_m_range_put_4 = accumarray(idx_m_range_put_4, option_put.quantity(idx_tau_range_put==4), [], @sum);

tbl_put = [quantity_m_range_put_1, quantity_m_range_put_2, quantity_m_range_put_3, quantity_m_range_put_4];
tbl_put = tbl_put/sum(sum(tbl_put));
tbl_put = tbl_put(:,[3,1,2,4]);
tbl_put = tbl_put([4,2,1,3,5],:);
tbl_put = [tbl_put;sum(tbl_put)];
tbl_put = [tbl_put,sum(tbl_put,2)];
Tbl_put = array2table(tbl_put,'VariableNames',X_labels,'RowNames',Y_labels);
writetable(Tbl_put,"Summary_stats/1_3_5/option_characteristics_quantity_put.csv")

%% summary statistics: volume
[unique_tau_range, ~, idx_tau_range] = unique(string(option.tau_range));
unique_tau_range

[unique_m_range_1, ~, idx_m_range_1] = unique(string(option.moneyness_range(idx_tau_range==1)));
unique_m_range_1
volume_m_range_1 = accumarray(idx_m_range_1, option.quantity(idx_tau_range==1).*option.option_price(idx_tau_range==1), [], @sum);
[unique_m_range_2, ~, idx_m_range_2] = unique(string(option.moneyness_range(idx_tau_range==2)));
volume_m_range_2 = accumarray(idx_m_range_2, option.quantity(idx_tau_range==2).*option.option_price(idx_tau_range==2), [], @sum);
[unique_m_range_3, ~, idx_m_range_3] = unique(string(option.moneyness_range(idx_tau_range==3)));
volume_m_range_3 = accumarray(idx_m_range_3, option.quantity(idx_tau_range==3).*option.option_price(idx_tau_range==3), [], @sum);
[unique_m_range_4, ~, idx_m_range_4] = unique(string(option.moneyness_range(idx_tau_range==4)));
volume_m_range_4 = accumarray(idx_m_range_4, option.quantity(idx_tau_range==4).*option.option_price(idx_tau_range==4), [], @sum);

tbl = [volume_m_range_1, volume_m_range_2, volume_m_range_3, volume_m_range_4];
tbl = tbl/sum(sum(tbl));
tbl = tbl(:,[3,1,2,4]);
tbl = tbl([4,2,1,3,5],:);
tbl = [tbl;sum(tbl)];
tbl = [tbl,sum(tbl,2)];
Tbl = array2table(tbl,'VariableNames',X_labels,'RowNames',Y_labels);
writetable(Tbl,"Summary_stats/1_3_5/option_characteristics_volume_overall.csv")

% call
option_call = option(strcmp(option.putcall,'C'),:);
[unique_tau_range_call, ~, idx_tau_range_call] = unique(string(option_call.tau_range));
unique_tau_range_call

[unique_m_range_call_1, ~, idx_m_range_call_1] = unique(string(option_call.moneyness_range(idx_tau_range_call==1)));
unique_m_range_call_1
volume_m_range_call_1 = accumarray(idx_m_range_call_1, option_call.quantity(idx_tau_range_call==1).*option_call.option_price(idx_tau_range_call==1), [], @sum);
[unique_m_range_call_2, ~, idx_m_range_call_2] = unique(string(option_call.moneyness_range(idx_tau_range_call==2)));
volume_m_range_call_2 = accumarray(idx_m_range_call_2, option_call.quantity(idx_tau_range_call==2).*option_call.option_price(idx_tau_range_call==2), [], @sum);
[unique_m_range_call_3, ~, idx_m_range_call_3] = unique(string(option_call.moneyness_range(idx_tau_range_call==3)));
volume_m_range_call_3 = accumarray(idx_m_range_call_3, option_call.quantity(idx_tau_range_call==3).*option_call.option_price(idx_tau_range_call==3), [], @sum);
[unique_m_range_call_4, ~, idx_m_range_call_4] = unique(string(option_call.moneyness_range(idx_tau_range_call==4)));
volume_m_range_call_4 = accumarray(idx_m_range_call_4, option_call.quantity(idx_tau_range_call==4).*option_call.option_price(idx_tau_range_call==4), [], @sum);

tbl_call = [volume_m_range_call_1, volume_m_range_call_2, volume_m_range_call_3, volume_m_range_call_4];
tbl_call = tbl_call/sum(sum(tbl_call));
tbl_call = tbl_call(:,[3,1,2,4]);
tbl_call = tbl_call([4,2,1,3,5],:);
tbl_call = [tbl_call;sum(tbl_call)];
tbl_call = [tbl_call,sum(tbl_call,2)];
Tbl_call = array2table(tbl_call,'VariableNames',X_labels,'RowNames',Y_labels);
writetable(Tbl_call,"Summary_stats/1_3_5/option_characteristics_volume_call.csv")

% put
option_put = option(strcmp(option.putcall,'P'),:);
[unique_tau_range_put, ~, idx_tau_range_put] = unique(string(option_put.tau_range));
unique_tau_range_put

[unique_m_range_put_1, ~, idx_m_range_put_1] = unique(string(option_put.moneyness_range(idx_tau_range_put==1)));
unique_m_range_put_1
volume_m_range_put_1 = accumarray(idx_m_range_put_1, option_put.quantity(idx_tau_range_put==1).*option_put.option_price(idx_tau_range_put==1), [], @sum);
[unique_m_range_put_2, ~, idx_m_range_put_2] = unique(string(option_put.moneyness_range(idx_tau_range_put==2)));
volume_m_range_put_2 = accumarray(idx_m_range_put_2, option_put.quantity(idx_tau_range_put==2).*option_put.option_price(idx_tau_range_put==2), [], @sum);
[unique_m_range_put_3, ~, idx_m_range_put_3] = unique(string(option_put.moneyness_range(idx_tau_range_put==3)));
volume_m_range_put_3 = accumarray(idx_m_range_put_3, option_put.quantity(idx_tau_range_put==3).*option_put.option_price(idx_tau_range_put==3), [], @sum);
[unique_m_range_put_4, ~, idx_m_range_put_4] = unique(string(option_put.moneyness_range(idx_tau_range_put==4)));
volume_m_range_put_4 = accumarray(idx_m_range_put_4, option_put.quantity(idx_tau_range_put==4).*option_put.option_price(idx_tau_range_put==4), [], @sum);

tbl_put = [volume_m_range_put_1, volume_m_range_put_2, volume_m_range_put_3, volume_m_range_put_4];
tbl_put = tbl_put/sum(sum(tbl_put));
tbl_put = tbl_put(:,[3,1,2,4]);
tbl_put = tbl_put([4,2,1,3,5],:);
tbl_put = [tbl_put;sum(tbl_put)];
tbl_put = [tbl_put,sum(tbl_put,2)];
Tbl_put = array2table(tbl_put,'VariableNames',X_labels,'RowNames',Y_labels);
writetable(Tbl_put,"Summary_stats/1_3_5/option_characteristics_volume_put.csv")


% % % % % %% number of transaction, quantity and volume overtime
% % % % % [unique_date, ~, idx_date] = unique(string(option.date));
% % % % % volume_daily = accumarray(idx_date, option.option_price.*option.quantity, [], @sum);
% % % % % quantity_daily = accumarray(idx_date, option.quantity, [], @sum);
% % % % % transaction_daily = accumarray(idx_date, ones(size(option.option_price)), [], @sum);
% % % % % 
% % % % % % daily value
% % % % % figure;
% % % % % plot(datetime(unique_date),volume_daily)
% % % % % dateaxis('x',12)
% % % % % title('BTC options value')
% % % % % ylabel('Daily trading value (quantity \times option price)')
% % % % % xticks(datetime(unique_date(round(linspace(1,1996,10)))));
% % % % % xticklabels(datestr(unique_date(round(linspace(1,1996,10))),'mmmyy'))
% % % % % saveas(gcf,"Summary_stats/1_3_5/Daily_volume.png")
% % % % % % daily quantity
% % % % % plot(datetime(unique_date),quantity_daily)
% % % % % dateaxis('x',12)
% % % % % title('BTC options quantity')
% % % % % ylabel('Daily trading quantity')
% % % % % xticks(datetime(unique_date(round(linspace(1,1996,10)))));
% % % % % xticklabels(datestr(unique_date(round(linspace(1,1996,10))),'mmmyy'))
% % % % % saveas(gcf,"Summary_stats/1_3_5/Daily_quantity.png")
% % % % % % daily transaction
% % % % % plot(datetime(unique_date),transaction_daily)
% % % % % dateaxis('x',12)
% % % % % title('BTC options transaction')
% % % % % ylabel('Daily number of transaction')
% % % % % xticks(datetime(unique_date(round(linspace(1,1996,10)))));
% % % % % xticklabels(datestr(unique_date(round(linspace(1,1996,10))),'mmmyy'))
% % % % % saveas(gcf,"Summary_stats/1_3_5/Daily_transaction.png")
% % % % % 
% % % % % % unique month & days in each month
% % % % % [unique_month, ~, idx_month] = unique(string(datestr(option.date,'yyyymm')));
% % % % % daysInMonth = eomday(year(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd')), month(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd')));
% % % % % daysInMonth(end)=17;
% % % % % 
% % % % % % daily average volume
% % % % % volume_average_daily = accumarray(idx_month, option.option_price.*option.quantity, [], @sum);
% % % % % volume_average_daily = volume_average_daily ./ daysInMonth;
% % % % % bar(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd'), volume_average_daily)
% % % % % ylabel('Daily average option value (quantity \times option price)')
% % % % % title('BTC options value')
% % % % % xticks(datetime(strcat(unique_month(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % xticklabels(datestr(datetime(strcat(unique_month(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'),'mmmyy'))
% % % % % dateaxis('x',12)
% % % % % saveas(gcf,"Summary_stats/1_3_5/Daily_average_volume.png")
% % % % % 
% % % % % % daily average quantity
% % % % % quantity_average_daily = accumarray(idx_month, option.quantity, [], @sum);
% % % % % quantity_average_daily = quantity_average_daily ./ daysInMonth;
% % % % % bar(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd'), quantity_average_daily)
% % % % % ylabel('Daily average option quantity')
% % % % % title('BTC options quantity')
% % % % % xticks(datetime(strcat(unique_month(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % xticklabels(datestr(datetime(strcat(unique_month(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'),'mmmyy'))
% % % % % dateaxis('x',12)
% % % % % saveas(gcf,"Summary_stats/1_3_5/Daily_average_quantity.png")
% % % % % 
% % % % % % daily average transaction
% % % % % transaction_average_daily = accumarray(idx_month, ones(size(option.option_price)), [], @sum);
% % % % % transaction_average_daily = transaction_average_daily ./ daysInMonth;
% % % % % bar(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd'), transaction_average_daily)
% % % % % ylabel('Daily average option transaction')
% % % % % title('BTC options transaction')
% % % % % xticks(datetime(strcat(unique_month(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % xticklabels(datestr(datetime(strcat(unique_month(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'),'mmmyy'))
% % % % % dateaxis('x',12)
% % % % % saveas(gcf,"Summary_stats/1_3_5/Daily_average_transaction.png")
% % % % % 
% % % % % %% numberof transaction, quantity and volume overtime  --  CALL OPTION
% % % % % [unique_date_call, ~, idx_date_call] = unique(string(option_call.date));
% % % % % volume_daily = accumarray(idx_date_call, option_call.option_price.*option_call.quantity, [], @sum);
% % % % % quantity_daily = accumarray(idx_date_call, option_call.quantity, [], @sum);
% % % % % transaction_daily = accumarray(idx_date_call, ones(size(option_call.option_price)), [], @sum);
% % % % % 
% % % % % % daily value
% % % % % figure;
% % % % % plot(datetime(unique_date_call),volume_daily)
% % % % % dateaxis('x',12)
% % % % % title('BTC call options value')
% % % % % ylabel('Daily trading value (quantity \times option price)')
% % % % % xticks(datetime(unique_date_call(round(linspace(1,1996,10)))));
% % % % % xticklabels(datestr(unique_date_call(round(linspace(1,1996,10))),'mmmyy'))
% % % % % saveas(gcf,"Summary_stats/1_3_5/Daily_volume_call.png")
% % % % % % daily quantity
% % % % % plot(datetime(unique_date_call),quantity_daily)
% % % % % dateaxis('x',12)
% % % % % title('BTC call options quantity')
% % % % % ylabel('Daily trading quantity')
% % % % % xticks(datetime(unique_date_call(round(linspace(1,1996,10)))));
% % % % % xticklabels(datestr(unique_date_call(round(linspace(1,1996,10))),'mmmyy'))
% % % % % saveas(gcf,"Summary_stats/1_3_5/Daily_quantity_call.png")
% % % % % % daily transaction
% % % % % plot(datetime(unique_date_call),transaction_daily)
% % % % % dateaxis('x',12)
% % % % % title('BTC call options transaction')
% % % % % ylabel('Daily number of transaction')
% % % % % xticks(datetime(unique_date_call(round(linspace(1,1996,10)))));
% % % % % xticklabels(datestr(unique_date_call(round(linspace(1,1996,10))),'mmmyy'))
% % % % % saveas(gcf,"Summary_stats/1_3_5/Daily_transaction_call.png")
% % % % % 
% % % % % % unique month & days in each month
% % % % % [unique_month, ~, idx_month] = unique(string(datestr(option_call.date,'yyyymm')));
% % % % % daysInMonth = eomday(year(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd')), month(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd')));
% % % % % daysInMonth(end)=17;
% % % % % 
% % % % % % daily average volume
% % % % % volume_average_daily = accumarray(idx_month, option_call.option_price.*option_call.quantity, [], @sum);
% % % % % volume_average_daily = volume_average_daily ./ daysInMonth;
% % % % % bar(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd'), volume_average_daily)
% % % % % ylabel('Daily average option value (quantity \times option price)')
% % % % % title('BTC call options value')
% % % % % xticks(datetime(strcat(unique_month(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % xticklabels(datestr(datetime(strcat(unique_month(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'),'mmmyy'))
% % % % % dateaxis('x',12)
% % % % % saveas(gcf,"Summary_stats/1_3_5/Daily_average_volume_call.png")
% % % % % 
% % % % % % daily average volume
% % % % % quantity_average_daily = accumarray(idx_month, option_call.quantity, [], @sum);
% % % % % quantity_average_daily = quantity_average_daily ./ daysInMonth;
% % % % % bar(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd'), quantity_average_daily)
% % % % % ylabel('Daily average option quantity')
% % % % % title('BTC call options quantity')
% % % % % xticks(datetime(strcat(unique_month(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % xticklabels(datestr(datetime(strcat(unique_month(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'),'mmmyy'))
% % % % % dateaxis('x',12)
% % % % % saveas(gcf,"Summary_stats/1_3_5/Daily_average_quantity_call.png")
% % % % % 
% % % % % % daily average transaction
% % % % % transaction_average_daily = accumarray(idx_month, ones(size(option_call.option_price)), [], @sum);
% % % % % transaction_average_daily = transaction_average_daily ./ daysInMonth;
% % % % % bar(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd'), transaction_average_daily)
% % % % % ylabel('Daily average option transaction')
% % % % % title('BTC call options transaction')
% % % % % xticks(datetime(strcat(unique_month(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % xticklabels(datestr(datetime(strcat(unique_month(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'),'mmmyy'))
% % % % % dateaxis('x',12)
% % % % % saveas(gcf,"Summary_stats/1_3_5/Daily_average_transaction_call.png")
% % % % % 
% % % % % %% numberof transaction, quantity and volume overtime  --  PUT OPTION
% % % % % [unique_date_put, ~, idx_date_put] = unique(string(option_put.date));
% % % % % volume_daily = accumarray(idx_date_put, option_put.option_price.*option_put.quantity, [], @sum);
% % % % % quantity_daily = accumarray(idx_date_put, option_put.quantity, [], @sum);
% % % % % transaction_daily = accumarray(idx_date_put, ones(size(option_put.option_price)), [], @sum);
% % % % % 
% % % % % % daily value
% % % % % plot(datetime(unique_date_put),volume_daily)
% % % % % dateaxis('x',12)
% % % % % title('BTC put options value')
% % % % % ylabel('Daily trading value (quantity \times option price)')
% % % % % xticks(datetime(unique_date_put(round(linspace(1,1996,10)))));
% % % % % xticklabels(datestr(unique_date_put(round(linspace(1,1996,10))),'mmmyy'))
% % % % % saveas(gcf,"Summary_stats/1_3_5/Daily_volume_put.png")
% % % % % % daily quantity
% % % % % plot(datetime(unique_date_put),quantity_daily)
% % % % % dateaxis('x',12)
% % % % % title('BTC put options quantity')
% % % % % ylabel('Daily trading quantity')
% % % % % xticks(datetime(unique_date_put(round(linspace(1,1996,10)))));
% % % % % xticklabels(datestr(unique_date_put(round(linspace(1,1996,10))),'mmmyy'))
% % % % % saveas(gcf,"Summary_stats/1_3_5/Daily_quantity_put.png")
% % % % % % daily transaction
% % % % % plot(datetime(unique_date_put),transaction_daily)
% % % % % dateaxis('x',12)
% % % % % title('BTC put options transaction')
% % % % % ylabel('Daily number of transaction')
% % % % % xticks(datetime(unique_date_put(round(linspace(1,1996,10)))));
% % % % % xticklabels(datestr(unique_date_put(round(linspace(1,1996,10))),'mmmyy'))
% % % % % saveas(gcf,"Summary_stats/1_3_5/Daily_transaction_put.png")
% % % % % 
% % % % % % unique month & days in each month
% % % % % [unique_month, ~, idx_month] = unique(string(datestr(option_put.date,'yyyymm')));
% % % % % daysInMonth = eomday(year(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd')), month(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd')));
% % % % % daysInMonth(end)=17;
% % % % % 
% % % % % % daily average value
% % % % % volume_average_daily = accumarray(idx_month, option_put.option_price.*option_put.quantity, [], @sum);
% % % % % volume_average_daily = volume_average_daily ./ daysInMonth;
% % % % % bar(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd'), volume_average_daily)
% % % % % ylabel('Daily average option value (quantity \times option price)')
% % % % % title('BTC put options value')
% % % % % xticks(datetime(strcat(unique_month(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % xticklabels(datestr(datetime(strcat(unique_month(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'),'mmmyy'))
% % % % % dateaxis('x',12)
% % % % % saveas(gcf,"Summary_stats/1_3_5/Daily_average_volume_put.png")
% % % % % 
% % % % % % daily average volume
% % % % % quantity_average_daily = accumarray(idx_month, option_put.quantity, [], @sum);
% % % % % quantity_average_daily = quantity_average_daily ./ daysInMonth;
% % % % % bar(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd'), quantity_average_daily)
% % % % % ylabel('Daily average option quantity')
% % % % % title('BTC put options quantity')
% % % % % xticks(datetime(strcat(unique_month(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % xticklabels(datestr(datetime(strcat(unique_month(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'),'mmmyy'))
% % % % % dateaxis('x',12)
% % % % % saveas(gcf,"Summary_stats/1_3_5/Daily_average_quantity_put.png")
% % % % % 
% % % % % % daily average transaction
% % % % % transaction_average_daily = accumarray(idx_month, ones(size(option_put.option_price)), [], @sum);
% % % % % transaction_average_daily = transaction_average_daily ./ daysInMonth;
% % % % % bar(datetime(strcat(unique_month,'01'),'InputFormat','uuuuMMdd'), transaction_average_daily)
% % % % % ylabel('Daily average option transaction')
% % % % % title('BTC put options transaction')
% % % % % xticks(datetime(strcat(unique_month(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % xticklabels(datestr(datetime(strcat(unique_month(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'),'mmmyy'))
% % % % % dateaxis('x',12)
% % % % % saveas(gcf,"Summary_stats/1_3_5/Daily_average_transaction_put.png")
% % % % % 
% % % % % %% 2-by-2 quantity, transaction and value PREPARE
% % % % % [~, ~, idx_month] = unique(string(datestr(option.date,'yyyymm')));
% % % % % 
% % % % % quantity_average_daily = accumarray(idx_month, option.quantity, [], @sum);
% % % % % quantity_average_daily = quantity_average_daily ./ daysInMonth;
% % % % % transaction_average_daily = accumarray(idx_month, ones(size(option.option_price)), [], @sum);
% % % % % transaction_average_daily = transaction_average_daily ./ daysInMonth;
% % % % % volume_average_daily = accumarray(idx_month, option.option_price.*option.quantity, [], @sum);
% % % % % volume_average_daily = volume_average_daily ./ daysInMonth;
% % % % % 
% % % % % option_1week = option(((option.tau>=0) & (option.tau<=9)), :);
% % % % % [uniqueDates_1week, ~, idx_1week] = unique(string(datestr(option_1week.date,'yyyymm')));
% % % % % option_1to3week = option(((option.tau>9) & (option.tau<27)), :);
% % % % % [uniqueDates_1to3week, ~, idx_1to3week] = unique(string(datestr(option_1to3week.date,'yyyymm')));
% % % % % option_4week = option(((option.tau>=27) & (option.tau<=33)), :);
% % % % % [uniqueDates_4week, ~, idx_4week] = unique(string(datestr(option_4week.date,'yyyymm')));
% % % % % option_longmaturity = option(((option.tau>33)), :);
% % % % % [uniqueDates_longmaturity, ~, idx_longmaturity] = unique(string(datestr(option_longmaturity.date,'yyyymm')));
% % % % % %% 2-by-2 quantity across time with different tau
% % % % % 
% % % % % % 1week
% % % % % quantity_1week = accumarray(idx_1week, option_1week.quantity, [], @sum);
% % % % % quantity_average_1week = quantity_1week ./ daysInMonth;
% % % % % subplot(2,2,1)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), quantity_average_1week./quantity_average_daily, 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of all BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), quantity_average_1week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), quantity_average_1week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily quantity')
% % % % % title('BTC 1-week tau options')
% % % % % xticks(datetime(strcat(uniqueDates_1week(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % 1 to 3 weeks: 9<tau<27
% % % % % quantity_1to3week = accumarray(idx_1to3week, option_1to3week.quantity, [], @sum);
% % % % % quantity_average_1to3week = quantity_1to3week ./ daysInMonth;
% % % % % subplot(2,2,2)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), quantity_average_1to3week./quantity_average_daily, 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of all BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), quantity_average_1to3week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), quantity_average_1to3week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily volume')
% % % % % title('BTC 1-to-3week-maturity options')
% % % % % xticks(datetime(strcat(uniqueDates_1to3week(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % 4week
% % % % % quantity_4week = accumarray(idx_4week, option_4week.quantity, [], @sum);
% % % % % quantity_average_4week = quantity_4week ./ daysInMonth(1:end-2);
% % % % % subplot(2,2,3)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), quantity_average_4week./quantity_average_daily(1:end-2), 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of all BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), quantity_average_4week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), quantity_average_4week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily volume')
% % % % % title('BTC 4-week options')
% % % % % xticks(datetime(strcat(uniqueDates_4week(round(linspace(1,66-2,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % more than 4 weeks: 33<tau
% % % % % quantity_longmaturity = accumarray(idx_longmaturity, option_longmaturity.quantity, [], @sum);
% % % % % quantity_average_longmaturity = quantity_longmaturity ./ daysInMonth(1:end-2);
% % % % % subplot(2,2,4)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_longmaturity,'01'),'InputFormat','uuuuMMdd'), quantity_average_longmaturity./quantity_average_daily(1:end-2), 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of all BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_longmaturity,'01'),'InputFormat','uuuuMMdd'), quantity_average_longmaturity, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_longmaturity,'01'),'InputFormat','uuuuMMdd'), quantity_average_longmaturity, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily volume')
% % % % % title('BTC longmaturity options')
% % % % % xticks(datetime(strcat(uniqueDates_longmaturity(round(linspace(1,66-2,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % dateaxis('x',12)
% % % % % set(gcf,'Position',[100,100,1200,900])
% % % % % sgtitle("Volumn and percentage of overall options")
% % % % % saveas(gcf,"Summary_stats/1_3_5/quantity_and_percentage_overall.png")
% % % % % 
% % % % % %% 2-by-2 transaction across time with different tau
% % % % % % 1week
% % % % % transaction_1week = accumarray(idx_1week, ones(size(option_1week.quantity)), [], @sum);
% % % % % transaction_average_1week = transaction_1week ./ daysInMonth;
% % % % % figure;
% % % % % subplot(2,2,1)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), transaction_average_1week./transaction_average_daily, 0.8, 'FaceAlpha',0.3);
% % % % % % ylabel('Percentage of all BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), transaction_average_1week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), transaction_average_1week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily transactions','FontSize',20)
% % % % % title('BTC 1-week options','FontSize',20)
% % % % % xticks([datetime(strcat(uniqueDates_1week(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd')])
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % 1 to 3 weeks
% % % % % transaction_1to3week = accumarray(idx_1to3week, ones(size(option_1to3week.quantity)), [], @sum);
% % % % % transaction_average_1to3week = transaction_1to3week ./ daysInMonth;
% % % % % subplot(2,2,2)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), transaction_average_1to3week./transaction_average_daily, 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of transaction','FontSize',20)
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), transaction_average_1to3week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), transaction_average_1to3week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % % ylabel('Average daily transactions')
% % % % % title('BTC 1-to-3week-maturity options','FontSize',20)
% % % % % xticks([datetime(strcat(uniqueDates_1to3week(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd')])
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % 4week
% % % % % transaction_4week = accumarray(idx_4week, ones(size(option_4week.quantity)), [], @sum);
% % % % % transaction_average_4week = transaction_4week ./ daysInMonth(1:end-2);
% % % % % subplot(2,2,3)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), transaction_average_4week./transaction_average_daily(1:end-2), 0.8, 'FaceAlpha',0.3);
% % % % % % ylabel('Percentage of all BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), transaction_average_4week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), transaction_average_4week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % xlabel('Date','FontSize',15)
% % % % % ylabel('Average daily transactions','FontSize',20)
% % % % % title('BTC 4-week options','FontSize',20)
% % % % % xticks(datetime(strcat(uniqueDates_4week(round(linspace(1,66-2,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % long maturity
% % % % % transaction_longmaturity = accumarray(idx_longmaturity, ones(size(option_longmaturity.quantity)), [], @sum);
% % % % % transaction_average_longmaturity = transaction_longmaturity ./ daysInMonth(1:end-2);
% % % % % subplot(2,2,4)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_longmaturity,'01'),'InputFormat','uuuuMMdd'), transaction_average_longmaturity./transaction_average_daily(1:end-2), 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of transaction','FontSize',20)
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_longmaturity ,'01'),'InputFormat','uuuuMMdd'), transaction_average_longmaturity , '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_longmaturity ,'01'),'InputFormat','uuuuMMdd'), transaction_average_longmaturity , 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % % ylabel('Average daily transactions')
% % % % % title('BTC longmaturity-maturity options','FontSize',20)
% % % % % xticks([datetime(strcat(uniqueDates_longmaturity(round(linspace(1,66-2,9))),'01'),'InputFormat','uuuuMMdd')])
% % % % % xlabel('Date','FontSize',15)
% % % % % dateaxis('x',12)
% % % % % set(gcf,'Position',[100,100,1200,900])
% % % % % % sgtitle("Transaction and percentage of overall options")
% % % % % saveas(gcf,"Summary_stats/1_3_5/transaction_and_percentage_overall.png")
% % % % % 
% % % % % %% 2-by-2 value across time with different tau
% % % % % % 1week
% % % % % volume_1week = accumarray(idx_1week, option_1week.quantity.*option_1week.option_price, [], @sum);
% % % % % volume_average_1week = volume_1week ./ daysInMonth;
% % % % % % figure;
% % % % % subplot(2,2,1)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), volume_average_1week./volume_average_daily, 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of all BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), volume_average_1week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), volume_average_1week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily volume')
% % % % % title('BTC 1-week options')
% % % % % xticks([datetime(strcat(uniqueDates_1week(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd')])
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % 1 to 3 weeks
% % % % % volume_1to3week = accumarray(idx_1to3week, option_1to3week.quantity.*option_1to3week.option_price, [], @sum);
% % % % % volume_average_1to3week = volume_1to3week ./ daysInMonth;
% % % % % subplot(2,2,2)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), volume_average_1to3week./volume_average_daily, 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of all BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), volume_average_1to3week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), volume_average_1to3week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily volume')
% % % % % title('BTC 1-to-3week-maturity options')
% % % % % xticks([datetime(strcat(uniqueDates_1to3week(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd')])
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % 4week
% % % % % volume_4week = accumarray(idx_4week, option_4week.quantity.*option_4week.option_price, [], @sum);
% % % % % volume_average_4week = volume_4week ./ daysInMonth(1:end-2);
% % % % % subplot(2,2,3)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), volume_average_4week./volume_average_daily(1:end-2), 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of all BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), volume_average_4week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), volume_average_4week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily volume')
% % % % % title('BTC 4-week options')
% % % % % xticks(datetime(strcat(uniqueDates_4week(round(linspace(1,66-2,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % long maturity
% % % % % volume_longmaturity = accumarray(idx_longmaturity, option_longmaturity.quantity.*option_longmaturity.option_price, [], @sum);
% % % % % volume_average_longmaturity = volume_longmaturity ./ daysInMonth(1:end-2);
% % % % % subplot(2,2,4)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_longmaturity,'01'),'InputFormat','uuuuMMdd'), volume_average_longmaturity./volume_average_daily(1:end-2), 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of all BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_longmaturity ,'01'),'InputFormat','uuuuMMdd'), volume_average_longmaturity , '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_longmaturity ,'01'),'InputFormat','uuuuMMdd'), volume_average_longmaturity , 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily value')
% % % % % title('BTC longmaturity-maturity options')
% % % % % xticks([datetime(strcat(uniqueDates_longmaturity(round(linspace(1,66-2,9))),'01'),'InputFormat','uuuuMMdd')])
% % % % % dateaxis('x',12)
% % % % % sgtitle("Value and percentage overall options")
% % % % % set(gcf,'Position',[100,100,1200,900])
% % % % % saveas(gcf,"Summary_stats/1_3_5/volume_and_percentage_overall.png")
% % % % % 
% % % % % %% 2-by-2 quantity, transaction and value PREPARE -- CALL OPTION
% % % % % [~, ~, idx_month_call] = unique(string(datestr(option_call.date,'yyyymm')));
% % % % % 
% % % % % quantity_average_daily = accumarray(idx_month_call, option_call.quantity, [], @sum);
% % % % % quantity_average_daily = quantity_average_daily ./ daysInMonth;
% % % % % transaction_average_daily = accumarray(idx_month_call, ones(size(option_call.option_price)), [], @sum);
% % % % % transaction_average_daily = transaction_average_daily ./ daysInMonth;
% % % % % volume_average_daily = accumarray(idx_month_call, option_call.option_price.*option_call.quantity, [], @sum);
% % % % % volume_average_daily = volume_average_daily ./ daysInMonth;
% % % % % 
% % % % % option_call_1week = option_call(((option_call.tau>=0) & (option_call.tau<=9)), :);
% % % % % [uniqueDates_1week, ~, idx_1week] = unique(string(datestr(option_call_1week.date,'yyyymm')));
% % % % % option_call_1to3week = option_call(((option_call.tau>9) & (option_call.tau<27)), :);
% % % % % [uniqueDates_1to3week, ~, idx_1to3week] = unique(string(datestr(option_call_1to3week.date,'yyyymm')));
% % % % % option_call_4week = option_call(((option_call.tau>=27) & (option_call.tau<=33)), :);
% % % % % [uniqueDates_4week, ~, idx_4week] = unique(string(datestr(option_call_4week.date,'yyyymm')));
% % % % % option_call_longmaturity = option_call(((option_call.tau>33)), :);
% % % % % [uniqueDates_longmaturity, ~, idx_longmaturity] = unique(string(datestr(option_call_longmaturity.date,'yyyymm')));
% % % % % %% 2-by-2 quantity across time with different tau -- CALL OPTION
% % % % % 
% % % % % % 1week
% % % % % quantity_1week = accumarray(idx_1week, option_call_1week.quantity, [], @sum);
% % % % % quantity_average_1week = quantity_1week ./ daysInMonth;
% % % % % % figure;
% % % % % subplot(2,2,1)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), quantity_average_1week./quantity_average_daily, 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of call BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), quantity_average_1week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), quantity_average_1week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily quantity')
% % % % % title('BTC 1-week tau call options')
% % % % % xticks(datetime(strcat(uniqueDates_1week(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % 1 to 3 weeks: 9<tau<27
% % % % % quantity_1to3week = accumarray(idx_1to3week, option_call_1to3week.quantity, [], @sum);
% % % % % quantity_average_1to3week = quantity_1to3week ./ daysInMonth;
% % % % % subplot(2,2,2)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), quantity_average_1to3week./quantity_average_daily, 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of call BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), quantity_average_1to3week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), quantity_average_1to3week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily quantity')
% % % % % title('BTC 1-to-3week-maturity call options')
% % % % % xticks(datetime(strcat(uniqueDates_1to3week(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % 4week
% % % % % quantity_4week = accumarray(idx_4week, option_call_4week.quantity, [], @sum);
% % % % % quantity_average_4week = quantity_4week ./ daysInMonth(1:end-2);
% % % % % subplot(2,2,3)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), quantity_average_4week./quantity_average_daily(1:end-2), 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of call BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), quantity_average_4week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), quantity_average_4week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily quantity')
% % % % % title('BTC 4-week call options')
% % % % % xticks(datetime(strcat(uniqueDates_4week(round(linspace(1,66-2,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % more than 4 weeks: 33<tau
% % % % % quantity_longmaturity = accumarray(idx_longmaturity, option_call_longmaturity.quantity, [], @sum);
% % % % % quantity_average_longmaturity = quantity_longmaturity ./ daysInMonth(1:end-2);
% % % % % subplot(2,2,4)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_longmaturity,'01'),'InputFormat','uuuuMMdd'), quantity_average_longmaturity./quantity_average_daily(1:end-2), 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of call BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_longmaturity,'01'),'InputFormat','uuuuMMdd'), quantity_average_longmaturity, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_longmaturity,'01'),'InputFormat','uuuuMMdd'), quantity_average_longmaturity, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily quantity')
% % % % % title('BTC longmaturity call options')
% % % % % xticks(datetime(strcat(uniqueDates_longmaturity(round(linspace(1,66-2,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % dateaxis('x',12)
% % % % % set(gcf,'Position',[100,100,1200,900])
% % % % % sgtitle("Volumn and percentage of call options")
% % % % % saveas(gcf,"Summary_stats/1_3_5/quantity_and_percentage_call.png")
% % % % % 
% % % % % %% 2-by-2 transaction across time with different tau -- CALL OPTION
% % % % % % 1week
% % % % % transaction_1week = accumarray(idx_1week, ones(size(option_call_1week.quantity)), [], @sum);
% % % % % transaction_average_1week = transaction_1week ./ daysInMonth;
% % % % % % figure;
% % % % % subplot(2,2,1)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), transaction_average_1week./transaction_average_daily, 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of call BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), transaction_average_1week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), transaction_average_1week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily transactions')
% % % % % title('BTC 1-week call options')
% % % % % xticks([datetime(strcat(uniqueDates_1week(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd')])
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % 1 to 3 weeks
% % % % % transaction_1to3week = accumarray(idx_1to3week, ones(size(option_call_1to3week.quantity)), [], @sum);
% % % % % transaction_average_1to3week = transaction_1to3week ./ daysInMonth;
% % % % % subplot(2,2,2)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), transaction_average_1to3week./transaction_average_daily, 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of call BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), transaction_average_1to3week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), transaction_average_1to3week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily transactions')
% % % % % title('BTC 1-to-3week-maturity call options')
% % % % % xticks([datetime(strcat(uniqueDates_1to3week(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd')])
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % 4week
% % % % % transaction_4week = accumarray(idx_4week, ones(size(option_call_4week.quantity)), [], @sum);
% % % % % transaction_average_4week = transaction_4week ./ daysInMonth(1:end-2);
% % % % % subplot(2,2,3)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), transaction_average_4week./transaction_average_daily(1:end-2), 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of call BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), transaction_average_4week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), transaction_average_4week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily transactions')
% % % % % title('BTC 4-week call options')
% % % % % xticks(datetime(strcat(uniqueDates_4week(round(linspace(1,66-2,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % long maturity
% % % % % transaction_longmaturity = accumarray(idx_longmaturity, ones(size(option_call_longmaturity.quantity)), [], @sum);
% % % % % transaction_average_longmaturity = transaction_longmaturity ./ daysInMonth(1:end-2);
% % % % % subplot(2,2,4)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_longmaturity,'01'),'InputFormat','uuuuMMdd'), transaction_average_longmaturity./transaction_average_daily(1:end-2), 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of call BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_longmaturity ,'01'),'InputFormat','uuuuMMdd'), transaction_average_longmaturity , '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_longmaturity ,'01'),'InputFormat','uuuuMMdd'), transaction_average_longmaturity , 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily transactions')
% % % % % title('BTC longmaturity-maturity call options')
% % % % % xticks([datetime(strcat(uniqueDates_longmaturity(round(linspace(1,66-2,9))),'01'),'InputFormat','uuuuMMdd')])
% % % % % dateaxis('x',12)
% % % % % set(gcf,'Position',[100,100,1200,900])
% % % % % sgtitle("Transaction and percentage of call options")
% % % % % saveas(gcf,"Summary_stats/1_3_5/transaction_and_percentage_call.png")
% % % % % 
% % % % % %% 2-by-2 value across time with different tau -- CALL OPTION
% % % % % % 1week
% % % % % volume_1week = accumarray(idx_1week, option_call_1week.quantity.*option_call_1week.option_price, [], @sum);
% % % % % volume_average_1week = volume_1week ./ daysInMonth;
% % % % % % figure;
% % % % % subplot(2,2,1)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), volume_average_1week./volume_average_daily, 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of call BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), volume_average_1week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), volume_average_1week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily volume')
% % % % % title('BTC 1-week call options')
% % % % % xticks([datetime(strcat(uniqueDates_1week(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd')])
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % 1 to 3 weeks
% % % % % volume_1to3week = accumarray(idx_1to3week, option_call_1to3week.quantity.*option_call_1to3week.option_price, [], @sum);
% % % % % volume_average_1to3week = volume_1to3week ./ daysInMonth;
% % % % % subplot(2,2,2)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), volume_average_1to3week./volume_average_daily, 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of call BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), volume_average_1to3week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), volume_average_1to3week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily volume')
% % % % % title('BTC 1-to-3week-maturity call options')
% % % % % xticks([datetime(strcat(uniqueDates_1to3week(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd')])
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % 4week
% % % % % volume_4week = accumarray(idx_4week, option_call_4week.quantity.*option_call_4week.option_price, [], @sum);
% % % % % volume_average_4week = volume_4week ./ daysInMonth(1:end-2);
% % % % % subplot(2,2,3)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), volume_average_4week./volume_average_daily(1:end-2), 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of call BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), volume_average_4week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), volume_average_4week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily volume')
% % % % % title('BTC 4-week call options')
% % % % % xticks(datetime(strcat(uniqueDates_4week(round(linspace(1,66-2,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % long maturity
% % % % % volume_longmaturity = accumarray(idx_longmaturity, option_call_longmaturity.quantity.*option_call_longmaturity.option_price, [], @sum);
% % % % % volume_average_longmaturity = volume_longmaturity ./ daysInMonth(1:end-2);
% % % % % subplot(2,2,4)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_longmaturity,'01'),'InputFormat','uuuuMMdd'), volume_average_longmaturity./volume_average_daily(1:end-2), 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of call BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_longmaturity ,'01'),'InputFormat','uuuuMMdd'), volume_average_longmaturity , '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_longmaturity ,'01'),'InputFormat','uuuuMMdd'), volume_average_longmaturity , 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily volume')
% % % % % title('BTC longmaturity-maturity call options')
% % % % % xticks([datetime(strcat(uniqueDates_longmaturity(round(linspace(1,66-2,9))),'01'),'InputFormat','uuuuMMdd')])
% % % % % dateaxis('x',12)
% % % % % set(gcf,'Position',[100,100,1200,900])
% % % % % sgtitle("Value and percentage of call options")
% % % % % saveas(gcf,"Summary_stats/1_3_5/volume_and_percentage_call.png")
% % % % % 
% % % % % 
% % % % % %% 2-by-2 quantity, transaction and volume PREPARE -- PUT OPTION
% % % % % [~, ~, idx_month_put] = unique(string(datestr(option_put.date,'yyyymm')));
% % % % % 
% % % % % quantity_average_daily = accumarray(idx_month_put, option_put.quantity, [], @sum);
% % % % % quantity_average_daily = quantity_average_daily ./ daysInMonth;
% % % % % transaction_average_daily = accumarray(idx_month_put, ones(size(option_put.option_price)), [], @sum);
% % % % % transaction_average_daily = transaction_average_daily ./ daysInMonth;
% % % % % volume_average_daily = accumarray(idx_month_put, option_put.option_price.*option_put.quantity, [], @sum);
% % % % % volume_average_daily = volume_average_daily ./ daysInMonth;
% % % % % 
% % % % % option_put_1week = option_put(((option_put.tau>=0) & (option_put.tau<=9)), :);
% % % % % [uniqueDates_1week, ~, idx_1week] = unique(string(datestr(option_put_1week.date,'yyyymm')));
% % % % % option_put_1to3week = option_put(((option_put.tau>9) & (option_put.tau<27)), :);
% % % % % [uniqueDates_1to3week, ~, idx_1to3week] = unique(string(datestr(option_put_1to3week.date,'yyyymm')));
% % % % % option_put_4week = option_put(((option_put.tau>=27) & (option_put.tau<=33)), :);
% % % % % [uniqueDates_4week, ~, idx_4week] = unique(string(datestr(option_put_4week.date,'yyyymm')));
% % % % % option_put_longmaturity = option_put(((option_put.tau>33)), :);
% % % % % [uniqueDates_longmaturity, ~, idx_longmaturity] = unique(string(datestr(option_put_longmaturity.date,'yyyymm')));
% % % % % %% 2-by-2 quantity across time with different tau -- PUT OPTION
% % % % % 
% % % % % % 1week
% % % % % quantity_1week = accumarray(idx_1week, option_put_1week.quantity, [], @sum);
% % % % % quantity_average_1week = quantity_1week ./ daysInMonth;
% % % % % % figure;
% % % % % subplot(2,2,1)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), quantity_average_1week./quantity_average_daily, 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of put BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), quantity_average_1week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), quantity_average_1week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily quantity')
% % % % % title('BTC 1-week tau put options')
% % % % % xticks(datetime(strcat(uniqueDates_1week(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % 1 to 3 weeks: 9<tau<27
% % % % % quantity_1to3week = accumarray(idx_1to3week, option_put_1to3week.quantity, [], @sum);
% % % % % quantity_average_1to3week = quantity_1to3week ./ daysInMonth;
% % % % % subplot(2,2,2)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), quantity_average_1to3week./quantity_average_daily, 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of put BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), quantity_average_1to3week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), quantity_average_1to3week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily quantity')
% % % % % title('BTC 1-to-3week-maturity put options')
% % % % % xticks(datetime(strcat(uniqueDates_1to3week(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % 4week
% % % % % quantity_4week = accumarray(idx_4week, option_put_4week.quantity, [], @sum);
% % % % % quantity_average_4week = quantity_4week ./ daysInMonth(1:end-2);
% % % % % subplot(2,2,3)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), quantity_average_4week./quantity_average_daily(1:end-2), 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of put BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), quantity_average_4week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), quantity_average_4week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily quantity')
% % % % % title('BTC 4-week put options')
% % % % % xticks(datetime(strcat(uniqueDates_4week(round(linspace(1,66-2,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % more than 4 weeks: 33<tau
% % % % % quantity_longmaturity = accumarray(idx_longmaturity, option_put_longmaturity.quantity, [], @sum);
% % % % % quantity_average_longmaturity = quantity_longmaturity ./ daysInMonth(1:end-2);
% % % % % subplot(2,2,4)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_longmaturity,'01'),'InputFormat','uuuuMMdd'), quantity_average_longmaturity./quantity_average_daily(1:end-2), 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of put BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_longmaturity,'01'),'InputFormat','uuuuMMdd'), quantity_average_longmaturity, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_longmaturity,'01'),'InputFormat','uuuuMMdd'), quantity_average_longmaturity, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily quantity')
% % % % % title('BTC longmaturity put options')
% % % % % xticks(datetime(strcat(uniqueDates_longmaturity(round(linspace(1,66-2,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % dateaxis('x',12)
% % % % % set(gcf,'Position',[100,100,1200,900])
% % % % % saveas(gcf,"Summary_stats/1_3_5/quantity_and_percentage_put.png")
% % % % % 
% % % % % %% 2-by-2 transaction across time with different tau -- PUT OPTION
% % % % % % 1week
% % % % % transaction_1week = accumarray(idx_1week, ones(size(option_put_1week.quantity)), [], @sum);
% % % % % transaction_average_1week = transaction_1week ./ daysInMonth;
% % % % % % figure;
% % % % % subplot(2,2,1)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), transaction_average_1week./transaction_average_daily, 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of put BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), transaction_average_1week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), transaction_average_1week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily transactions')
% % % % % title('BTC 1-week put options')
% % % % % xticks([datetime(strcat(uniqueDates_1week(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd')])
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % 1 to 3 weeks
% % % % % transaction_1to3week = accumarray(idx_1to3week, ones(size(option_put_1to3week.quantity)), [], @sum);
% % % % % transaction_average_1to3week = transaction_1to3week ./ daysInMonth;
% % % % % subplot(2,2,2)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), transaction_average_1to3week./transaction_average_daily, 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of put BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), transaction_average_1to3week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), transaction_average_1to3week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily transactions')
% % % % % title('BTC 1-to-3week-maturity put options')
% % % % % xticks([datetime(strcat(uniqueDates_1to3week(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd')])
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % 4week
% % % % % transaction_4week = accumarray(idx_4week, ones(size(option_put_4week.quantity)), [], @sum);
% % % % % transaction_average_4week = transaction_4week ./ daysInMonth(1:end-2);
% % % % % subplot(2,2,3)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), transaction_average_4week./transaction_average_daily(1:end-2), 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of put BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), transaction_average_4week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), transaction_average_4week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily transactions')
% % % % % title('BTC 4-week put options')
% % % % % xticks(datetime(strcat(uniqueDates_4week(round(linspace(1,66-2,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % long maturity
% % % % % transaction_longmaturity = accumarray(idx_longmaturity, ones(size(option_put_longmaturity.quantity)), [], @sum);
% % % % % transaction_average_longmaturity = transaction_longmaturity ./ daysInMonth(1:end-2);
% % % % % subplot(2,2,4)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_longmaturity,'01'),'InputFormat','uuuuMMdd'), transaction_average_longmaturity./transaction_average_daily(1:end-2), 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of put BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_longmaturity ,'01'),'InputFormat','uuuuMMdd'), transaction_average_longmaturity , '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_longmaturity ,'01'),'InputFormat','uuuuMMdd'), transaction_average_longmaturity , 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily transactions')
% % % % % title('BTC longmaturity-maturity put options')
% % % % % xticks([datetime(strcat(uniqueDates_longmaturity(round(linspace(1,66-2,9))),'01'),'InputFormat','uuuuMMdd')])
% % % % % dateaxis('x',12)
% % % % % set(gcf,'Position',[100,100,1200,900])
% % % % % sgtitle("Transaction and percentage of put options")
% % % % % saveas(gcf,"Summary_stats/1_3_5/transaction_and_percentage_put.png")
% % % % % 
% % % % % %% 2-by-2 volume across time with different tau -- PUT OPTION
% % % % % % 1week
% % % % % volume_1week = accumarray(idx_1week, option_put_1week.quantity.*option_put_1week.option_price, [], @sum);
% % % % % volume_average_1week = volume_1week ./ daysInMonth;
% % % % % % figure;
% % % % % subplot(2,2,1)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), volume_average_1week./volume_average_daily, 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of put BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), volume_average_1week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_1week,'01'),'InputFormat','uuuuMMdd'), volume_average_1week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily volume')
% % % % % title('BTC 1-week put options')
% % % % % xticks([datetime(strcat(uniqueDates_1week(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd')])
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % 1 to 3 weeks
% % % % % volume_1to3week = accumarray(idx_1to3week, option_put_1to3week.quantity.*option_put_1to3week.option_price, [], @sum);
% % % % % volume_average_1to3week = volume_1to3week ./ daysInMonth;
% % % % % subplot(2,2,2)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), volume_average_1to3week./volume_average_daily, 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of put BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), volume_average_1to3week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_1to3week,'01'),'InputFormat','uuuuMMdd'), volume_average_1to3week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily volume')
% % % % % title('BTC 1-to-3week-maturity put options')
% % % % % xticks([datetime(strcat(uniqueDates_1to3week(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd')])
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % 4week
% % % % % volume_4week = accumarray(idx_4week, option_put_4week.quantity.*option_put_4week.option_price, [], @sum);
% % % % % volume_average_4week = volume_4week ./ daysInMonth(1:end-2);
% % % % % subplot(2,2,3)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), volume_average_4week./volume_average_daily(1:end-2), 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of put BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), volume_average_4week, '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_4week,'01'),'InputFormat','uuuuMMdd'), volume_average_4week, 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily volume')
% % % % % title('BTC 4-week put options')
% % % % % xticks(datetime(strcat(uniqueDates_4week(round(linspace(1,66-2,9))),'01'),'InputFormat','uuuuMMdd'));
% % % % % dateaxis('x',12)
% % % % % 
% % % % % % long maturity
% % % % % volume_longmaturity = accumarray(idx_longmaturity, option_put_longmaturity.quantity.*option_put_longmaturity.option_price, [], @sum);
% % % % % volume_average_longmaturity = volume_longmaturity ./ daysInMonth(1:end-2);
% % % % % subplot(2,2,4)
% % % % % yyaxis right
% % % % % bar(datetime(strcat(uniqueDates_longmaturity,'01'),'InputFormat','uuuuMMdd'), volume_average_longmaturity./volume_average_daily(1:end-2), 0.8, 'FaceAlpha',0.3);
% % % % % ylabel('Percentage of put BTC options')
% % % % % yyaxis left
% % % % % plot(datetime(strcat(uniqueDates_longmaturity ,'01'),'InputFormat','uuuuMMdd'), volume_average_longmaturity , '-',...
% % % % %     'LineWidth', 2);hold on
% % % % % scatter(datetime(strcat(uniqueDates_longmaturity ,'01'),'InputFormat','uuuuMMdd'), volume_average_longmaturity , 20, ...
% % % % %     [0 0.4470 0.7410],'Filled');hold off
% % % % % ylabel('Average daily volume')
% % % % % title('BTC longmaturity-maturity put options')
% % % % % xticks([datetime(strcat(uniqueDates_longmaturity(round(linspace(1,66-2,9))),'01'),'InputFormat','uuuuMMdd')])
% % % % % dateaxis('x',12)
% % % % % set(gcf,'Position',[100,100,1200,900])
% % % % % sgtitle("Value and percentage of put options")
% % % % % saveas(gcf,"Summary_stats/1_3_5/volume_and_percentage_put.png")
% % % % % % 
% % % % % % %% stacked bar
% % % % % % monthlyVolume1 = volume_average_1week(1:(end-2));
% % % % % % monthlyVolume2 = volume_average_1to3week(1:(end-2));
% % % % % % monthlyVolume3 = volume_average_4week;
% % % % % % monthlyVolume4 = volume_average_longmaturity;
% % % % % % date_monthly = datetime(strcat(uniqueDates(1:(end-2)),'01'),'InputFormat','uuuuMMdd');
% % % % % % figure;
% % % % % % bar(date_monthly, [monthlyVolume1, monthlyVolume2, monthlyVolume3, monthlyVolume4], 'stacked');
% % % % % % ylabel('Trading Volume');
% % % % % % title('Monthly Trading Volume and Proportion of options');
% % % % % % legend('\tau<=9', '9<\tau<27', '27<=<\tau<=33', '\tau>33','Location','northwest');
% % % % % % xticks([datetime(strcat(uniqueDates_1week(round(linspace(1,66,9))),'01'),'InputFormat','uuuuMMdd')])
% % % % % % dateaxis('x',12)
% % % % % % % Add percentage labels to the bars
% % % % % % totals = monthlyVolume1 + monthlyVolume2 + monthlyVolume3 + monthlyVolume4;
% % % % % % percent1 = monthlyVolume1 ./ totals;
% % % % % % percent2 = monthlyVolume2 ./ totals;
% % % % % % percent3 = monthlyVolume3 ./ totals;
% % % % % % percent4 = monthlyVolume4 ./ totals;
% % % % % % percent = [percent1, percent2, percent3, percent4];
% % % % % % monthlyTotalVolume = monthlyVolume1+ monthlyVolume2+ monthlyVolume3+ monthlyVolume4;
% % % % % % monthlyAvgVolume = trading_quantity_average(1:(end-2));
% % % % % % % for i = 1:length(date_monthly)
% % % % % % %     x = date_monthly(i);
% % % % % % %     y = monthlyTotalVolume(i);
% % % % % % %     txt = sprintf('%.1f%%\n%.2f', percent(i,:)*100, monthlyAvgVolume(i));
% % % % % % %     text(x, y, txt, 'HorizontalAlignment','center','VerticalAlignment','bottom')
% % % % % % % end
% % % % % % saveas(gcf,"Summary_stats/1_3_5/Daily_average_quantity_and_proportion.png")
% % % % % %% moneyness range
% % % % % % figure;
% % % % % % yyaxis left
% % % % % % plot(option.date,log(option.moneyness),'.')
% % % % % % ylabel('Log moneyness: log(K/S_\tau)')
% % % % % % yyaxis right
% % % % % % plot(BTC_Dvol.date,BTC_Dvol.index,'-')
% % % % % % ylabel('BTC volatility index')
% % % % % % xticks(datetime(unique_date(round(linspace(1,1996,10)))));
% % % % % % xticklabels(datestr(unique_date(round(linspace(1,1996,10))),'mmmyy'))
% % % % % 
% % % % % % figure;
% % % % % % plot(option.date,log(option.moneyness),'.')
% % % % % % ylabel('Log moneyness: log(K/S_\tau)')
% % % % % % xticks(datetime(unique_date(round(linspace(1,1996,10)))));
% % % % % % xticklabels(datestr(unique_date(round(linspace(1,1996,10))),'mmmyy'))
% % % % % % saveas(gcf,"Summary_stats/1_3_5/Moneyness_range.png")
% % % % % 

%% sort by date, putcall, K
[~,I]=sortrows(option,["date","putcall","K"]);
option1 = option(I,:);

%% Summary statistics of option variables for call and puts separately
option_call = option(strcmp(option.putcall,'C'),:);
tau=round([mean(option_call.tau);median(option_call.tau);std(option_call.tau);min(option_call.tau);max(option_call.tau);size(option_call,1)],2);
moneyness=round([mean(option_call.moneyness);median(option_call.moneyness);std(option_call.moneyness);min(option_call.moneyness);max(option_call.moneyness);size(option_call,1)],2);
IV=round([mean(option_call.IV);median(option_call.IV);std(option_call.IV);min(option_call.IV);max(option_call.IV);size(option_call,1)*100]/100,2);
tb = table(tau,moneyness, IV);
tb.Properties.RowNames = {'Mean', 'Median', 'Std. Dev.', 'Min', 'Max','Total'};
writetable(tb,"Summary_stats/1_3_5/sum_stats_variables_call.csv")

option_put = option(strcmp(option.putcall,'P'),:);
tau=round([mean(option_put.tau);median(option_put.tau);std(option_put.tau);min(option_put.tau);max(option_put.tau);size(option_call,1)],2);
moneyness=round([mean(option_put.moneyness);median(option_put.moneyness);std(option_put.moneyness);min(option_put.moneyness);max(option_put.moneyness);size(option_call,1)],2);
IV=round([mean(option_put.IV);median(option_put.IV);std(option_put.IV);min(option_put.IV);max(option_put.IV);size(option_call,1)*100]/100,2);
tb = table(tau,moneyness, IV);
tb.Properties.RowNames = {'Mean', 'Median', 'Std. Dev.', 'Min', 'Man','Total'};
writetable(tb,"Summary_stats/1_3_5/sum_stats_variables_put.csv")
