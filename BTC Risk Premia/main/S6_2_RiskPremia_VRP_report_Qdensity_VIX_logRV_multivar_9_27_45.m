% This version is what we use in the draft



clc,clear
tb_Qdensity_RV_VRP_cluster0 = readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Variance_Risk_Premium/VRP_Qdensity_logRV_HV.csv");
tb_Qdensity_RV_VRP_cluster1 = readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Variance_Risk_Premium/VRP_Qdensity_logRV_LV.csv");
tb_Qdensity_RV_VRP_overall = [tb_Qdensity_RV_VRP_cluster0;tb_Qdensity_RV_VRP_cluster1];
tb_VIX_RV_VRP_cluster0 = readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Variance_Risk_Premium/VRP_VIX_logRV_HV.csv");
tb_VIX_RV_VRP_cluster1 = readtable("RiskPremia/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/Variance_Risk_Premium/VRP_VIX_logRV_LV.csv");
tb_VIX_RV_VRP_overall = [tb_VIX_RV_VRP_cluster0;tb_VIX_RV_VRP_cluster1];

%% Moments ANOVA of cluster 0 and 1 (annualized)
% P: backward density
cluster_label_0_Qdensity = [repmat("cluster_0",height(tb_Qdensity_RV_VRP_cluster0),1);repmat("overall",height(tb_Qdensity_RV_VRP_overall),1)];
cluster_label_1_Qdensity = [repmat("cluster_1",height(tb_Qdensity_RV_VRP_cluster1),1);repmat("overall",height(tb_Qdensity_RV_VRP_overall),1)];
cluster_label_0_VIX = [repmat("cluster_0",height(tb_VIX_RV_VRP_cluster0),1);repmat("overall",height(tb_VIX_RV_VRP_overall),1)];
cluster_label_1_VIX = [repmat("cluster_1",height(tb_VIX_RV_VRP_cluster1),1);repmat("overall",height(tb_VIX_RV_VRP_overall),1)];
% Q: Q density vs VIX
[~,tbl11,stats11] = anova1([tb_Qdensity_RV_VRP_cluster0.Q_variance_Qdensity;tb_Qdensity_RV_VRP_overall.Q_variance_Qdensity],cluster_label_0_Qdensity);
[~,tbl12,stats12] = anova1([tb_Qdensity_RV_VRP_cluster1.Q_variance_Qdensity;tb_Qdensity_RV_VRP_overall.Q_variance_Qdensity],cluster_label_1_Qdensity);
[~,tbl13,stats13] = anova1([tb_VIX_RV_VRP_cluster0.Q_variance_VIX;tb_VIX_RV_VRP_overall.Q_variance_VIX],cluster_label_0_VIX);
[~,tbl14,stats14] = anova1([tb_VIX_RV_VRP_cluster1.Q_variance_VIX;tb_VIX_RV_VRP_overall.Q_variance_VIX],cluster_label_1_VIX);
[~,tbl31,stats31] = anova1([tb_Qdensity_RV_VRP_cluster0.VRP;tb_Qdensity_RV_VRP_overall.VRP],cluster_label_0_Qdensity);
[~,tbl32,stats32] = anova1([tb_Qdensity_RV_VRP_cluster1.VRP;tb_Qdensity_RV_VRP_overall.VRP],cluster_label_1_Qdensity);
[~,tbl33,stats33] = anova1([tb_VIX_RV_VRP_cluster0.VRP;tb_VIX_RV_VRP_overall.VRP],cluster_label_0_VIX);
[~,tbl34,stats34] = anova1([tb_VIX_RV_VRP_cluster1.VRP;tb_VIX_RV_VRP_overall.VRP],cluster_label_1_VIX);
[~,tbl51,stats51] = anova1([tb_Qdensity_RV_VRP_cluster0.RV;tb_Qdensity_RV_VRP_overall.RV],cluster_label_0_Qdensity);
[~,tbl52,stats52] = anova1([tb_Qdensity_RV_VRP_cluster1.RV;tb_Qdensity_RV_VRP_overall.RV],cluster_label_1_Qdensity);
[~,tbl53,stats53] = anova1([tb_VIX_RV_VRP_cluster0.RV;tb_VIX_RV_VRP_overall.RV],cluster_label_0_VIX);
[~,tbl54,stats54] = anova1([tb_VIX_RV_VRP_cluster1.RV;tb_VIX_RV_VRP_overall.RV],cluster_label_1_VIX);

VRP_difference=nan(7,6);
VRP_difference(1,:)=[stats31.means(2),stats31.means(1),stats32.means(1),stats33.means(2),stats33.means(1),stats34.means(1)];
VRP_difference(2,[2,3,5,6])=[tbl31{2,6},tbl32{2,6},tbl33{2,6},tbl34{2,6}];
VRP_difference(3,:)=[stats11.means(2),stats11.means(1),stats12.means(1),stats13.means(2),stats13.means(1),stats14.means(1)];
VRP_difference(4,[2,3,5,6])=[tbl11{2,6},tbl12{2,6},tbl13{2,6},tbl14{2,6}];
VRP_difference(5,:)=[stats51.means(2),stats51.means(1),stats52.means(1),stats53.means(2),stats53.means(1),stats54.means(1)];
VRP_difference(6,[2,3,5,6])=[tbl51{2,6},tbl52{2,6},tbl53{2,6},tbl54{2,6}];
VRP_difference(7,:)=[height(tb_Qdensity_RV_VRP_overall),height(tb_Qdensity_RV_VRP_cluster0),height(tb_Qdensity_RV_VRP_cluster1),...
    height(tb_VIX_RV_VRP_overall),height(tb_VIX_RV_VRP_cluster0),height(tb_VIX_RV_VRP_cluster1)];
clear info;
info.rnames = strvcat('.','VRP','p-value','Q ann variance','p-value','P ann variance','p-value','Num of obser');
info.cnames = strvcat('Overall','Cluster 0','Cluster 1','Overall','Cluster 0','Cluster 1');
info.fmt    = '%10.2f';
disp('Q average vs. VIX average')
mprint(VRP_difference,info)

close all