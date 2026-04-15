



%% Plot BP overall
shadow_x_negative = [-0.6, -0.2];
shadow_x_positive = [0.2, 0.6];

BP = BP_overall;
Q_density = fQ_overall;
P_density = fP_overall;
PK = Q_density ./ P_density;

BP_sub1 = BP(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
BP_sub2 = BP(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
ret_sub1 = R_vec(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
ret_sub2 = R_vec(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
P_density_sub1 = P_density(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
P_density_sub2 = P_density(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
Q_density_sub1 = Q_density(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
Q_density_sub2 = Q_density(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
P_integral_sub1 = trapz(ret_sub1, P_density_sub1);
P_integral_sub2 = trapz(ret_sub2, P_density_sub2);
Q_integral_sub1 = trapz(ret_sub1, Q_density_sub1);
Q_integral_sub2 = trapz(ret_sub2, Q_density_sub2);

PK_sub1 = PK(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
PK_sub2 = PK(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
PK_integral_sub1 = abs(trapz(ret_sub1, PK_sub1));
PK_integral_sub2 = abs(trapz(ret_sub2, PK_sub2));
PK_average_sub1 = PK_integral_sub1 / (shadow_x_negative(2)-shadow_x_negative(1));
PK_average_sub2 = PK_integral_sub2 / (shadow_x_positive(2)-shadow_x_positive(1));

OA = [BP_sub1(end)-BP_sub1(1), P_integral_sub1, Q_integral_sub1/P_integral_sub1,...
    BP_sub2(end)-BP_sub2(1), P_integral_sub2, Q_integral_sub2/P_integral_sub2];

OA1 = [BP_sub1(end)-BP_sub1(1), P_integral_sub1, Q_integral_sub1, Q_integral_sub1/P_integral_sub1,...
    BP_sub2(end)-BP_sub2(1), P_integral_sub2, Q_integral_sub2, Q_integral_sub2/P_integral_sub2];

OA2 = [BP_sub1(end)-BP_sub1(1), PK_integral_sub1,PK_average_sub1,...
    BP_sub2(end)-BP_sub2(1), PK_integral_sub2,PK_average_sub2];

PKlog_sub1 = log(PK_sub1);
PKlog_sub2 = log(PK_sub2);

AKA_sub1 = -gradient(PKlog_sub1, ret_sub1);
AKA_sub2 = -gradient(PKlog_sub2, ret_sub2);
disp([mean(AKA_sub1),mean(AKA_sub2)])

%% Plot BP for 2 HV cluster 
shadow_x_negative = [-0.6, -0.2];
shadow_x_positive = [0.2, 0.6];

BP = BP_HV;
Q_density = fQ_HV;
P_density = fQ_LV;
PK = Q_density ./ P_density;

BP_sub1 = BP(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
BP_sub2 = BP(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
ret_sub1 = R_vec(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
ret_sub2 = R_vec(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
P_density_sub1 = P_density(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
P_density_sub2 = P_density(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
Q_density_sub1 = Q_density(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
Q_density_sub2 = Q_density(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
P_integral_sub1 = trapz(ret_sub1, P_density_sub1);
P_integral_sub2 = trapz(ret_sub2, P_density_sub2);
Q_integral_sub1 = trapz(ret_sub1, Q_density_sub1);
Q_integral_sub2 = trapz(ret_sub2, Q_density_sub2);

PK_sub1 = PK(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
PK_sub2 = PK(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
% PK_integral_sub1 = abs(trapz(ret_sub1, log(PK_sub1)));
% PK_integral_sub2 = abs(trapz(ret_sub2, log(PK_sub2)));
PK_integral_sub1 = abs(trapz(ret_sub1, PK_sub1));
PK_integral_sub2 = abs(trapz(ret_sub2, PK_sub2));
PK_average_sub1 = PK_integral_sub1 / (shadow_x_negative(2)-shadow_x_negative(1));
PK_average_sub2 = PK_integral_sub2 / (shadow_x_positive(2)-shadow_x_positive(1));

HV = [BP_sub1(end)-BP_sub1(1), P_integral_sub1, Q_integral_sub1/P_integral_sub1,...
    BP_sub2(end)-BP_sub2(1), P_integral_sub2, Q_integral_sub2/P_integral_sub2];

HV1 = [BP_sub1(end)-BP_sub1(1), P_integral_sub1, Q_integral_sub1, Q_integral_sub1/P_integral_sub1,...
    BP_sub2(end)-BP_sub2(1), P_integral_sub2, Q_integral_sub2, Q_integral_sub2/P_integral_sub2];

HV2 = [BP_sub1(end)-BP_sub1(1), PK_integral_sub1,PK_average_sub1,...
    BP_sub2(end)-BP_sub2(1), PK_integral_sub2,PK_average_sub2];

PKlog_sub1 = log(PK_sub1);
PKlog_sub2 = log(PK_sub2);

AKA_sub1 = -gradient(PKlog_sub1, ret_sub1);
AKA_sub2 = -gradient(PKlog_sub2, ret_sub2);
disp([mean(AKA_sub1),mean(AKA_sub2)])

%% Plot BP for 2 LV cluster
shadow_x_negative = [-0.6, -0.2];
shadow_x_positive = [0.2, 0.6];

BP = BP_LV;
Q_density = fQ_LV;
P_density = fP_LV;
PK = Q_density ./ P_density;

BP_sub1 = BP(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
BP_sub2 = BP(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
ret_sub1 = R_vec(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
ret_sub2 = R_vec(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
P_density_sub1 = P_density(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
P_density_sub2 = P_density(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
Q_density_sub1 = Q_density(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
Q_density_sub2 = Q_density(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
P_integral_sub1 = trapz(ret_sub1, P_density_sub1);
P_integral_sub2 = trapz(ret_sub2, P_density_sub2);
Q_integral_sub1 = trapz(ret_sub1, Q_density_sub1);
Q_integral_sub2 = trapz(ret_sub2, Q_density_sub2);

PK_sub1 = PK(R_vec>=shadow_x_negative(1) & R_vec<=shadow_x_negative(2));
PK_sub2 = PK(R_vec>=shadow_x_positive(1) & R_vec<=shadow_x_positive(2));
PK_integral_sub1 = abs(trapz(ret_sub1, PK_sub1));
PK_integral_sub2 = abs(trapz(ret_sub2, PK_sub2));
PK_average_sub1 = PK_integral_sub1 / (shadow_x_negative(2)-shadow_x_negative(1));
PK_average_sub2 = PK_integral_sub2 / (shadow_x_positive(2)-shadow_x_positive(1));

LV = [BP_sub1(end)-BP_sub1(1), P_integral_sub1, Q_integral_sub1/P_integral_sub1,...
    BP_sub2(end)-BP_sub2(1), P_integral_sub2, Q_integral_sub2/P_integral_sub2];

LV1 = [BP_sub1(end)-BP_sub1(1), P_integral_sub1, Q_integral_sub1, Q_integral_sub1/P_integral_sub1,...
    BP_sub2(end)-BP_sub2(1), P_integral_sub2, Q_integral_sub2, Q_integral_sub2/P_integral_sub2];

LV2 = [BP_sub1(end)-BP_sub1(1), PK_integral_sub1,PK_average_sub1,...
    BP_sub2(end)-BP_sub2(1), PK_integral_sub2,PK_average_sub2];

PKlog_sub1 = log(PK_sub1);
PKlog_sub2 = log(PK_sub2);

AKA_sub1 = -gradient(PKlog_sub1, ret_sub1);
AKA_sub2 = -gradient(PKlog_sub2, ret_sub2);
disp([mean(AKA_sub1),mean(AKA_sub2)])

%% Report
Influential_return_state_table = [OA;HV;LV];
info.rnames = strvcat('.','OA','HV','LV');
info.cnames = strvcat('BP(-0.2)-BP(-0.6)','int_-0.6^-0.2p','q/p','BP(0.6)-BP(0.2)','int_0.2^0.6p','q/p');
info.fmt    = '%10.3f';
disp('Influential return state table')
mprint(Influential_return_state_table,info)