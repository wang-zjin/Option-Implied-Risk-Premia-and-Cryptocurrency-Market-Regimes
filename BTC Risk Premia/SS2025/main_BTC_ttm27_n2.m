% =========================================================================
% Main
% =========================================================================
%
% This program accompanies Schreindorfer and Sichert (2025), "Conditional 
% Risk and the Pricing Kernel". See README for additional details. 
%
% Last modified: 4/2025
%
% Description: 
% --------------------
% This code performs the all the estimation and computation done in the
% main paper and produces all tables and figures.
% The code can be run in two settings: i) loading pre-computed results by 
% setting all "do\_XXX" dummies in lines 24ff. to false, or ii) performing 
% the estimation by setting the dummies to true.
% =========================================================================
  
clear; rng('default'); clc; close all; 
addpath utilities utilities/nig data_outputs
load data_BTC

% determine which parts of the code to run / load
do_estimate = false; % bootstrap estimates
do_fig1     = false;
do_tab4     = false;
do_tab5     = false;
do_tab6     = false;
do_fig4     = false;


% estimation + bootstrap
N           = 1:2; % polynomial orders
reps        = 10000; % # of bootstrap reps
block       = 26; % bootstrap block length
T           = length(r30);
[theta_0,theta_b0_0,LL_0,theta_boot,theta_b0_boot,LL_boot,fig1,tab4,tab5,tab6] = bootstrap_BTC(reps,T,block,N,ln_fQ_t,ln_sig_t,ln_fQ,r30,r_vec,del,lnRf,do_estimate,do_fig1,do_tab4,do_tab5,do_tab6);  
if do_fig1 & do_tab4 & do_tab5 & do_tab6 & reps==10000
   save data_outputs/bootstrap_results_BTC fig1 tab4 tab5 tab6
end
if ~do_fig1
   load data_outputs/bootstrap_results fig1 
end
if ~do_tab4
   load data_outputs/bootstrap_results tab4 
end
if ~do_tab5
   load data_outputs/bootstrap_results tab5 
end
if ~do_tab6
   load data_outputs/bootstrap_results tab6 
end


% produce tables and figures
figure_1_BTC

table_1_BTC

table_2_BTC

redo_our_table2_Corsi_RV

% figure_2
% 
% figure_3_BTC
% 
% table_3
% 
% figure_4
% 
% table_4
% 
% % Implications section
% figure_5
% 
% table_5
% 
% table_6
% 
% % Model section
% figure_6
% 
% figure_7
% 
% table_7
% 
% % Appendix
% figure_8
% 
% table_8
% 
% detection_of_ncc_violations