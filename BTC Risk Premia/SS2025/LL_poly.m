function [OBJ_FUN,gradient,logLik,mass,fP_norm,logLik_terms] = LL_poly(theta,N,ln_fQ,r30,sig_t,r_vec,ln_fQ_t,del,K,r_vec_pow,r30_pow,sig_t_pow)

% Check if theta and N match
if N ~= length(theta)/(K+1)
    error('N and the number of parameters does not match')
end

% the function runs faster when there objects are supplied externally:
if ~exist('r30_pow','var')
    r30_pow   = r30.^(1:N);
    r_vec_pow = r_vec.^(1:N);
    sig_t_pow = sig_t.^(0:K);
end

% M polynomial
coef         = sig_t_pow*reshape(theta,[K+1,N]);
lnM_realized = sum(r30_pow.*coef,2); % this is the log change-of-measure, up to delta_it


% probability mass
fP_30 = exp(ln_fQ-coef*r_vec_pow'); 
%Note: fQ integrates to one, so fQ/R_F cancels with the exp(-r_f) in M
mass  = sum(fP_30,2)*del; 
if nargout>4
   fP_norm = fP_30./mass;
end

% likelihood
logLik_terms = ln_fQ_t-lnM_realized-log(mass);
logLik       = mean(logLik_terms);

% gradient
if nargout>1
    gradient_LL = zeros(length(theta),1);
    for i=1:N
        dp_dc = (-r30_pow(:,i) + del*(fP_30*r_vec_pow(:,i))./mass).*sig_t_pow;       
        gradient_LL((i-1)*sum(K+1)+(1:K+1)) = mean(dp_dc); 
    end
    gradient = -gradient_LL;
    gradient =  gather(gradient);
end

% objective function
OBJ_FUN = -gather(logLik);
