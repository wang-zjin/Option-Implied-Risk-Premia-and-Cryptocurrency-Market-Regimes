

% projected kernel estimate
[~,~,~,~,fP] = LL(theta_0(2,1:3),2,ln_fQ,r30,log(sig_t),r_vec,ln_fQ_t,del); % normalized density on every day
mR           = ln_fQ-lnRf-log(fP);


% SDF for low and high vol
[ ~, i10 ]  = min( abs( sig_t-prctile(sig_t,10) ));
[ ~, i90 ]  = min( abs( sig_t-prctile(sig_t,90) ));
M10         = exp(mR(i10,:));
M90         = exp(mR(i90,:));


ff = figure('Position', [100, 100, 595, 550]);
   set(ff,'Units','Inches');
   pos = get(ff,'Position');
   set(ff,'PaperPositionMode','Auto','PaperUnits','Inches','PaperSize',[pos(3), pos(4)]) 
subplot = @(m,n,p)subtightplot(m, n, p, [0.03 0.03], [0.12 0.015], [0.10 0.015]);
subplot(1,1,1)
hold on; box on;

c1=35;c2=201;

plot(100*R_vec(c1:c2),fig1.M10_p05(c1:c2),'-',100*R_vec(c1:c2),fig1.M10_p95(c1:c2),'-','Color',0.99*[.24 .69 .59]); 

%c1=350; c2=600; 

%plot(100*R_vec(c1:c2),fig1.M10_p05(c1:c2),'-',100*R_vec(c1:c2),fig1.M10_p95(c1:c2),'-','Color',0.99*[.24 .69 .59]); 
inBetween = [fig1.M10_p05(c1:c2), fliplr(fig1.M10_p95(c1:c2))]; x2 = [100*R_vec(c1:c2)', fliplr(100*R_vec(c1:c2)')]; ff=patch(x2,inBetween,0.8*[.24 .69 .59],'LineStyle','none'); alpha(0.1) 
l1=plot(100*R_vec(c1:c2),M10(1,c1:c2),'color',0.8*[.24 .69 .59],'LineWidth',1.8); 

plot(100*R_vec(c1:c2),fig1.M90_p05(c1:c2),'-',100*R_vec(c1:c2),fig1.M90_p95(c1:c2),'-','Color',0.7*ones(3,1)); 
inBetween = [fig1.M90_p05(c1:c2), fliplr(fig1.M90_p95(c1:c2))]; x2 = [100*R_vec(c1:c2)', fliplr(100*R_vec(c1:c2)')]; ff=patch(x2,inBetween,'k','LineStyle','none'); alpha(0.1) 
l2=plot(100*R_vec(c1:c2),M90(1,c1:c2),'k--','LineWidth',1.8); 

hold off;
grid on
axis([-60,100,0,10]); 
grid on; set(gca,'FontSize',14)
ylabel('$E_t[M_{t+1}|R_{t+1}]$','FontSize',18,'interpreter','latex')
xlabel('$R_{t+1}-1$: Monthly return, \%','FontSize',18,'interpreter','latex')
leg=legend([l1,l2],'Low BTC market volatility','High BTC market volatility','Location','NE','box','on','FontSize',15,'interpreter','latex'); 
yticks(0:2:10)
saveas(ff, 'figure_1_BTC.png')
%print(gcf,'figure_1','-dpdf','-r0')


