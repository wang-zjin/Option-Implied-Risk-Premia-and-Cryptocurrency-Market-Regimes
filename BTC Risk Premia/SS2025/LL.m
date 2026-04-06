function [OBJ_FUN,gradient,logLik,mass,fP_norm,logLik_terms] = LL(theta,N,ln_fQ,r30,ln_sig_t,r_vec,ln_fQ_t,del,r_vec_pow,r30_pow)

% Check if theta and N match
if N ~= length(theta)-1
    error('N and the number of parameters does not match')
end

% the function runs faster when these objects are supplied externally
if ~exist('r30_pow','var')
    r30_pow   = r30.^(1:N);
    r_vec_pow = r_vec.^(1:N);
end

% polynomial coefficients
b        = theta(1);
theta    = reshape(theta(2:end),[1,length(theta)-1]);
if abs(b)<1e-12
   scale = ones(length(ln_sig_t),N);
else
   scale = exp(ln_sig_t.*(1:N)*b);
end
coef     = theta./scale;

% probability mass
fP_30     = exp(ln_fQ-coef*r_vec_pow'); 
  % the subtracted term is the log change-of-measure, up to delta_it
  % fQ integrates to one, so fQ/R_F cancels with the exp(-r_f) in M
mass      = sum(fP_30,2)*del; 
if nargout>4
   fP_norm = fP_30./mass;
end

% likelihood
lnM_realized = sum(r30_pow.*coef,2); % this is the log change-of-measure, up to delta_it
logLik_terms = ln_fQ_t-lnM_realized-log(mass);
logLik       = mean(logLik_terms);

% gradient
if nargout>1
   value1      = -r30_pow + del*(fP_30*r_vec_pow)./mass; 
   dp_dc       = value1./scale;
   gradient_LL = mean(dp_dc)';
   dp_dsigma   = - sum((1:N) .* mean( value1 .* coef .* ln_sig_t )); 
   gradient    = -[ dp_dsigma; gradient_LL ];  % Note: negative of the gradient
   gradient    = gather(gradient);
end

% objective function
OBJ_FUN = -gather(logLik);%Note: negative of the objective function

