function [logLik,fP_30] = LL_nig(theta,R30,eval_vec)
 
alp = theta(1);
bet = theta(2);
mu  = theta(3);
del = theta(4);

if del<=0 || abs(bet)>alp
   logLik = -1e6;
else
   logLik = mean(log(NIG_pdf(R30,alp,bet,mu,del)));
end
     
if nargout>1
   fP_30 = NaN(length(R30),size(eval_vec,2));
   for t=1:length(R30)
       fP_30(t,:) = NIG_pdf(eval_vec(t,:),alp,bet,mu,del);
   end
end
logLik = gather(logLik);
end