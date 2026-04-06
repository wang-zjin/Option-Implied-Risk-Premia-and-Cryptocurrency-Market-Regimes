
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


ff = figure('Position', [100, 100, 595, 700]);
   set(ff,'Units','Inches');
   pos = get(ff,'Position');
   set(ff,'PaperPositionMode','Auto','PaperUnits','Inches','PaperSize',[pos(3), pos(4)]) 
subplot = @(m,n,p)subtightplot(m, n, p, [0.06 0.06], [0.04 0.035], [0.05 0.01]);
datesNum = datenum(num2str(dates),'yyyymmdd');

SP=subplot(4,1,1); 
hold on; 
h = area([min(datesNum),min(datesNum)],[70,70],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits'); 
% h = area([min(datesNum(dates>=20071201)),min(datesNum(dates>=20090630))],[70,70],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits'); 
% h = area([min(datesNum(dates>=20200201)),min(datesNum(dates>=20200430))],[70,70],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits'); 
% h = area([min(datesNum(dates>=20010301)),min(datesNum(dates>=20011131))],[70,70],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits'); 
% h = area([min(datesNum(dates>=19900701)),min(datesNum(dates>=19910331))],[70,70],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits'); 
plot(datesNum,1200*(ER_P-ER_Q),'color',0.8*[.24 .69 .59]); %ylim([0,50]); 
grid on; box on; set(gca,'FontSize',12); xlim([min(datesNum), max(datesNum)]); datetick('x', 'yyyy', 'keeplimits'); title('$E_t[R_{t+1}]-E_t^*[R_{t+1}]$','FontSize',13,'interpreter','latex'); set(gca,'XTickLabel',[]); SP.Layer = 'top';


SP=subplot(4,1,2); 
hold on; 
% h = area([min(datesNum(dates>=20071201)),min(datesNum(dates>=20090630))],[90,90],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits'); 
% h = area([min(datesNum(dates>=20200201)),min(datesNum(dates>=20200430))],[90,90],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits'); 
% h = area([min(datesNum(dates>=20010301)),min(datesNum(dates>=20011131))],[90,90],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits'); 
% h = area([min(datesNum(dates>=19900701)),min(datesNum(dates>=19910331))],[90,90],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits'); 
plot(datesNum,sqrt(12)*100*std_P,'color',0.8*[.24 .69 .59]); %ylim([0,75]); 
grid on; box on; set(gca,'FontSize',12); xlim([min(datesNum), max(datesNum)]); datetick('x', 'yyyy', 'keeplimits'); title('Std$_t[R_{t+1}]$','FontSize',13,'interpreter','latex'); set(gca,'XTickLabel',[]); SP.Layer = 'top';

SP=subplot(4,1,3); 
hold on; 
% h = area([min(datesNum(dates>=20071201)),min(datesNum(dates>=20090630))],[60,60],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits'); 
% h = area([min(datesNum(dates>=20071201)),min(datesNum(dates>=20090630))],[-60,-60],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits'); 
% h = area([min(datesNum(dates>=20200201)),min(datesNum(dates>=20200430))],[60,60],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits'); 
% h = area([min(datesNum(dates>=20200201)),min(datesNum(dates>=20200430))],[-60,-60],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits'); 
% h = area([min(datesNum(dates>=20010301)),min(datesNum(dates>=20011131))],[70,70],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits'); 
% h = area([min(datesNum(dates>=20010301)),min(datesNum(dates>=20011131))],[-70,-70],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits'); 
% h = area([min(datesNum(dates>=19900701)),min(datesNum(dates>=19910331))],[70,70],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits'); 
% h = area([min(datesNum(dates>=19900701)),min(datesNum(dates>=19910331))],[-70,-70],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits'); 
plot([-1e6,1e6],[0,0],'k','LineWidth',0.5)
plot(datesNum,skew_P,'color',0.8*[.24 .69 .59]); %ylim([-2,1]); 
grid on; box on; set(gca,'FontSize',12); xlim([min(datesNum), max(datesNum)]); datetick('x', 'yyyy', 'keeplimits'); title('Skew$_t[R_{t+1}]$','FontSize',13,'interpreter','latex'); set(gca,'XTickLabel',[]); SP.Layer = 'top';

SP=subplot(4,1,4); 
hold on; 
% h = area([min(datesNum(dates>=20071201)),min(datesNum(dates>=20090630))],[60,60],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits'); 
% h = area([min(datesNum(dates>=20071201)),min(datesNum(dates>=20090630))],[-60,-60],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits');
% h = area([min(datesNum(dates>=20200201)),min(datesNum(dates>=20200430))],[60,60],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits'); 
% h = area([min(datesNum(dates>=20200201)),min(datesNum(dates>=20200430))],[-60,-60],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits'); 
% h = area([min(datesNum(dates>=20010301)),min(datesNum(dates>=20011131))],[70,70],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits'); 
% h = area([min(datesNum(dates>=20010301)),min(datesNum(dates>=20011131))],[-70,-70],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits'); 
% h = area([min(datesNum(dates>=19900701)),min(datesNum(dates>=19910331))],[70,70],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits'); 
% h = area([min(datesNum(dates>=19900701)),min(datesNum(dates>=19910331))],[-70,-70],'LineStyle','none'); hold on; h(1).FaceColor = [0.90,0.90,0.90]; datetick('x', 'yyyy', 'keeplimits'); 
plot(datesNum,kurt_P,'color',0.8*[.24 .69 .59]); grid on; box on; set(gca,'FontSize',12); xlim([min(datesNum), max(datesNum)]); datetick('x', 'yyyy', 'keeplimits'); title('Kurt$_t[R_{t+1}]$','FontSize',13,'interpreter','latex'); SP.Layer = 'top';
ylim([0,10])
saveas(ff, 'figure_3_BTC.png')
%print(gcf,'figure_3','-dpdf','-r0')


% disp([mean(1200*ER_P),mean(1200*ER_Q)])
% disp(100*[mean(sqrt(12*var_P)),mean(sqrt(12*var_Q))])
% disp([mean(skew_P),mean(skew_Q)])
% disp([mean(kurt_P),mean(kurt_Q)])
% 
% for i=1:5
%     [~,~,~,~,fP_i] = LL(theta_0(i,1:i+1),i,ln_fQ,r30,log(sig_t),r_vec,ln_fQ_t,del); % normalized density on every day
%     ER_P   = fP_i*R_vec*del;
%     var_P  = fP_i*R_vec.^2*del-ER_P.^2;
%     ER_Q   = fQ*R_vec*del;
%     var_Q  = fQ*R_vec.^2*del-ER_Q.^2;
%     disp(10000*mean(var_P-var_Q))
% end