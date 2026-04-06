function [logLik_all,theta_all] = estimate_poly(N,ln_fQ,r30,sig_t,r_vec,ln_fQ_t,del,K_max,theta_0_mat)

if ~exist('K_max','var')
    K_max = 6;
end

r_vec_pow  = r_vec.^(1:N);
r30_pow    = r30.^(1:N);

logLik_all = NaN(K_max,1);
theta_all  = NaN(K_max,N*(K_max+1));
for K=1:K_max
    sig_t_pow = sig_t.^(0:K);
    if exist('theta_0_mat','var') && ~isempty(theta_0_mat)  %NOTE: 'theta_0_mat' contains a starting value for each K. multiple starting value for a given K not implemented
        theta_0 = theta_0_mat(K,1:(K+1)*N);
    else
        if K==1
           theta_0 = ones(1,N*(K+1))*0.00001;
        else
           theta_0 = [reshape(theta_opt,[K,N]);ones(1,N)*0.00001];
           theta_0 = theta_0(:);
        end
    end
    theta_opt              = fmincon(@(x)LL_poly(x,N,ln_fQ,r30,sig_t,r_vec,ln_fQ_t,del,K,r_vec_pow,r30_pow,sig_t_pow),theta_0,[],[],[],[],[],[],[],optimoptions('fmincon','SpecifyObjectiveGradient',true,'display','off','TolX',1e-14,'TolFun',1e-20,'MaxFunctionEvaluations',100000));
    [~,~,logLik_all(K)]    = LL_poly(theta_opt,N,ln_fQ,r30,sig_t,r_vec,ln_fQ_t,del,K,r_vec_pow,r30_pow,sig_t_pow);
    theta_all(K,1:N*(K+1)) = theta_opt;
    
    %try to move away from previous values
    if K>1
        theta_0 = theta_0/2;
        theta_opt_2       = fmincon(@(x)LL_poly(x,N,ln_fQ,r30,sig_t,r_vec,ln_fQ_t,del,K,r_vec_pow,r30_pow,sig_t_pow),theta_0,[],[],[],[],[],[],[],optimoptions('fmincon','SpecifyObjectiveGradient',true,'display','off','TolX',1e-14,'TolFun',1e-20,'MaxFunctionEvaluations',100000));
        [~,~,logLik_2]    = LL_poly(theta_opt_2,N,ln_fQ,r30,sig_t,r_vec,ln_fQ_t,del,K,r_vec_pow,r30_pow,sig_t_pow);
        if logLik_2>logLik_all(K)
            theta_all(K,1:N*(K+1)) = theta_opt_2;
            logLik_all(K) = logLik_2;
        end
    end
    
    %try to start from no prior values
    if K>1
        theta_0 = repmat(1000.^-(1:K+1) , 1, N);
        theta_opt_2       = fmincon(@(x)LL_poly(x,N,ln_fQ,r30,sig_t,r_vec,ln_fQ_t,del,K,r_vec_pow,r30_pow,sig_t_pow),theta_0,[],[],[],[],[],[],[],optimoptions('fmincon','SpecifyObjectiveGradient',true,'display','off','TolX',1e-14,'TolFun',1e-20,'MaxFunctionEvaluations',100000));
        [~,~,logLik_2]    = LL_poly(theta_opt_2,N,ln_fQ,r30,sig_t,r_vec,ln_fQ_t,del,K,r_vec_pow,r30_pow,sig_t_pow);
        if logLik_2>logLik_all(K)
            theta_all(K,1:N*(K+1)) = theta_opt_2;
            logLik_all(K) = logLik_2;
        end
    end
end


