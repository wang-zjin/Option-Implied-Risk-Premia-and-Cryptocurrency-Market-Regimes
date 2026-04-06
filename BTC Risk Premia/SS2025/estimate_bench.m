function [logLik_all,theta_all] = estimate_bench(N,ln_fQ,r30,ln_sig_t,r_vec,ln_fQ_t,del,b_vec,theta_0_mat)
if min(ln_sig_t)>=0 %LL function changed from level vol into ln(vol); this error just checks if old code was adjusted to new input
    error('volatility on wrong scale')
end
    
r_vec_pow  = r_vec.^(1:N);
r30_pow    = r30.^(1:N);

% % If b_vec is null, provide a set of grids
% if ~exist('b_vec','var') || isempty(b_vec)
%     b_coarse = linspace(0.7, 1.3, 13);          % croase grid
%     b_fine   = 1 + [-0.05 -0.02 -0.01 0 0.01 0.02 0.05];  % fine grid
%     b_extra  = [0.9 0.95 1.001 1.01 1.05 1.1];  % common safe points
%     b_vec    = unique([b_coarse, b_fine, b_extra]);  % duplicate
% end

nB         = length(b_vec); % number of restricted estimations
logLik_all = NaN(nB+1,1);
theta_all  = NaN(nB+1,N+1);

% estimation, b restricted
% [use fmincon, as it converges more reliably than fminunc]
for bb=1:nB
    theta_0                = ones(1,N)*0.00001;
    f0                     = LL_fixed_b([b_vec(bb);theta_0(:)], N, ln_fQ, r30, ln_sig_t, r_vec, ln_fQ_t, del, r_vec_pow, r30_pow);
    theta_opt              = fminunc(@(x)LL_fixed_b([b_vec(bb);x(:)],N,ln_fQ,r30,ln_sig_t,r_vec,ln_fQ_t,del,r_vec_pow,r30_pow),theta_0,optimoptions('fminunc','SpecifyObjectiveGradient',false,'display','off','TolX',1e-14,'TolFun',1e-20,'MaxFunctionEvaluations',5000));      
    %theta_opt              = fminunc(@(x)LL_fixed_b([b_vec(bb);x(:)],N,ln_fQ,r30,ln_sig_t,r_vec,ln_fQ_t,del,r_vec_pow,r30_pow),theta_0,optimoptions('fminunc','SpecifyObjectiveGradient',true,'display','off','TolX',1e-14,'TolFun',1e-20,'MaxFunctionEvaluations',5000));      
    [~,~,logLik_all(bb+1)] = LL_fixed_b([b_vec(bb);theta_opt(:)],N,ln_fQ,r30,ln_sig_t,r_vec,ln_fQ_t,del,r_vec_pow,r30_pow);
    theta_all(bb+1,:)      = [b_vec(bb),theta_opt(:)'];
end

% estimation, b unrestricted
% [try alternative starting values]
if ~exist('theta_0_mat','var')
if N==5
   theta_0_mat = [ 1.01   -0.1    0.01    0.01    0.01  -1e-6;
                   1.01   -0.1    0.01    0.01    0.01  -1e-8;
                   1.01   -0.1    0.01    0.01    0.01   1e-6;
                   1.01   -0.1    0.01    0.01    0.01   1e-8];
else
   % theta_0_mat = [ 1.001,-ones(1,N)*0.001;
   %                 1.001, ones(1,N)*0.001;
   %                -1.001,-ones(1,N)*0.001;
   %                -1.001, ones(1,N)*0.001]; 
   theta_0_mat = [ 1.001,-ones(1,N)*0.001;
                   1.001, ones(1,N)*0.001;
                   1.501,-ones(1,N)*0.001;
                   1.501, ones(1,N)*0.001;
                  -1.001,-ones(1,N)*0.001;
                  -1.001, ones(1,N)*0.001]; 
end
end
OBJ = 1e6;
for i=1:size(theta_0_mat,1)
    try
        theta_0         = theta_0_mat(i,:);
        
        % Pre-examine: object function has value at the initial point? Gradient dimension matches?
        % [f0, g0] = LL(theta_0, N, ln_fQ, r30, ln_sig_t, r_vec, ln_fQ_t, del, r_vec_pow, r30_pow);
        % assert(isfinite(f0) && isreal(f0), 'LL at theta_0 not finite/real');
        % assert(isvector(g0) && numel(g0) == numel(theta_0), 'Gradient size mismatch');
        % g0 = g0(:);  % 强制列向量
        % assert(all(isfinite(g0)) && isreal(g0), 'Gradient contains NaN/Inf');
    
        opts_numgrad = optimoptions('fminunc', ...
            'SpecifyObjectiveGradient', false, ...
            'Algorithm', 'quasi-newton', ...
            'Display', 'off', ...
            'MaxFunctionEvaluations',5000, ...
            'StepTolerance',1e-12,'FunctionTolerance',1e-10);
        [theta_1, OBJ_1] = fminunc(@(x) LL(x, N, ln_fQ, r30, ln_sig_t, r_vec, ln_fQ_t, del, r_vec_pow, r30_pow), ...
            theta_0, opts_numgrad);
    
        %[theta_1,OBJ_1] = fminunc(@(x)LL(x,N,ln_fQ,r30,ln_sig_t,r_vec,ln_fQ_t,del,r_vec_pow,r30_pow),theta_0,optimoptions('fminunc','SpecifyObjectiveGradient',true,'display','off','TolX',1e-14,'TolFun',1e-20,'MaxFunctionEvaluations',5000));
        if OBJ_1<OBJ
           theta_opt = theta_1;
           OBJ = OBJ_1;
        end
    catch ME
        fprintf('\n[fminunc failed at start #%d]\n', i);
        fprintf('theta_0 = '); disp(theta_0);
        fprintf('%s\n', getReport(ME, 'extended'));  % Print compact 堆栈
        % rethrow(ME);  % Direct throw real error
    end
end

% try starting values based on restricted estimation, if available
if any(b_vec==1)
   ix = find(b_vec==1);
   theta_0         = [1.001,theta_all(1+ix,2:end)];
   [theta_1,OBJ_1] = fminunc(@(x)LL(x,N,ln_fQ,r30,ln_sig_t,r_vec,ln_fQ_t,del,r_vec_pow,r30_pow),theta_0,optimoptions('fminunc','SpecifyObjectiveGradient',true,'display','off','TolX',1e-14,'TolFun',1e-20,'MaxFunctionEvaluations',5000));
   if OBJ_1<OBJ
      theta_opt = theta_1;
      OBJ = OBJ_1;
   end
end
logLik_all(1) = -OBJ;
disp(theta_opt)
theta_all(1,:) = theta_opt;


