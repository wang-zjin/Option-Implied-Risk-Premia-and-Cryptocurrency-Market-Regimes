clear,clc
BVIX_DVOL = readtable("data/BVIX/BVIX_DVOL.csv");
output_folder = "BVIX/";
[~,~,~] = mkdir(output_folder);
%% BVIX and DVOL
figure;
plot(BVIX_DVOL.DateTime,BVIX_DVOL.VIX,'k-','LineWidth',2);hold on
plot(BVIX_DVOL.DateTime,BVIX_DVOL.BTCVolatilityIndex_DVOL_,'k--','LineWidth',2);hold off
xlim([min(BVIX_DVOL.DateTime)-10,max(BVIX_DVOL.DateTime)+10])
numTicks = 9; % Number of ticks
tickLocations = linspace(min(BVIX_DVOL.DateTime), max(BVIX_DVOL.DateTime), numTicks);
xticks(tickLocations);
dateaxis('x',12)
set(gcf,'Position',[0,0,1500,600])
set(gca,'FontSize',20)
legend(["BVIX","DVOL"],"FontSize",30,"Box","off")
saveas(gcf,strcat(output_folder,"BVIX_DVOL.png"))