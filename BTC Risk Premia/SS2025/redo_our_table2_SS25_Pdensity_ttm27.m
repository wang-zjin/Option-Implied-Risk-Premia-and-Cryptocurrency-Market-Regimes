%% Load cluster
common_dates = readtable('data_prep/data_BTC/common_dates_cluster.csv');
common_dates.Date = str2num(datestr(datetime(common_dates.Date, "Format","uuuuMMdd", "InputFormat", "uuuu-MM-dd"), 'yyyymmdd'));
dates = string(common_dates.Date);
dates_list = datetime(dates, "InputFormat","uuuuMMdd", "Format", "yyyymmdd");
index0 = common_dates.Cluster==0;
index1 = common_dates.Cluster==1;
dates_Q{1,1} = dates_list(index0);
dates_Q{1,2} = dates_list(index1);

IR = readtable("data_prep/data_BTC/IR_daily.csv");
IR.index=datetime(IR.index);
IR.DTB3=IR.DTB3/100;
IR = renamevars(IR,"index","Date");

index_IR = ismember(IR.Date, dates_list);
IR = IR.DTB3(index_IR);


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

PK = fQ ./ fP;

BP_VRP_SS=nan(6,3);
BP_VRP_SS(2,:)=[mean(ER_P),mean(ER_P(index0,:)),mean(ER_P(index1,:))]*365/27;
% BP_VRP_SS(3,:)=[mean(ER_Q),mean(ER_Q(index0,:)),mean(ER_Q(index1,:))]*365/27;
BP_VRP_SS(3,:)=[mean(IR),mean(IR(index0,:)),mean(IR(index1,:))];
BP_VRP_SS(1,:)=BP_VRP_SS(2,:)-BP_VRP_SS(3,:);
BP_VRP_SS(5,:)=[mean(var_Q),mean(var_Q(index0,:)),mean(var_Q(index1,:))]*365/27;
BP_VRP_SS(6,:)=[mean(var_P),mean(var_P(index0,:)),mean(var_P(index1,:))]*365/27;
BP_VRP_SS(4,:)=BP_VRP_SS(5,:)-BP_VRP_SS(6,:);
clear info;
info.rnames = strvcat('.','E_P-E_Q','E_P: P density','E_Q: Q density','VRP','Var_Q','Var_P');
info.cnames = strvcat('Overall','Cluster 0','Cluster 1');
info.fmt    = '%10.2f';
mprint(BP_VRP_SS,info)


%% BP table

% BP: Pdensity - Qdensity

E_P_OA=mean(fP * R_vec) * 365/27 * del;
E_P_HV=mean(fP(index0,:) * R_vec) * 365/27 * del;
E_P_LV=mean(fP(index1,:) * R_vec) * 365/27 * del;

E_Q_OA=mean(fQ * R_vec) * del;
E_Q_HV=mean(fQ(index0,:) * R_vec) * del;
E_Q_LV=mean(fQ(index1,:) * R_vec) * del;

BP_density_cluster=nan(3,3);
BP_density_cluster(1,:)=[E_P_OA,E_P_HV,E_P_LV];
%BP_density_cluster(2,:)=[E_Q_OA,E_Q_HV,E_Q_LV];
BP_density_cluster(2,:)=[mean(IR),mean(IR(index0,:)),mean(IR(index1,:))];
BP_density_cluster(3,:)=BP_density_cluster(1,:)-BP_density_cluster(2,:);
BP_density_cluster = BP_density_cluster([3,1,2],:);
clear info;
info.rnames = strvcat('.','E_P-E_Q','E_P: P density','E_Q: Q density');
info.cnames = strvcat('Overall','Cluster 0','Cluster 1');
info.fmt    = '%10.2f';
mprint(BP_density_cluster,info)

%% Write VRP
ttm = 27;
tb_date_cluster0 = table(dates_Q{1,1},'VariableNames',"Date");
tb_date_cluster1 = table(dates_Q{1,2},'VariableNames',"Date");
tb_date_overall = table(dates_list,'VariableNames',"Date");
%% P variance

tb_Pdensity_cluster0 = [tb_date_cluster0, table(var_P(index0) * 365/ttm,'VariableNames',"Pvar"),table(zeros(size(tb_date_cluster0)),'VariableNames',"Cluster")];
tb_Pdensity_cluster1 = [tb_date_cluster1, table(sig_t(index1,1).^2 * 365/ttm,'VariableNames',"Pvar"),table(ones(size(tb_date_cluster1)),'VariableNames',"Cluster")];
tb_Pdensity_overall = [tb_date_overall, table(sig_t(:,1).^2 * 365/ttm,'VariableNames',"Pvar"),table(common_dates.Cluster,'VariableNames',"Cluster")];
%% Introduce VIX
VIX = readtable(['data_prep/data_BTC/btc_vix_EWA_',num2str(ttm),'.csv']);
VIX.Date = datetime(VIX.Date, "Format", "uuuuMMdd", "InputFormat", "uuuu-MM-dd");
Q_vola_VIX_cluster0=VIX.EMA((ismember(VIX.Date,dates_list(index0))))/100;
Q_vola_VIX_cluster1=VIX.EMA((ismember(VIX.Date,dates_list(index1))))/100;
Q_vola_VIX_overall=VIX.EMA((ismember(VIX.Date,dates_list)))/100;
tb_Q_variance_VIX_cluster0 = array2table(Q_vola_VIX_cluster0.^2,'VariableNames',"Q_variance_VIX");
tb_Q_variance_VIX_cluster1 = array2table(Q_vola_VIX_cluster1.^2,'VariableNames',"Q_variance_VIX");
tb_Q_variance_VIX_overall = array2table(Q_vola_VIX_overall.^2,'VariableNames',"Q_variance_VIX");
tb_Q_date_VIX_cluster0 = table(VIX.Date((ismember(VIX.Date,dates_list(index0)))),'VariableNames',"Date");
tb_Q_date_VIX_cluster1 = table(VIX.Date((ismember(VIX.Date,dates_list(index1)))),'VariableNames',"Date");
tb_Q_date_VIX_overall = table(VIX.Date((ismember(VIX.Date,dates_list))),'VariableNames',"Date");
tb_Q_variance_VIX_cluster0 = [tb_Q_date_VIX_cluster0, tb_Q_variance_VIX_cluster0];
tb_Q_variance_VIX_cluster1 = [tb_Q_date_VIX_cluster1, tb_Q_variance_VIX_cluster1];
tb_Q_variance_VIX_overall = [tb_Q_date_VIX_overall, tb_Q_variance_VIX_overall];

%% Generate table "tb_VIX_Pdensity_VRP"
tb_VIX_Pdensity_VRP_cluster0 = innerjoin(tb_Q_variance_VIX_cluster0, tb_Pdensity_cluster0,"Key","Date");
tb_VIX_Pdensity_VRP_cluster1 = innerjoin(tb_Q_variance_VIX_cluster1, tb_Pdensity_cluster1,"Key","Date");
tb_VIX_Pdensity_VRP_overall = innerjoin(tb_Q_variance_VIX_overall, tb_Pdensity_overall,"Key","Date");
tb_VIX_Pdensity_VRP_cluster0 = addvars(tb_VIX_Pdensity_VRP_cluster0, tb_VIX_Pdensity_VRP_cluster0.Q_variance_VIX-tb_VIX_Pdensity_VRP_cluster0.Pvar, 'NewVariableNames',"VRP");
tb_VIX_Pdensity_VRP_cluster1 = addvars(tb_VIX_Pdensity_VRP_cluster1, tb_VIX_Pdensity_VRP_cluster1.Q_variance_VIX-tb_VIX_Pdensity_VRP_cluster1.Pvar, 'NewVariableNames',"VRP");
tb_VIX_Pdensity_VRP_overall = addvars(tb_VIX_Pdensity_VRP_overall, tb_VIX_Pdensity_VRP_overall.Q_variance_VIX-tb_VIX_Pdensity_VRP_overall.Pvar, 'NewVariableNames',"VRP");

%% Save tb_VIX_Pdensity_VRP_HV, tb_VIX_Pdensity_VRP_LV
writetable(tb_VIX_Pdensity_VRP_cluster0,"data_prep/data_BTC/RiskPremia/multivariate_clustering_9_27_45/Variance_Risk_Premium/VRP_VIX_Pdensity_HV.csv");
writetable(tb_VIX_Pdensity_VRP_cluster1,"data_prep/data_BTC/RiskPremia/multivariate_clustering_9_27_45/Variance_Risk_Premium/VRP_VIX_Pdensity_LV.csv");

%% Report VRP

tb_VIX_Pdensity_VRP_cluster0 = readtable("data_prep/data_BTC/RiskPremia/multivariate_clustering_9_27_45/Variance_Risk_Premium/VRP_VIX_Pdensity_HV.csv");
tb_VIX_Pdensity_VRP_cluster1 = readtable("data_prep/data_BTC/RiskPremia/multivariate_clustering_9_27_45/Variance_Risk_Premium/VRP_VIX_Pdensity_LV.csv");
tb_VIX_Pdensity_VRP_overall = [tb_VIX_Pdensity_VRP_cluster0;tb_VIX_Pdensity_VRP_cluster1];

%% Moments ANOVA of cluster 0 and 1 (annualized)
% P: backward density
cluster_label_0_VIX = [repmat("cluster_0",height(tb_VIX_Pdensity_VRP_cluster0),1);repmat("overall",height(tb_VIX_Pdensity_VRP_overall),1)];
cluster_label_1_VIX = [repmat("cluster_1",height(tb_VIX_Pdensity_VRP_cluster1),1);repmat("overall",height(tb_VIX_Pdensity_VRP_overall),1)];
% Q: Q density vs VIX
[~,tbl_VRP_HV,stats_VRP_HV] = anova1([tb_VIX_Pdensity_VRP_cluster0.VRP;tb_VIX_Pdensity_VRP_overall.VRP],cluster_label_0_VIX);
[~,tbl_VRP_LV,stats_VRP_LV] = anova1([tb_VIX_Pdensity_VRP_cluster1.VRP;tb_VIX_Pdensity_VRP_overall.VRP],cluster_label_1_VIX);
[~,tbl_VarQ_HV,stats_VarQ_HV] = anova1([tb_VIX_Pdensity_VRP_cluster0.Q_variance_VIX;tb_VIX_Pdensity_VRP_overall.Q_variance_VIX],cluster_label_0_VIX);
[~,tbl_VarQ_LV,stats_VarQ_LV] = anova1([tb_VIX_Pdensity_VRP_cluster1.Q_variance_VIX;tb_VIX_Pdensity_VRP_overall.Q_variance_VIX],cluster_label_1_VIX);
[~,tbl_VarP_HV,stats_VarP_HV] = anova1([tb_VIX_Pdensity_VRP_cluster0.Pvar;tb_VIX_Pdensity_VRP_overall.Pvar],cluster_label_0_VIX);
[~,tbl_VarP_LV,stats_VarP_LV] = anova1([tb_VIX_Pdensity_VRP_cluster1.Pvar;tb_VIX_Pdensity_VRP_overall.Pvar],cluster_label_1_VIX);

VRP_difference=nan(7,3);
VRP_difference(1,:)=[stats_VRP_HV.means(2),stats_VRP_HV.means(1),stats_VRP_LV.means(1)];
VRP_difference(2,[2,3])=[tbl_VRP_HV{2,6},tbl_VRP_LV{2,6}];
VRP_difference(3,:)=[stats_VarQ_HV.means(2),stats_VarQ_HV.means(1),stats_VarQ_LV.means(1)];
VRP_difference(4,[2,3])=[tbl_VarQ_HV{2,6},tbl_VarQ_LV{2,6}];
VRP_difference(5,:)=[stats_VarP_HV.means(2),stats_VarP_HV.means(1),stats_VarP_LV.means(1)];
VRP_difference(6,[2,3])=[tbl_VarP_HV{2,6},tbl_VarP_LV{2,6}];
VRP_difference(7,:)=[height(tb_VIX_Pdensity_VRP_overall),height(tb_VIX_Pdensity_VRP_cluster0),height(tb_VIX_Pdensity_VRP_cluster1)];
clear info;
info.rnames = strvcat('.','VRP','p-value','Q ann variance','p-value','P ann variance','p-value','Num of obser');
info.cnames = strvcat('Overall','Cluster 0','Cluster 1');
info.fmt    = '%10.2f';
disp('Q average vs. VIX average')
mprint(VRP_difference,info)

close all
