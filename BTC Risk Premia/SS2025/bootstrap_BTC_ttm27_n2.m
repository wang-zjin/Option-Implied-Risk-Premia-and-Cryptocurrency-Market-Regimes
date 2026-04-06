function [theta_0,theta_b0_0,LL_0,theta_boot,theta_b0_boot,LL_boot,fig1,tab4,tab5,tab6] = bootstrap_BTC(reps,T,block,N,ln_fQ_t,ln_sig_t,ln_fQ,r30,r_vec,del,lnRf,do_estimate,do_fig1,do_tab4,do_tab5,do_tab6)

% N: the order of polynomial

% prep
numblock    = ceil(T/block);
load data_outputs/rand_U rand_U % No need to modify the random set
rand_U      = rand_U(1:numblock,1:reps);
if isgpuarray(ln_fQ)
   rand_U         = gpuArray(rand_U);
   N              = gpuArray(N);
   T              = gpuArray(T);
   block          = gpuArray(block);
   LL_boot        = gpuArray.NaN(reps,length(N));
   theta_boot     = gpuArray.NaN(reps,length(N),max(N)+1);
   theta_b0_boot  = gpuArray.NaN(reps,3);
   M10_boot       = gpuArray.NaN(reps,size(ln_fQ,2));
   M90_boot       = gpuArray.NaN(reps,size(ln_fQ,2));
   RRTO_R_boot    = gpuArray.NaN(reps,length(N)+1,1);
   RRTO_ER_boot   = gpuArray.NaN(reps,length(N)+1,1);
   RRTO_ER2_boot  = gpuArray.NaN(reps,length(N)+1,2);
   RRTO_ER3_boot  = gpuArray.NaN(reps,length(N)+1,3);
   VP_R_OLS_boot  = gpuArray.NaN(reps,length(N)+1,1);
   VP_R_WLS_boot  = gpuArray.NaN(reps,length(N)+1,1);
   VP_ER_boot     = gpuArray.NaN(reps,length(N)+1,1);
   VP2_ER_boot    = gpuArray.NaN(reps,length(N)+1,2);
   momQ_boot      = gpuArray.NaN(reps,length(N)+1,1);
   momP_boot      = gpuArray.NaN(reps,length(N)+1,1);
   momPQ_boot     = gpuArray.NaN(reps,length(N)+1,1);
else
   LL_boot        = NaN(reps,length(N));
   theta_boot     = NaN(reps,length(N),max(N)+1);
   theta_b0_boot  = NaN(reps,3);
   M10_boot       = NaN(reps,size(ln_fQ,2));
   M90_boot       = NaN(reps,size(ln_fQ,2));   
   RRTO_R_boot    = NaN(reps,length(N)+1,1);
   RRTO_ER_boot   = NaN(reps,length(N)+1,1);
   RRTO_ER2_boot  = NaN(reps,length(N)+1,2);
   RRTO_ER3_boot  = NaN(reps,length(N)+1,3);
   VP_R_OLS_boot  = NaN(reps,length(N)+1,1);
   VP_R_WLS_boot  = NaN(reps,length(N)+1,1);
   VP_ER_boot     = NaN(reps,length(N)+1,1);
   VP2_ER_boot    = NaN(reps,length(N)+1,2);   
   momQ_boot      = NaN(reps,length(N)+1,1);
   momP_boot      = NaN(reps,length(N)+1,1);
   momPQ_boot     = NaN(reps,length(N)+1,1);
end


% estimate in original sample to get starting values for bootstrap samples
LL_0                 = NaN(length(N),1);
theta_0              = NaN(length(N),max(N)+1);
for i=1:length(N)
    if N(i)<=2      % For order <=2, set starting value
       start_val = [ 1.001,-ones(1,N(i))*0.001;
                     1.001, ones(1,N(i))*0.001;
                    -1.001,-ones(1,N(i))*0.001;
                    -1.001, ones(1,N(i))*0.001]; 
    else            % For order >2, no need to set another starting value, just follow the lower order's staring value
       start_val = [theta_0(i-1,1:N(i)), 1e-5;
                    theta_0(i-1,1:N(i)),-1e-5];
    end
    if N(i)==2 
       [temp1,temp2] = estimate_bench(N(i),ln_fQ,r30,ln_sig_t,r_vec,ln_fQ_t,del,0,start_val);
       LL_0(i) = temp1(1);
       theta_0(i,1:N(i)+1) = temp2(1,:);
       theta_b0_0 = temp2(2,:);
    else
       [LL_0(i),theta_0(i,1:N(i)+1)] = estimate_bench(N(i),ln_fQ,r30,ln_sig_t,r_vec,ln_fQ_t,del,[],start_val);
    end
end


% bootstrap
if ~do_estimate
   load data_outputs/bootstrap_estimates_BTC theta_boot theta_b0_boot LL_boot 
   if isgpuarray(ln_fQ)
      theta_boot = gpuArray(theta_boot);
      theta_b0_boot = gpuArray(theta_b0_boot);
      LL_boot = gpuArray(LL_boot);
   end
end

for b=1:reps
    tic

    % generate sample
    obs_b      = round(rand_U(:,b)*(T-block+1)-0.5) + (1:block);
    obs_b      = obs_b(:);
    ln_fQ_b    = ln_fQ(obs_b,:);
    fQ_b       = exp(ln_fQ_b);
    r30_b      = r30(obs_b);
    r30_b      = exp(r30_b);
    ln_sig_t_b = ln_sig_t(obs_b);
    ln_fQ_t_b  = ln_fQ_t(obs_b);
   
    % estimation
    if do_estimate
       logLik_boot_b = NaN(1,length(N));
       theta_boot_b  = NaN(length(N),max(N)+1);
       for i=1:length(N)

           caught = false;
           try
              if N(i)==2
                 [temp1,temp2] = estimate_bench(N(i),ln_fQ_b,r30_b,ln_sig_t_b,r_vec,ln_fQ_t_b,del,0,theta_0(i,1:N(i)+1)); % estimator from original (non-bootstrapped) sample
                 theta_b0 = temp2(2,:); % estimate with restriction b=0
                 theta_b  = temp2(1,:);
                 LL_b     = temp1(1);
              else
                 [LL_b,theta_b] = estimate_bench(N(i),ln_fQ_b,r30_b,ln_sig_t_b,r_vec,ln_fQ_t_b,del,[],theta_0(i,1:N(i)+1)); % estimator from original (non-bootstrapped) sample
              end
           catch
              if N(i)==2
                 [temp1,temp2] = estimate_bench(N(i),ln_fQ_b,r30_b,ln_sig_t_b,r_vec,ln_fQ_t_b,del,0); % set of fixed starting values in estimation function
                 theta_b0 = temp2(2,:); % estimate with restriction b=0
                 theta_b  = temp2(1,:); 
                 LL_b     = temp1(1);
              else
                 [LL_b,theta_b] = estimate_bench(N(i),ln_fQ_b,r30_b,ln_sig_t_b,r_vec,ln_fQ_t_b,del,[]); % set of fixed starting values in estimation function
              end
              caught = true;
           end


           if ~caught & all(  abs(theta_b./theta_0(i,1:N(i)+1)-1)<0.01  |  abs(theta_b)<1e-4  ) % if estimator got stuck on parameter values from original sample
              try

                 if N(i)==2
                    [LL_2,theta_2] = estimate_bench(N(i),ln_fQ_b,r30_b,ln_sig_t_b,r_vec,ln_fQ_t_b,del,0);
                    if LL_2>LL_b
                       theta_b0 = theta_2(2,:); % estimate with restriction b=0
                       theta_b  = theta_2(1,:);
                       LL_b     = LL_2(1);
                    end
                 else
                    [LL_2,theta_2] = estimate_bench(N(i),ln_fQ_b,r30_b,ln_sig_t_b,r_vec,ln_fQ_t_b,del,[]);
                    if LL_2>LL_b
                       LL_b = LL_2;
                       theta_b = theta_2;
                    end
                 end
              catch
              end
           end



           % for N=5, run estimation with additional starting values
           if N(i)==5
              try
                [LL_2,theta_2] = estimate_bench(N(i),ln_fQ_b,r30_b,ln_sig_t_b,r_vec,ln_fQ_t_b,del,[],[theta_boot_b(i-1,1:N(i)), 1e-8]); % (N-1) bootstrapped parameter estimates
                if LL_2>LL_b
                   LL_b = LL_2;
                   theta_b = theta_2;
                end
                [LL_2,theta_2] = estimate_bench(N(i),ln_fQ_b,r30_b,ln_sig_t_b,r_vec,ln_fQ_t_b,del,[],[theta_boot_b(i-1,1:N(i)),-1e-8]); % (N-1) bootstrapped parameter estimates
                if LL_2>LL_b
                   LL_b = LL_2;
                   theta_b = theta_2;
                end
                [LL_2,theta_2] = estimate_bench(N(i),ln_fQ_b,r30_b,ln_sig_t_b,r_vec,ln_fQ_t_b,del,[],[theta_0(i-1,1:N(i)), 1e-8]); % (N-1) original parameter estimates
                if LL_2>LL_b
                   LL_b = LL_2;
                   theta_b = theta_2;
                end
                [LL_2,theta_2] = estimate_bench(N(i),ln_fQ_b,r30_b,ln_sig_t_b,r_vec,ln_fQ_t_b,del,[],[theta_0(i-1,1:N(i)),-1e-8]); % (N-1) original parameter estimates
                if LL_2>LL_b
                   LL_b = LL_2;
                   theta_b = theta_2;
                end
              catch
              end
           end


           logLik_boot_b(i)         = LL_b;
           theta_boot_b(i,1:N(i)+1) = theta_b;
       end
       LL_boot(b,:)         = logLik_boot_b;
       theta_boot(b,:,:)    = theta_boot_b;
       theta_b0_boot(b,:,:) = theta_b0;

    end


    % figure 1 : E[M|R] 
    if do_fig1
       if N(2)~=2 
          disp('Figure 1 objects can only be computed for N=2'); return;
       else
       theta_b        = reshape(theta_boot(b,2,1:3),[3,1]);
       lnRf_b         = lnRf(obs_b);
       [~,~,~,~,fP_b] = LL(theta_b,N(2),ln_fQ_b,r30_b,ln_sig_t_b,r_vec,ln_fQ_t_b,del); % normalized density on every day
       mR             = ln_fQ_b-lnRf_b-log(fP_b);  
       [ ~, i10 ]     = min( abs( ln_sig_t_b-prctile(ln_sig_t_b,10) ));
       [ ~, i90 ]     = min( abs( ln_sig_t_b-prctile(ln_sig_t_b,90) ));        
       M10_boot(b,:)  = exp(mR(i10,:));
       M90_boot(b,:)  = exp(mR(i90,:));   
       end
    end

    % table 4 : RRTO regressions
    if do_tab4
       RRTO_R_boot_b   = NaN(length(N)+1,1);
       RRTO_ER_boot_b  = NaN(length(N)+1,1);
       RRTO_ER2_boot_b = NaN(length(N)+1,2);
       RRTO_ER3_boot_b = NaN(length(N)+1,3);
       for i=1:length(N)+1
           if i<=length(N)
              theta_b           = reshape(theta_boot(b,i,1:N(i)+1),[N(i)+1,1]);
              [~,~,~,~,fP_b]    = LL(theta_b,N(i),ln_fQ_b,r30_b,ln_sig_t_b,r_vec,ln_fQ_t_b,del); % normalized density on every day
           else
              theta_b           = reshape(theta_b0_boot(b,:),[3,1]);
              [~,~,~,~,fP_b]    = LL(theta_b,2,ln_fQ_b,r30_b,ln_sig_t_b,r_vec,ln_fQ_t_b,del); % normalized density on every day
           end
           ER_P                 = fP_b*exp(r_vec)*del;
           ER_Q                 = fQ_b*exp(r_vec)*del;
           R0                   = exp(r_vec)'-ER_P;
           var_P                = sum(fP_b.*R0.^2,2)*del;
           vol_P                = sqrt(var_P);
           skew_P               = sum(fP_b.*(R0./vol_P).^3,2)*del;
           kurt_P               = sum(fP_b.*(R0./vol_P).^4,2)*del;
           std_P                = 100*sqrt(12*var_P);
           Y1                   = 1200*(r30_b-ER_Q);
           Y2                   = 1200*(ER_P -ER_Q);
           X                    = [ones(size(ER_P,1),1),(vol_P-mean(vol_P))./std(vol_P)];
           bb                   = OLS(Y1./std_P,X./std_P,0,0,0);
           RRTO_R_boot_b(i)     = bb(2);
           bb                   = OLS(Y2,X,0,0,0);
           RRTO_ER_boot_b(i)    = bb(2);
           X                    = [ones(size(ER_P,1),1),(vol_P-mean(vol_P))./std(vol_P),(skew_P-mean(skew_P))./std(skew_P)];
           bb                   = OLS(Y2,X,0,0,0);
           RRTO_ER2_boot_b(i,:) = bb(2:3);
           X                    = [ones(size(ER_P,1),1),(vol_P-mean(vol_P))./std(vol_P),(skew_P-mean(skew_P))./std(skew_P),(kurt_P-mean(kurt_P))./std(kurt_P)];
           bb                   = OLS(Y2,X,0,0,0);
           RRTO_ER3_boot_b(i,:) = bb(2:4);
       end
       RRTO_R_boot(b,:,:)   = RRTO_R_boot_b;
       RRTO_ER_boot(b,:,:)  = RRTO_ER_boot_b;
       RRTO_ER2_boot(b,:,:) = RRTO_ER2_boot_b;
       RRTO_ER3_boot(b,:,:) = RRTO_ER3_boot_b;
    end

    % table 5 : VRP regressions
    if do_tab5
       VP_R_OLS_boot_b = NaN(length(N)+1,1);
       VP_R_WLS_boot_b = NaN(length(N)+1,1);
       VP_ER_boot_b    = NaN(length(N)+1,1);
       VP2_ER_boot_b   = NaN(length(N)+1,2);
       for i=1:length(N)+1
           if i<=length(N)
              theta_b           = reshape(theta_boot(b,i,1:N(i)+1),[N(i)+1,1]);
              [~,~,~,~,fP_b]    = LL(theta_b,N(i),ln_fQ_b,r30_b,ln_sig_t_b,r_vec,ln_fQ_t_b,del); % normalized density on every day
           else
              theta_b           = reshape(theta_b0_boot(b,:),[3,1]);
              [~,~,~,~,fP_b]    = LL(theta_b,2,ln_fQ_b,r30_b,ln_sig_t_b,r_vec,ln_fQ_t_b,del); % normalized density on every day
           end
           ER_P                 = fP_b*exp(r_vec)*del;
           ER_Q                 = fQ_b*exp(r_vec)*del;
           var_P                = sum(fP_b.*(exp(r_vec)'-ER_P).^2,2)*del;
           var_Q                = sum(fQ_b.*(exp(r_vec)'-ER_Q).^2,2)*del;
           vol_P                = sqrt(var_P);
           std_P                = 100*sqrt(12*var_P); 
           VP                   = var_P-var_Q;
           Y1                   = 1200*(r30_b-ER_Q);
           Y2                   = 1200*(ER_P -ER_Q);
           X                    = [ones(size(ER_P,1),1),(VP-mean(VP))./std(VP)];
           bb                   = OLS(Y1,X,0,0,0);
           VP_R_OLS_boot_b(i,1) = bb(2);
           bb                   = OLS(Y1./std_P,X./std_P,0,0,0);
           VP_R_WLS_boot_b(i,1) = bb(2);
           bb                   = OLS(Y2,X,0,0,0);
           VP_ER_boot_b(i,1)    = bb(2);
           X                    = [ones(size(ER_P,1),1),(VP-mean(VP))./std(VP),(vol_P-mean(vol_P))./std(vol_P)];
           bb                   = OLS(Y2,X,0,0,0);
           VP2_ER_boot_b(i,:)   = bb(2:3);
       end
       VP_R_OLS_boot(b,:,:) = VP_R_OLS_boot_b;
       VP_R_WLS_boot(b,:,:) = VP_R_WLS_boot_b;
       VP_ER_boot(b,:,:)    = VP_ER_boot_b;
       VP2_ER_boot(b,:,:)   = VP2_ER_boot_b;
    end


    % table 6 : higher moments
    if do_tab6
       momQ_boot_b  = NaN(length(N)+1,1);
       momP_boot_b  = NaN(length(N)+1,1);
       momPQ_boot_b = NaN(length(N)+1,1);
       for i=1:length(N)+1
           if i<=length(N)
              theta_b           = reshape(theta_boot(b,i,1:N(i)+1),[N(i)+1,1]);
              [~,~,~,~,fP_b]    = LL(theta_b,N(i),ln_fQ_b,r30_b,ln_sig_t_b,r_vec,ln_fQ_t_b,del); % normalized density on every day
           else
              theta_b           = reshape(theta_b0_boot(b,:),[3,1]);
              [~,~,~,~,fP_b]    = LL(theta_b,2,ln_fQ_b,r30_b,ln_sig_t_b,r_vec,ln_fQ_t_b,del); % normalized density on every day
           end
           if ~do_tab4 % objects not computed yet
              ER_P              = fP_b*exp(r_vec)*del;
              var_P             = sum(fP_b.*(exp(r_vec)'-ER_P).^2,2)*del;
              vol_P             = sqrt(var_P);
              skew_P            = sum(fP_b.*((exp(r_vec)'-ER_P)./vol_P).^3,2)*del;
           end
           if ~do_tab5 % objects not computed yet
              ER_Q              = fQ_b*exp(r_vec)*del;
              var_Q             = sum(fQ_b.*(exp(r_vec)'-ER_Q).^2,2)*del;
           end
           vol_Q                = sqrt(var_Q);
           skew_Q               = sum(fQ_b.*((exp(r_vec)'-ER_Q)./vol_Q).^3,2)*del;
           X                    = [ones(size(ER_P,1),1),1200*var_Q];
           bb                   = OLS(skew_Q,X,0,0,0);
           momQ_boot_b(i)       = bb(2);
           X                    = [ones(size(ER_P,1),1),1200*var_P];
           bb                   = OLS(skew_P,X,0,0,0);
           momP_boot_b(i)       = bb(2);
           X                    = [ones(size(ER_P,1),1),1200*(var_P-var_Q)];
           bb                   = OLS(skew_P-skew_Q,X,0,0,0);
           momPQ_boot_b(i)      = bb(2);
       end
       momQ_boot(b,:) = momQ_boot_b;
       momP_boot(b,:) = momP_boot_b;
       momPQ_boot(b,:) = momPQ_boot_b;
    end

    fprintf('iteration %4.0f: %6.2f seconds\n',b,toc);
end

% pack up return arguments
if isgpuarray(ln_fQ)
   LL_boot    = gather(LL_boot);
   theta_boot = gather(theta_boot);
   if do_fig1
      fig1.M10_p05 = gather(prctile(M10_boot,5,1));
      fig1.M10_p95 = gather(prctile(M10_boot,95,1));
      fig1.M90_p05 = gather(prctile(M90_boot,5,1));
      fig1.M90_p95 = gather(prctile(M90_boot,95,1));
   else
      fig1 = NaN;
   end
   if do_tab4
      tab4.RRTO_R_boot   = gather(RRTO_R_boot);
      tab4.RRTO_ER_boot  = gather(RRTO_ER_boot);
      tab4.RRTO_ER2_boot = gather(RRTO_ER2_boot);
      tab4.RRTO_ER3_boot = gather(RRTO_ER3_boot);
   else
      tab4 = NaN;
   end
   if do_tab5
      tab5.VP_R_OLS_boot = gather(VP_R_OLS_boot);
      tab5.VP_R_WLS_boot = gather(VP_R_WLS_boot);
      tab5.VP_ER_boot    = gather(VP_ER_boot);
      tab5.VP2_ER_boot   = gather(VP2_ER_boot);
   else
      tab5 = NaN;
   end
   if do_tab6
      tab6.momQ_boot  = gather(momQ_boot);
      tab6.momP_boot  = gather(momP_boot);
      tab6.momPQ_boot = gather(momPQ_boot);
   else
      tab6 = NaN;
   end
else
   if do_fig1
      fig1.M10_p05 = prctile(M10_boot,5,1);
      fig1.M10_p95 = prctile(M10_boot,95,1);
      fig1.M90_p05 = prctile(M90_boot,5,1);
      fig1.M90_p95 = prctile(M90_boot,95,1);
   else
      fig1 = NaN;
   end
   if do_tab4
      tab4.RRTO_R_boot   = RRTO_R_boot;
      tab4.RRTO_ER_boot  = RRTO_ER_boot;
      tab4.RRTO_ER2_boot = RRTO_ER2_boot;
      tab4.RRTO_ER3_boot = RRTO_ER3_boot;
   else
      tab4 = NaN;
   end
   if do_tab5
      tab5.VP_R_OLS_boot = VP_R_OLS_boot;
      tab5.VP_R_WLS_boot = VP_R_WLS_boot;
      tab5.VP_ER_boot    = VP_ER_boot;
      tab5.VP2_ER_boot   = VP2_ER_boot;
   else
      tab5 = NaN;
   end  
   if do_tab6
      tab6.momQ_boot  = momQ_boot;
      tab6.momP_boot  = momP_boot;
      tab6.momPQ_boot = momPQ_boot;
   else
      tab6 = NaN;
   end
end

% if new estimates were obtained, save them
if do_estimate && all(N(:)'==[1 2]) % We use N=1;2 while the original SS2025JFE paper set N=1:5
   if isgpuarray(LL_boot)
      theta_boot = gather(theta_boot);
      theta_b0_boot = gather(theta_b0_boot);
      LL_boot = gather(LL_boot);       
   end
   save data_outputs/bootstrap_estimates_BTC theta_boot theta_b0_boot LL_boot theta_0 theta_b0_0 LL_0
end


            