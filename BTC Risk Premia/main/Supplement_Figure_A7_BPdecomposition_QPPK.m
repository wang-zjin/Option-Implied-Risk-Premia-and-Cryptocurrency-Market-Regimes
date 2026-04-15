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



%% Calculate BP
fP_overall = mean(fP, 1);
fP_HV = mean(fP(index0, :), 1);
fP_LV = mean(fP(index1, :), 1);

fQ_overall = mean(fQ, 1);
fQ_HV = mean(fQ(index0,:), 1);
fQ_LV = mean(fQ(index1,:), 1);

BP_overall = zeros(size(fQ_overall));
BP_HV = zeros(size(fQ_HV));
BP_LV = zeros(size(fQ_LV));

for i = 2:numel(BP_overall)
    BP_overall(i) = trapz(R_vec(1:i)',(fP_overall(1:i) -fQ_overall(1:i)).*R_vec(1:i)') *del;
    BP_HV(i) = trapz(R_vec(1:i)',(fP_HV(1:i) -fQ_HV(1:i)).*R_vec(1:i)') *del;
    BP_LV(i) = trapz(R_vec(1:i)',(fP_LV(1:i) -fQ_LV(1:i)).*R_vec(1:i)') *del;
end
BP_overall   = BP_overall/BP_overall(end);
BP_HV        = BP_HV/BP_HV(end);
BP_LV        = BP_LV/BP_LV(end);

%% Plot BP overall
shadow_x_negative = [-0.6, -0.2];
shadow_x_positive = [0.2, 0.6];
figure;
plot(R_vec,BP_overall,'Color','k','LineWidth',2);hold on

x_shaded = [shadow_x_negative(1), shadow_x_negative(2), shadow_x_negative(2), shadow_x_negative(1)];% x-coordinates of the shaded area
y_shaded = [-1.5, -1.5, 8, 8];                                       % y-coordinates of the shaded area
fill(x_shaded, y_shaded, 'k', 'FaceAlpha', 0.05, 'EdgeColor','none'); % 'k' for black color, 10% transparent
x_shaded = [ shadow_x_positive(1), shadow_x_positive(2), shadow_x_positive(2), shadow_x_positive(1)]; % x-coordinates of the shaded area
y_shaded = [-1.5, -1.5, 8, 8];                                       % y-coordinates of the shaded area
fill(x_shaded, y_shaded, 'k', 'FaceAlpha', 0.05, 'EdgeColor','none'); % 'k' for black color, 10% transparent
hold off
xlim([-1,1]),ylim([0,1.5])
xticks([-1,-0.8,-0.6,-0.4,-0.2,0,0.2,0.4,0.6,0.8,1])
xlabel('Return','FontSize',15)
legend('$\widehat{BP}_{OA}$','FontSize',15,'Interpreter','latex','Location','Northwest','box','off')

set(gcf,'Position',[0,0,450,300])
ax = gca;
ax.FontSize = 15;
ax.YAxis.LineWidth = 1; % Increase the line width of the Y-axis
ax.XAxis.LineWidth = 1; % Increase the line width of the Y-axis
saveas(gcf,"RiskPremia/multivariate_clustering_9_27_45/BP_SS2025_OA.png")

BP_sub1 = BP_overall(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
BP_sub2 = BP_overall(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
disp([BP_sub1(end)-BP_sub1(1),BP_sub2(end)-BP_sub2(1)])

%% Plot BP for 2 HV cluster 
shadow_x_negative = [-0.6, -0.2];
shadow_x_positive = [0.2, 0.6];
figure;
plot(R_vec,BP_HV,'Color','b','LineWidth',2);hold on

x_shaded = [shadow_x_negative(1), shadow_x_negative(2), shadow_x_negative(2), shadow_x_negative(1)];                                 % x-coordinates of the shaded area
y_shaded = [-1.5, -1.5, 8, 8];                                       % y-coordinates of the shaded area
fill(x_shaded, y_shaded, 'b', 'FaceAlpha', 0.05, 'EdgeColor','none'); % 'k' for black color, 10% transparent
x_shaded = [ shadow_x_positive(1), shadow_x_positive(2), shadow_x_positive(2), shadow_x_positive(1)];                                 % x-coordinates of the shaded area
y_shaded = [-1.5, -1.5, 8, 8];                                       % y-coordinates of the shaded area
fill(x_shaded, y_shaded, 'b', 'FaceAlpha', 0.05, 'EdgeColor','none'); % 'k' for black color, 10% transparent
hold off
xlim([-1,1]),ylim([0,1.5])
xticks([-1,-0.8,-0.6,-0.4,-0.2,0,0.2,0.4,0.6,0.8,1])
xlabel('Return','FontSize',15)
legend('$\widehat{BP}_{HV}$','FontSize',15,'Interpreter','latex','Location','Northwest','box','off')

set(gcf,'Position',[0,0,450,300])
ax = gca;
ax.FontSize = 15;
ax.YAxis.LineWidth = 1; % Increase the line width of the Y-axis
ax.XAxis.LineWidth = 1; % Increase the line width of the Y-axis
saveas(gcf,"RiskPremia/multivariate_clustering_9_27_45/BP_SS2025_HV.png")


BP_sub1 = BP_HV(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
BP_sub2 = BP_HV(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
disp([BP_sub1(end)-BP_sub1(1),BP_sub2(end)-BP_sub2(1)])

%% Plot BP for 2 LV cluster
shadow_x_negative = [-0.6, -0.2];
shadow_x_positive = [0.2, 0.6];
figure;
plot(R_vec,BP_LV,'Color','r','LineWidth',2);hold on

x_shaded = [shadow_x_negative(1), shadow_x_negative(2), shadow_x_negative(2), shadow_x_negative(1)];                                 % x-coordinates of the shaded area
y_shaded = [-1.5, -1.5, 8, 8];                                       % y-coordinates of the shaded area
fill(x_shaded, y_shaded, 'r', 'FaceAlpha', 0.05, 'EdgeColor','none'); % 'k' for black color, 10% transparent
x_shaded = [ shadow_x_positive(1), shadow_x_positive(2), shadow_x_positive(2), shadow_x_positive(1)];                                 % x-coordinates of the shaded area
y_shaded = [-1.5, -1.5, 8, 8];                                       % y-coordinates of the shaded area
fill(x_shaded, y_shaded, 'r', 'FaceAlpha', 0.05, 'EdgeColor','none'); % 'k' for black color, 10% transparent
hold off
xlim([-1,1]),ylim([0,1.5])
xticks([-1,-0.8,-0.6,-0.4,-0.2,0,0.2,0.4,0.6,0.8,1])
xlabel('Return','FontSize',15)
legend('$\widehat{BP}_{LV}$','FontSize',15,'Interpreter','latex','Location','Northwest','box','off')

set(gcf,'Position',[0,0,450,300])
ax = gca;
ax.FontSize = 15;
ax.YAxis.LineWidth = 1; % Increase the line width of the Y-axis
ax.XAxis.LineWidth = 1; % Increase the line width of the Y-axis
saveas(gcf,"RiskPremia/multivariate_clustering_9_27_45/BP_SS2025_LV.png")


BP_sub1 = BP_LV(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
BP_sub2 = BP_LV(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
disp([BP_sub1(end)-BP_sub1(1),BP_sub2(end)-BP_sub2(1)])

%% Plot BP for OA, HV, LV

figure;
plot(R_vec,BP_overall,'Color','k','LineWidth',2);hold on
plot(R_vec,BP_HV,'Color','b','LineWidth',2);
plot(R_vec,BP_LV,'Color','r','LineWidth',2);

hold off
% grid on
xlim([-1,1]),ylim([0,1.5])
xticks([-1,-0.8,-0.6,-0.4,-0.2,0,0.2,0.4,0.6,0.8,1])
% ylabel('$\hat{BP}$','FontSize',20,'Interpreter','tex')
xlabel('Return','FontSize',15)
% title("Overall",'FontSize',20)
legend(["$\widehat{BP}_{OA}$","$\widehat{BP}_{HV}$","$\widehat{BP}_{LV}$"],'FontSize',15,'Interpreter','latex','Location','Northwest','box','off')

set(gcf,'Position',[0,0,450,300])
ax = gca;
ax.FontSize = 15;
% ax.YAxis.FontWeight = 'bold'; % Make Y-axis tick labels bold
ax.YAxis.LineWidth = 1; % Increase the line width of the Y-axis
ax.XAxis.LineWidth = 1; % Increase the line width of the Y-axis
% sgtitle(strcat('BP, full sample overlapping empirical PDF by rescaled returns'),'FontSize',30)
saveas(gcf,"RiskPremia/multivariate_clustering_9_27_45/BP_SS2025.png")

%% Plot Q, P, Q/P for overall
% Focus on TTM 27
shadow_x_negative = [-0.6, -0.2];
shadow_x_positive = [0.2, 0.6];
figure;

plot(nan,nan,'-','Color','k','LineWidth',2);hold on
plot(nan,nan,'--','Color','k','LineWidth',2);
plot(nan,nan,'-.','Color','k','LineWidth',1);

x_shaded = [shadow_x_negative(1), shadow_x_negative(2), shadow_x_negative(2), shadow_x_negative(1)];% x-coordinates of the shaded area
y_shaded = [-0.5, -0.5, 6, 6];                                       % y-coordinates of the shaded area
fill(x_shaded, y_shaded, 'k', 'FaceAlpha', 0.05, 'EdgeColor','none'); % 'k' for black color, 10% transparent
x_shaded = [ shadow_x_positive(1), shadow_x_positive(2), shadow_x_positive(2), shadow_x_positive(1)]; % x-coordinates of the shaded area
y_shaded = [-0.5, -0.5, 6, 6];                                       % y-coordinates of the shaded area
fill(x_shaded, y_shaded, 'k', 'FaceAlpha', 0.05, 'EdgeColor','none'); % 'k' for black color, 10% transparent

plot(R_vec,fQ_overall','-','Color','k','LineWidth',2);
plot(R_vec,fP_overall','--','Color','k','LineWidth',2);
plot(R_vec,fQ_overall'./fP_overall','-.','Color','k','LineWidth',2);
hold off
legend(["$\hat{q}$","$\hat{p}$","$\widehat{PK}$"],'FontSize',15,'Location','northwest','Interpreter','latex','Box','off')
xticks([-1,-0.8,-0.6,-0.4,-0.2,0,0.2,0.4,0.6,0.8,1])
xlabel('Return')
xlim([-1,1])
ylim([0,4])
grid off
set(gcf,'Position',[0,0,450,300]);  
ax = gca;
ax.FontSize = 15;
ax.YAxis.LineWidth = 1; % Increase the line width of the Y-axis
ax.XAxis.LineWidth = 1; % Increase the line width of the Y-axis

saveas(gcf,"RiskPremia/multivariate_clustering_9_27_45/QP_OA.png")
EP=trapz(R_vec,R_vec.*fP_overall);
EQ=trapz(R_vec,R_vec.*fQ_overall);
disp([EP,EQ,EP-EQ])

% Compute P(r< negative shadow upper limit) and P(r< negative shadow lower limit)
index = (R_vec<shadow_x_negative(2));
P_negative_upper = trapz(R_vec(index), fP_overall(index));
disp(['The probability of return <',num2str(shadow_x_negative(2)),' is ',num2str(P_negative_upper)])
index = (R_vec<shadow_x_negative(1));
P_negative_lower = trapz(R_vec(index), fP_overall(index));
disp(['The probability of return <',num2str(shadow_x_negative(1)),' is ',num2str(P_negative_lower)])
% Compute P(r< positive shadow upper limit) and P(r< positive shadow lower limit)
index = (R_vec<shadow_x_positive(1));
P_positive_lower = trapz(R_vec(index), fP_overall(index));
disp(['The probability of return >',num2str(shadow_x_positive(1)),' is ',num2str(P_positive_lower)])
index = (R_vec>shadow_x_positive(2));
P_positive_upper = trapz(R_vec(index), fP_overall(index));
disp(['The probability of return >',num2str(shadow_x_positive(2)),' is ',num2str(P_positive_upper)])

%% Plot q, p, PK, for HV cluster
% Focus on TTM 27
shadow_x_negative = [-0.6, -0.2];
shadow_x_positive = [0.2, 0.6];
figure;

plot(nan,nan,'-','Color','b','LineWidth',2);hold on
plot(nan,nan,'--','Color','b','LineWidth',2);
plot(nan,nan,'-.','Color','b','LineWidth',2);

plot(R_vec,fQ_HV,'-','Color','b','LineWidth',2);
plot(R_vec,fP_HV,'--','Color','b','LineWidth',2);
plot(R_vec,fQ_HV./fP_HV,'-.','Color','b','LineWidth',2);

x_shaded = [shadow_x_negative(1), shadow_x_negative(2), shadow_x_negative(2), shadow_x_negative(1)];% x-coordinates of the shaded area
y_shaded = [-0.5, -0.5, 6, 6];                                       % y-coordinates of the shaded area
fill(x_shaded, y_shaded, 'b', 'FaceAlpha', 0.05, 'EdgeColor','none'); % 'k' for black color, 10% transparent
x_shaded = [ shadow_x_positive(1), shadow_x_positive(2), shadow_x_positive(2), shadow_x_positive(1)];% x-coordinates of the shaded area
y_shaded = [-0.5, -0.5, 6, 6];                                       % y-coordinates of the shaded area
fill(x_shaded, y_shaded, 'b', 'FaceAlpha', 0.05, 'EdgeColor','none'); % 'k' for black color, 10% transparent
hold off
legend(["$\hat{q}_{HV}$","$\hat{p}_{HV}$","$\widehat{PK}_{HV}$"],'FontSize',15,'Location','northwest','Interpreter','latex','Box','off')
ylim([0,4])
xlim([-1,1])
xticks([-1,-0.8,-0.6,-0.4,-0.2,0,0.2,0.4,0.6,0.8,1])
xlabel('Return','FontSize',15)
set(gcf,'Position',[0,0,450,300]);  
ax = gca;
ax.FontSize = 15;
ax.YAxis.LineWidth = 1; % Increase the line width of the Y-axis
ax.XAxis.LineWidth = 1; % Increase the line width of the Y-axis
saveas(gcf,"RiskPremia/multivariate_clustering_9_27_45/QP_HV.png")
%% Plot q, p, PK, for LV cluster
% Focus on TTM 27
shadow_x_negative = [-0.6, -0.2];
shadow_x_positive = [0.2, 0.6];
figure;

plot(nan,nan,'-','Color','r','LineWidth',2);hold on
plot(nan,nan,'--','Color','r','LineWidth',2);
plot(nan,nan,'-.','Color','r','LineWidth',2);

plot(R_vec,fQ_LV,'-','Color','r','LineWidth',2);
plot(R_vec,fP_LV,'--','Color','r','LineWidth',2);
plot(R_vec,fQ_LV./fP_LV,'-.','Color','r','LineWidth',2);


x_shaded = [shadow_x_negative(1), shadow_x_negative(2), shadow_x_negative(2), shadow_x_negative(1)];% x-coordinates of the shaded area
y_shaded = [-0.5, -0.5, 6, 6];                                       % y-coordinates of the shaded area
fill(x_shaded, y_shaded, 'r', 'FaceAlpha', 0.05, 'EdgeColor','none'); % 'k' for black color, 10% transparent
x_shaded = [ shadow_x_positive(1), shadow_x_positive(2), shadow_x_positive(2), shadow_x_positive(1)];% x-coordinates of the shaded area
y_shaded = [-0.5, -0.5, 6, 6];                                       % y-coordinates of the shaded area
fill(x_shaded, y_shaded, 'r', 'FaceAlpha', 0.05, 'EdgeColor','none'); % 'k' for black color, 10% transparent
hold off
% grid on
legend(["$\hat{q}_{LV}$","$\hat{p}_{LV}$","$\widehat{PK}_{LV}$"],'FontSize',15,'Location','northwest','Interpreter','latex','Box','off')
ylim([0,4])
xlim([-1,1])
xticks([-1,-0.8,-0.6,-0.4,-0.2,0,0.2,0.4,0.6,0.8,1])
xlabel('Return','FontSize',15)
% ylabel('PK','FontSize',15)
set(gcf,'Position',[0,0,450,300]);  
ax = gca;
ax.FontSize = 15;
% ax.YAxis.FontWeight = 'bold'; % Make Y-axis tick labels bold
ax.YAxis.LineWidth = 1; % Increase the line width of the Y-axis
ax.XAxis.LineWidth = 1; % Increase the line width of the Y-axis
saveas(gcf,"RiskPremia/multivariate_clustering_9_27_45/QP_LV.png")


%% Plot PK of OA, HV, LV in the same figure
% Focus on TTM 27
figure;

plot(nan,nan,'-.','Color','k','LineWidth',2);hold on
plot(nan,nan,'-.','Color','b','LineWidth',2);
plot(nan,nan,'-.','Color','r','LineWidth',2);

plot(R_vec,fQ_overall./fP_overall,'-.','Color','k','LineWidth',2);
plot(R_vec,fQ_HV./fP_HV,'-.','Color','b','LineWidth',2);
plot(R_vec,fQ_LV./fP_LV,'-.','Color','r','LineWidth',2);

hold off
% grid on
legend(["$\widehat{PK}_{OA}$","$\widehat{PK}_{HV}$","$\widehat{PK}_{LV}$"],'FontSize',15,'Location','northeast','Interpreter','latex','Box','off')
ylim([0,4])
xlim([-1,1])
xticks([-1,-0.8,-0.6,-0.4,-0.2,0,0.2,0.4,0.6,0.8,1])
xlabel('Return','FontSize',15)
% ylabel('PK','FontSize',15)
set(gcf,'Position',[0,0,450,300]);  
ax = gca;
ax.FontSize = 15;
% ax.YAxis.FontWeight = 'bold'; % Make Y-axis tick labels bold
ax.YAxis.LineWidth = 1; % Increase the line width of the Y-axis
ax.XAxis.LineWidth = 1; % Increase the line width of the Y-axis
saveas(gcf,"RiskPremia/multivariate_clustering_9_27_45/PK_SS2025.png")


%% Plot P of OA, HV, LV in the same figure
% Focus on TTM 27
figure;

plot(nan,nan,'-.','Color','k','LineWidth',2);hold on
plot(nan,nan,'-.','Color','b','LineWidth',2);
plot(nan,nan,'-.','Color','r','LineWidth',2);

plot(R_vec,fP_overall,'-.','Color','k','LineWidth',2);
plot(R_vec,fP_HV,'-.','Color','b','LineWidth',2);
plot(R_vec,fP_LV,'-.','Color','r','LineWidth',2);

hold off
% grid on
legend(["$\widehat{P}_{OA}$","$\widehat{P}_{HV}$","$\widehat{P}_{LV}$"],'FontSize',15,'Location','northeast','Interpreter','latex','Box','off')
ylim([0,4])
xlim([-1,1])
xticks([-1,-0.8,-0.6,-0.4,-0.2,0,0.2,0.4,0.6,0.8,1])
xlabel('Return','FontSize',15)
% ylabel('PK','FontSize',15)
set(gcf,'Position',[0,0,450,300]);  
ax = gca;
ax.FontSize = 15;
% ax.YAxis.FontWeight = 'bold'; % Make Y-axis tick labels bold
ax.YAxis.LineWidth = 1; % Increase the line width of the Y-axis
ax.XAxis.LineWidth = 1; % Increase the line width of the Y-axis
saveas(gcf,"RiskPremia/multivariate_clustering_9_27_45/P_SS2025.png")

%% Plot Q of OA, HV, LV in the same figure
% Focus on TTM 27
figure;

plot(nan,nan,'-.','Color','k','LineWidth',2);hold on
plot(nan,nan,'-.','Color','b','LineWidth',2);
plot(nan,nan,'-.','Color','r','LineWidth',2);

plot(R_vec,fQ_overall,'-.','Color','k','LineWidth',2);
plot(R_vec,fQ_HV,'-.','Color','b','LineWidth',2);
plot(R_vec,fQ_LV,'-.','Color','r','LineWidth',2);

hold off
% grid on
legend(["$\widehat{Q}_{OA}$","$\widehat{Q}_{HV}$","$\widehat{Q}_{LV}$"],'FontSize',15,'Location','northeast','Interpreter','latex','Box','off')
ylim([0,4])
xlim([-1,1])
xticks([-1,-0.8,-0.6,-0.4,-0.2,0,0.2,0.4,0.6,0.8,1])
xlabel('Return','FontSize',15)
% ylabel('PK','FontSize',15)
set(gcf,'Position',[0,0,450,300]);  
ax = gca;
ax.FontSize = 15;
% ax.YAxis.FontWeight = 'bold'; % Make Y-axis tick labels bold
ax.YAxis.LineWidth = 1; % Increase the line width of the Y-axis
ax.XAxis.LineWidth = 1; % Increase the line width of the Y-axis
saveas(gcf,"RiskPremia/multivariate_clustering_9_27_45/Q_SS2025.png")
