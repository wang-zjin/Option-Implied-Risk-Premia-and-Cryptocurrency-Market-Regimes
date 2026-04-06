
# This is the MAIN code for: 

# BTC lower bound (with regularization on preference parameters)
# Reference: Chabi-Yo & Loudis (2020), Martin (2017), Foley et al. (2022)
# 在估计 preference parameter (tau, rho, kappa) 时加入 L2 正则化，使估计出的参数绝对值不会过大

"""
There are three types of lower bound: 
- Martin's lower bound
- Preference-based lower bound (unrestricted) - from Chabi-Yo & Loudis (2020)
- Restricted lower bound - from Chabi-Yo & Loudis (2020)

Notice the preference-based lower bound, there are three parameters in the lower bound formula (27) associated with preference:
- tau
- rho
- kappa

We should estimate these parameters using moment restrictions.

R_M_t - R_f_t = alpha1 + LB1_t + epsilon1
(R_M_t - R_f_t)^2 - M2_t = alpha2 + UB2_t + epsilon2
(R_M_t - R_f_t)^3 - M3_t = alpha3 + LB3_t + epsilon3

"""

import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.optimize import minimize

base_dir = "/Users/irtg/Documents/同步空间/Pricing_Kernel/EPK/SVI_independent_tau/"
os.chdir(base_dir)

# 带正则化估计的结果输出目录
OUTPUT_DIR = "S10_4_upper_bound_regularization"

ttm = 27
Q_matrix_path = f"Q_matrix/Tau-independent/unique/moneyness_step_0d01/Q_matrix_{ttm}day.csv"
Q_matrix = pd.read_csv(Q_matrix_path)

def moments_Q_density(date_Q, Q_matrix, ttm=27, ret=np.arange(-1, 1.01, 0.01)):
    # date_Q: the date of Q
    # Q_matrix: the first column is the moneyness, the other columns are the dates of the Q densities

    # Read the Q_density of the date_Q
    Q_density = Q_matrix[date_Q]
    Q_density = Q_density.values

    # The return column of Q_matrix
    return_column = Q_matrix['Return']

    # Interpolate the Q-density to map returns we need
    Q_density_interpolated = np.interp(ret, return_column, Q_density, left=0, right=0)

    # Ensure Q-density has no negative values
    if np.any(Q_density_interpolated < 0):
        #print(f"Negative Q-density found for date {date_Q}")
        Q_density_interpolated[Q_density_interpolated < 0] = 0

    # M1: First moment (Mean)
    M1 = np.trapz(ret * Q_density_interpolated, ret) 

    # M2: Second moment (Variance)
    M2 = np.trapz((ret - M1) ** 2 * Q_density_interpolated, ret) 

    # M3: Third moment (Skewness)
    M3 = np.trapz((ret - M1) ** 3 * Q_density_interpolated, ret) #/ M2 ** 1.5

    # M4: Fourth moment (Kurtosis)
    M4 = np.trapz((ret - M1) ** 4 * Q_density_interpolated, ret) #/ M2 ** 2

    # M5: Fifth moment
    M5 = np.trapz((ret - M1) ** 5 * Q_density_interpolated, ret) 

    # M6: Sixth moment
    M6 = np.trapz((ret - M1) ** 6 * Q_density_interpolated, ret) 

    return {'M1': M1, 'M2': M2, 'M3': M3, 'M4': M4, 'M5': M5, 'M6': M6}


def calculate_time_varying_moments(Q_matrix, dates_Q=Q_matrix.columns[1:], ret=np.arange(-1, 1.01, 0.01)):
    M1 = []
    M2 = []
    M3 = []
    M4 = []
    M5 = []
    M6 = []

    for date_Q in dates_Q:

        # Ensure date_Q is in "yyyy-mm-dd" format
        date_Q = pd.to_datetime(date_Q).strftime('%Y-%m-%d')

        # Calculate risk-neutral moments for the given date
        Moments = moments_Q_density(date_Q, Q_matrix, ttm, ret)
        M1_t = Moments['M1']
        M2_t = Moments['M2']
        M3_t = Moments['M3']
        M4_t = Moments['M4']
        M5_t = Moments['M5']
        M6_t = Moments['M6']

        # Store the results
        M1.append((date_Q, M1_t))
        M2.append((date_Q, M2_t))
        M3.append((date_Q, M3_t))
        M4.append((date_Q, M4_t))
        M5.append((date_Q, M5_t))
        M6.append((date_Q, M6_t))

    return {'M1':M1, 'M2':M2, 'M3':M3, 'M4':M4, 'M5':M5, 'M6':M6}

def main(estimation_execute = True):
    # Load daily price data
    BTC_daily_price_path = "Data/BTC_USD_Quandl_2011_2023.csv"
    daily_price = pd.read_csv(BTC_daily_price_path, parse_dates=['Date'], dayfirst=False)

    # Sort and filter the daily price data
    daily_price = daily_price.sort_values(by='Date')
    daily_price = daily_price[(daily_price['Date'] <= '2022-12-31') & (daily_price['Date'] >= '2014-01-01')]

    # Load the common dates of the multivariate clustering
    common_dates_path = "Clustering/Tau-independent/unique/moneyness_step_0d01/multivariate_clustering_9_27_45/common_dates_cluster.csv"
    common_dates = pd.read_csv(common_dates_path)

    dates_Q = {}
    dates_Q[0] = common_dates[common_dates['Cluster']==0]['Date']
    dates_Q[1] = common_dates[common_dates['Cluster']==1]['Date']

    dates_Q_overall = pd.concat([dates_Q[0], dates_Q[1]])
    dates_Q_overall = pd.to_datetime(dates_Q_overall)
    dates_Q_overall = dates_Q_overall.sort_values()

    # Define the function to calculate forward returns
    def return_overall_forward(daily_price, dates_Q_overall, ttm, ret_type="gross"):
        return_forward = []
        for date_Q in dates_Q_overall:
            # Ensure date_Q is datetime
            date_Q = pd.to_datetime(date_Q)

            # Filter the prices for the time period between date_Q and (date_Q + ttm days)
            start_date = date_Q
            end_date = date_Q + pd.Timedelta(days=ttm)
            sp1 = daily_price[(daily_price['Date'] >= start_date) & (daily_price['Date'] <= end_date)]
            sp1 = sp1.sort_values(by='Date')
            
            # Calculate forward return
            if len(sp1) > 0:  # Check if there is enough data for the given period
                if ret_type == "gross":
                    forward_return = sp1['Adj.Close'].iloc[-1] / sp1['Adj.Close'].iloc[0]
                elif ret_type == "log":
                    forward_return = np.log(sp1['Adj.Close'].iloc[-1] / sp1['Adj.Close'].iloc[0])
                elif ret_type == "simple":
                    forward_return = (sp1['Adj.Close'].iloc[-1] / sp1['Adj.Close'].iloc[0]) - 1
                else:
                    raise ValueError(f"Invalid return type: {ret_type}")
            else:
                forward_return = np.nan  # Handle missing data
            
            return_forward.append(forward_return)
    
        return np.array(return_forward)

    # Calculate forward returns
    return_forward = return_overall_forward(daily_price, dates_Q_overall, ttm)

    # Define the gross risk-free rate
    R_f = 1
    
    # Calculate excess returns (forward return - risk-free rate)
    excess_returns = return_forward - R_f

    def equation_63(params, Q_matrix, R_f, excess_returns, ret, dates_Q_overall):
        tau, rho, kappa, alpha1, alpha2, alpha3 = params

        params_LB = [tau, rho, kappa]
        
        # Calculate the unrestricted lower bound of expected excess returns
        LB1_t_df = calculate_time_varying_LBU(Q_matrix, params_LB, R_f, dates_Q_overall)
        LB1_t = LB1_t_df['Lower_Bound']
        
        # Ensure excess_returns_t is numeric
        excess_returns_t = pd.to_numeric(excess_returns, errors='coerce')
        
        # Compute the residuals for equation (63)
        residuals = excess_returns_t - alpha1 - LB1_t
        
        return residuals
        
    def equation_64(params, Q_matrix, R_f, excess_returns, ret, dates_Q_overall, Moments):
        tau, rho, kappa, alpha1, alpha2, alpha3 = params
        
        params_UB = [tau, rho, kappa]
        
        # Calculate the model-implied upper bound of expected excess returns
        UB2_t_df = calculate_time_varying_UBU2(Q_matrix, params_UB, R_f, dates_Q_overall)
        UB2_t = UB2_t_df['Upper_Bound']
        
        # Ensure excess_returns_t is numeric
        excess_returns_t = pd.to_numeric(excess_returns, errors='coerce')
        
        # The 'y' term is defined as excess returns squared minus the second moment (variance)
        M2 = np.array(Moments['M2'])[:,1].astype(float)
        y = excess_returns_t ** 2 - M2
        
        # Compute the residuals for equation (64)
        residuals_64 = y - alpha2 - UB2_t
        
        return residuals_64
        
    def equation_65(params, Q_matrix, R_f, excess_returns, ret, dates_Q_overall, Moments):
        tau, rho, kappa, alpha1, alpha2, alpha3 = params
        
        params_LB = [tau, rho, kappa]
        
        # Calculate the model-implied lower bound of expected excess returns
        LB3_t_df = calculate_time_varying_LBU3(Q_matrix, params_LB, R_f, dates_Q_overall)
        LB3_t = LB3_t_df['Lower_Bound']
        
        # Ensure excess_returns_t is numeric
        excess_returns_t = pd.to_numeric(excess_returns, errors='coerce')
        
        # The 'y' term is defined as excess returns cubed minus the third moment (M3)
        M3 = np.array(Moments['M3'])[:,1].astype(float)
        y = excess_returns_t ** 3 - M3
        
        # Compute the residuals for equation (65)
        residuals = y - alpha3 - LB3_t
        
        return residuals

    def calculate_time_varying_LBR(Q_matrix, R_f, dates_Q_overall=Q_matrix.columns[1:], ret=np.arange(-1, 1.01, 0.01)):

        # LBR: restricted lower bound

        # This follows Eq. (31) in Chabi-Yo & Loudis (2020)

        LBR1s = []

        for date_Q in dates_Q_overall:

            # Ensure date_Q is in "yyyy-mm-dd" format
            date_Q = pd.to_datetime(date_Q).strftime('%Y-%m-%d')

            # Calculate risk-neutral moments for the given date
            Moments = moments_Q_density(date_Q, Q_matrix, ttm=ttm, ret=ret)
            M_2 = Moments['M2']
            M_3 = Moments['M3']
            M_4 = Moments['M4']

            # Compute restricted lower bound using equation (31) in Chabi-Yo & Loudis (2020)
            numerator = M_2/R_f - M_3/R_f**2 + M_4/R_f**3
            denominator = 1 - M_2/R_f**2 + M_3/R_f**3
            
            # Calculate lower bound for the given date
            LB1_t = numerator / denominator

            # Store the result
            LBR1s.append((date_Q, LB1_t))

        # Convert to a DataFrame for better handling
        LBR1_df = pd.DataFrame(LBR1s, columns=['Date', 'Lower_Bound'])

        return LBR1_df

    def calculate_time_varying_UBR2(Q_matrix, R_f, dates_Q_overall=Q_matrix.columns[1:], ret=np.arange(-1, 1.01, 0.01)):

        # UBR2: restricted upper bound

        # Under the assumption 1 and 2
        # This is similar to Eq. (31) in Chabi-Yo & Loudis (2020) with restricted parameters
        #      but with modified numerator
        # theta_1 >= 1/R_f, theta_2 <= -1/R_f**2, theta_3 >= 1/R_f**3
        # M_3 <= 0, M_4 >= 0, M_5 <=0
        # UBU2 = (theta_1 * M_3 + theta_2 * (M_4 - M_2**2) + theta_3 * (M_5 - M_3 * M_2)) / (1 + theta_2 * M_2 + theta_3 * M_3)
        #      = (M_3/R_f - (M4 - M_2**2)/R_f**2 + (M_5 - M_3 * M_2)/R_f**3) / (1 - M_2/R_f**2 + M_3/R_f**3)

        UBR2s = []

        for date_Q in dates_Q_overall:

            # Ensure date_Q is in "yyyy-mm-dd" format
            date_Q = pd.to_datetime(date_Q).strftime('%Y-%m-%d')

            # Calculate risk-neutral moments for the given date
            Moments = moments_Q_density(date_Q, Q_matrix, ttm=ttm, ret=ret)
            M_2 = Moments['M2']
            M_3 = Moments['M3']
            M_4 = Moments['M4']
            M_5 = Moments['M5']

            # Compute restricted upper bound using equation (26) in Chabi-Yo & Loudis (2020)
            # Double check the equation
            numerator = M_3/R_f - (M_4 - M_2**2)/R_f**2 + (M_5 - M_3 * M_2)/R_f**3
            denominator = 1 - M_2/R_f**2 + M_3/R_f**3

            # Calculate upper bound for the given date
            UB2_t = numerator / denominator

            # Store the result
            UBR2s.append((date_Q, UB2_t))

        # Convert to a DataFrame for better handling
        UBR2_df = pd.DataFrame(UBR2s, columns=['Date', 'Upper_Bound'])

        return UBR2_df
        
    def calculate_time_varying_LBU(Q_matrix, params, R_f, dates_Q_overall=Q_matrix.columns[1:], ret=np.arange(-1, 1.01, 0.01)):

        lower_bounds = []

        tau, rho, kappa = params

        for date_Q in dates_Q_overall:

            # Ensure date_Q is in "yyyy-mm-dd" format
            date_Q = pd.to_datetime(date_Q).strftime('%Y-%m-%d')

            # Calculate risk-neutral moments for the given date
            Moments = moments_Q_density(date_Q, Q_matrix, ttm=ttm, ret=ret)
            M_1 = Moments['M1']
            M_2 = Moments['M2']
            M_3 = Moments['M3']
            M_4 = Moments['M4']

            # Compute theta parameters using equation (21) in Chabi-Yo & Loudis (2020)
            theta_1 = 1 / (tau * R_f)
            theta_2 = (1 - rho) / (tau ** 2 * R_f ** 2)
            theta_3 = (1 - 2 * rho + kappa) / (tau ** 3 * R_f ** 3)

            # Estimate the lower bound using equation (27) in Chabi-Yo & Loudis (2020)
            numerator = theta_1 * M_2 + theta_2 * M_3 + theta_3 * M_4
            #denominator = 1 + theta_1 * M_1 + theta_2 * M_2 + theta_3 * M_3
            denominator = 1 + theta_2 * M_2 + theta_3 * M_3

            # Calculate lower bound for the given date
            LB1_t = numerator / denominator

            # Store the result
            lower_bounds.append((date_Q, LB1_t))

        # Convert to a DataFrame for better handling
        LBU = pd.DataFrame(lower_bounds, columns=['Date', 'Lower_Bound'])

        return LBU
        
    def calculate_time_varying_UBU2(Q_matrix, params, R_f, dates_Q_overall=Q_matrix.columns[1:], ret=np.arange(-1, 1.01, 0.01)):

        upper_bounds = []

        tau, rho, kappa = params

        for date_Q in dates_Q_overall:

            # Ensure date_Q is in "yyyy-mm-dd" format
            date_Q = pd.to_datetime(date_Q).strftime('%Y-%m-%d')

            # Calculate risk-neutral moments for the given date
            Moments = moments_Q_density(date_Q, Q_matrix, ttm=ttm, ret=ret)
            M_2 = Moments['M2']
            M_3 = Moments['M3']
            M_4 = Moments['M4']
            M_5 = Moments['M5']

            # Compute theta parameters using equation (21) in Chabi-Yo & Loudis (2020)
            theta_1 = 1 / (tau * R_f)
            theta_2 = (1 - rho) / (tau ** 2 * R_f ** 2)
            theta_3 = (1 - 2 * rho + kappa) / (tau ** 3 * R_f ** 3)

            # Estimate the lower bound using equation (27) in Chabi-Yo & Loudis (2020)
            numerator = theta_1 * M_3 + theta_2 * (M_4 - M_2 ** 2) + theta_3 * (M_5 - M_3 * M_2)
            denominator = 1 + theta_2 * M_2 + theta_3 * M_3

            # Calculate lower bound for the given date
            UB2_t = numerator / denominator

            # Store the result
            upper_bounds.append((date_Q, UB2_t))

        # Convert to a DataFrame for better handling
        UBU2 = pd.DataFrame(upper_bounds, columns=['Date', 'Upper_Bound'])

        return UBU2

    def calculate_time_varying_LBU3(Q_matrix, params, R_f, dates_Q_overall=Q_matrix.columns[1:], ret=np.arange(-1, 1.01, 0.01)):

        lower_bounds = []

        tau, rho, kappa = params

        for date_Q in dates_Q_overall:

            # Ensure date_Q is in "yyyy-mm-dd" format
            date_Q = pd.to_datetime(date_Q).strftime('%Y-%m-%d')

            # Calculate risk-neutral moments for the given date
            Moments = moments_Q_density(date_Q, Q_matrix, ttm=ttm, ret=ret)
            M_2 = Moments['M2']
            M_3 = Moments['M3']
            M_4 = Moments['M4']
            M_5 = Moments['M5']
            M_6 = Moments['M6']

            # Compute theta parameters using equation (21) in Chabi-Yo & Loudis (2020)
            theta_1 = 1 / (tau * R_f)
            theta_2 = (1 - rho) / (tau ** 2 * R_f ** 2)
            theta_3 = (1 - 2 * rho + kappa) / (tau ** 3 * R_f ** 3)

            # Estimate the lower bound using equation (27) in Chabi-Yo & Loudis (2020)
            numerator = theta_1 * M_4 + theta_2 * (M_5 - M_3 * M_2) + theta_3 * (M_6 - M_4 * M_3) 
            denominator = 1 + theta_2 * M_2 + theta_3 * M_3

            # Calculate lower bound for the given date
            LB3_t = numerator / denominator

            # Store the result
            lower_bounds.append((date_Q, LB3_t))

        # Convert to a DataFrame for better handling
        LBU3 = pd.DataFrame(lower_bounds, columns=['Date', 'Lower_Bound'])

        return LBU3

    def estimate_preference_parameters_in_LBU(Q_matrix, params0, R_f, excess_returns, Moments, ret=np.arange(-1, 1.01, 0.01), \
        dates_Q_overall=Q_matrix.columns[1:], reg_lambda=0.01):

        # First step: equally weighted moments for Eq. (63)-(65) + L2 regularization on (tau, rho, kappa)
        # Nonlinear least squares with regularization: 惩罚偏好参数过大，使估计更稳定
        def objective_function(params, weights, reg_lambda, Q_matrix, R_f, ret=np.arange(-1, 1.01, 0.01), \
            dates_Q_overall=Q_matrix.columns[1:]):
            
            weight63 = weights[0]
            weight64 = weights[1]
            weight65 = weights[2]

            tau, rho, kappa, alpha1, alpha2, alpha3 = params
            params_LBU = [tau, rho, kappa]
            
            # Calculate the lower bound
            LBU = calculate_time_varying_LBU(Q_matrix, params_LBU, R_f, dates_Q_overall, ret)

            residual63 = equation_63(params, Q_matrix, R_f, excess_returns, ret, dates_Q_overall)
            residual64 = equation_64(params, Q_matrix, R_f, excess_returns, ret, dates_Q_overall, Moments)
            residual65 = equation_65(params, Q_matrix, R_f, excess_returns, ret, dates_Q_overall, Moments)

            # 矩条件损失 + L2 正则化（仅对 tau, rho, kappa），抑制参数绝对值过大
            moment_loss = np.sum(residual63 ** 2 * weight63 + residual64 **2 * weight64 + residual65 ** 2 * weight65)
            reg_penalty = reg_lambda * (tau**2 + rho**2 + kappa**2)
            return moment_loss + reg_penalty
    
        # Equal weights
        weights = [w/3 for w in [1, 1, 1]]

        # Use scipy.optimize.minimize to find the optimal parameters (with regularization)
        result = minimize(objective_function, params0, args=(weights, reg_lambda, Q_matrix, R_f, ret, dates_Q_overall), method='Nelder-Mead')

        # Extract the optimized parameters
        params = result.x
        
        fitness = result.fun
        print(f"The fitness of the first step is {fitness}")

        residual63 = equation_63(params, Q_matrix, R_f, excess_returns, ret, dates_Q_overall)
        residual64 = equation_64(params, Q_matrix, R_f, excess_returns, ret, dates_Q_overall, Moments)
        residual65 = equation_65(params, Q_matrix, R_f, excess_returns, ret, dates_Q_overall, Moments)

        Variance63 = np.var(residual63)
        Variance64 = np.var(residual64)
        Variance65 = np.var(residual65)

        weights_new = [1 / Variance63, 1 / Variance64, 1 / Variance65]
        weights_new = weights_new / np.sum(weights_new)
        weights_new_df = pd.DataFrame({'weights': weights_new})
        weights_new_df.to_csv(os.path.join(OUTPUT_DIR, "weights_2nd_step.csv"), index=False)

        # Second step: weighted by variance of residuals s.t. more weights for lower variance (with same regularization)
        result_2nd = minimize(objective_function, params, args=(weights_new, reg_lambda, Q_matrix, R_f, ret, dates_Q_overall), method='Nelder-Mead')
        params = result_2nd.x

        fitness = result_2nd.fun
        print(f"The fitness of the second step is {fitness}")

        return params

    # The gross risk-free rate, set to 1 because it is defined by simple return plus one
    R_f = 1

    # Calculate time-varying moments
    Moments = calculate_time_varying_moments(Q_matrix, dates_Q_overall)

    # Convert Moments to numpy arrays for element-wise operations
    M2_array = np.array(Moments['M2'])[:,1].astype(float)
    M3_array = np.array(Moments['M3'])[:,1].astype(float)
    M4_array = np.array(Moments['M4'])[:,1].astype(float)

    # 确保结果输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if estimation_execute:

        # Estimate the preference parameters in the lower bound
        # Set initial values for the parameters
        tau = 0.97 # risk tolerance
        rho = 2.32 # skewness preference
        kappa = 3.50 # kurtosis preference
        alpha1 = 0.0042
        alpha2 = -1e-4
        alpha3 = 9.2e-5

        params = [tau, rho, kappa, alpha1, alpha2, alpha3]
        weights = [w/3 for w in [1, 1, 1]]
        # reg_lambda: 正则化强度，越大则 tau/rho/kappa 的估计值越被压小
        reg_lambda = 0.01
        params_estimated = estimate_preference_parameters_in_LBU(Q_matrix, params, R_f, excess_returns, 
                                                        Moments, 
                                                        np.arange(-1, 1.01, 0.01),
                                                        dates_Q_overall, reg_lambda=reg_lambda)
        tau = params_estimated[0]
        rho = params_estimated[1]
        kappa = params_estimated[2]
        alpha1 = params_estimated[3]
        alpha2 = params_estimated[4]
        alpha3 = params_estimated[5]
        params = [tau, rho, kappa]

        # Save the preference parameters to the csv file
        params_df = pd.DataFrame({'tau': [tau], 'rho': [rho], 'kappa': [kappa], 'alpha1': [alpha1], 'alpha2': [alpha2], 'alpha3': [alpha3]})
        params_df.to_csv(os.path.join(OUTPUT_DIR, "Chabi-Yo_LBU_params.csv"), index=False)

    else:
        # Load the preference parameters from the csv file
        params_df = pd.read_csv(os.path.join(OUTPUT_DIR, "Chabi-Yo_LBU_params.csv"))
        tau = float(params_df['tau'].values[0])
        rho = float(params_df['rho'].values[0])
        kappa = float(params_df['kappa'].values[0])
        alpha1 = float(params_df['alpha1'].values[0])
        alpha2 = float(params_df['alpha2'].values[0])
        alpha3 = float(params_df['alpha3'].values[0])
        params = [tau, rho, kappa]

    # Eq.(21) in Chabi-Yo & Loudis (2020): theta from tau, rho, kappa，单独输出为 CSV
    theta1 = 1 / (tau * R_f)
    theta2 = (1 - rho) / (tau ** 2 * R_f ** 2)
    theta3 = (1 - 2 * rho + kappa) / (tau ** 3 * R_f ** 3)
    theta_df = pd.DataFrame({'theta1': [theta1], 'theta2': [theta2], 'theta3': [theta3]})
    theta_df.to_csv(os.path.join(OUTPUT_DIR, "CL20_theta_S10_4.csv"), index=False)

    # Calculate the BP unrestricted lower bounds using Eq. (27) in Chabi-Yo & Loudis (2020)
    LBU = calculate_time_varying_LBU(Q_matrix, params, R_f, dates_Q_overall)
    LBU["Lower_Bound"] = LBU["Lower_Bound"] / ttm * 365

    # Calculate the BP restricted lower bounds using Eq. (31) in Chabi-Yo & Loudis (2020)
    LBR = calculate_time_varying_LBR(Q_matrix, R_f, dates_Q_overall)
    LBR["Lower_Bound"] = LBR["Lower_Bound"] / ttm * 365
    
    # Calculate the VRP unrestricted upper bounds using Eq. (26) in Chabi-Yo & Loudis (2020)
    UBU2 = calculate_time_varying_UBU2(Q_matrix, params, R_f, dates_Q_overall)
    UBU2["Upper_Bound"] = UBU2["Upper_Bound"] / ttm * 365

    # Calculate the VRP restricted upper bounds similar to LBR by Eq. (31) in Chabi-Yo & Loudis (2020) but with the second moment
    UBR2 = calculate_time_varying_UBR2(Q_matrix, R_f, dates_Q_overall)
    UBR2["Upper_Bound"] = UBR2["Upper_Bound"] / ttm * 365

    # Martin (2017) measure of BP lower bound
    # Section 2.3 in Chabi-Yo & Loudis (2020) illustrates the formula
    MB = {'Lower_Bound': M2_array / R_f /ttm * 365, 'Date': dates_Q_overall}
    MB = pd.DataFrame(MB, columns=['Date', 'Lower_Bound'])

    # Chabi-Yo & Loudis (2020) BP restricted lower bound
    # Equation (31) LBR
    #denominator = M2_array / R_f - M3_array / R_f**2 + M4_array / R_f**3
    #numerator = 1 - M2_array / R_f**2 + M3_array / R_f**3
    #LBR = {'Lower_Bound': denominator / numerator, 'Date': dates_Q_overall}
    #LBR = pd.DataFrame(LBR, columns=['Date', 'Lower_Bound'])
    #LBR['Lower_Bound'] = LBR['Lower_Bound'] / ttm * 365

    # Plot
    # Ensure all Date columns are in datetime format before plotting
    # Convert to datetime and ensure they are in the same type
    MB['Date'] = pd.to_datetime(MB['Date'])
    LBU['Date'] = pd.to_datetime(LBU['Date'])
    LBR['Date'] = pd.to_datetime(LBR['Date'])
    UBU2['Date'] = pd.to_datetime(UBU2['Date'])
    UBR2['Date'] = pd.to_datetime(UBR2['Date'])
    
    # Sort all DataFrames by Date to ensure consistent plotting
    MB = MB.sort_values(by='Date')
    LBU = LBU.sort_values(by='Date')
    LBR = LBR.sort_values(by='Date')
    UBU2 = UBU2.sort_values(by='Date')
    UBR2 = UBR2.sort_values(by='Date')

    # Plot BP lower bounds
    plt.figure(figsize=(10, 6))
    # Plot Martin (2017) BP lower bounds
    plt.plot(MB['Date'], MB['Lower_Bound'], label='Martin17 Lower Bound', color='red', linewidth=2)
    # Plot Chabi-Yo & Loudis (2020) BP Unrestricted Lower Bound
    plt.plot(LBU['Date'], LBU['Lower_Bound'], label='CL20 Unrestricted Lower Bound (regularization)', color='blue', linewidth=2)
    # Plot Chabi-Yo & Loudis (2020) BP Restricted Lower Bound
    plt.plot(LBR['Date'], LBR['Lower_Bound'], label='CL20 Restricted Lower Bound ', color='green', linewidth=2)
    # Formatting the x-axis with yearly intervals and specific date limits
    plt.gca().xaxis.set_major_locator(mdates.YearLocator())  # Set major ticks to yearly intervals
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y'))  # Set the date format to just show the year

    # Convert date limits to the appropriate datetime format
    start_date = pd.to_datetime('2017-07-01')
    end_date = pd.to_datetime('2022-12-17')

    # Set limits for the x-axis
    plt.xlim(start_date, end_date)
    # Add labels and title
    plt.xlabel('Date', fontsize=18)
    plt.ylabel('Lower Bound', fontsize=18)
    plt.title('Time-Varying Bitcoin Premium Lower Bound by CL20 (regularization)', fontsize=18)
    # Rotate x-tick labels for better readability
    plt.xticks(rotation=45)
    # Add grid, legend, and show the plot
    plt.grid(True)
    plt.tight_layout()
    plt.legend(fontsize=12)
    # Save the plot
    lower_bound_plot_path = os.path.join(OUTPUT_DIR, "Martin_Chabi-Yo_LB.png")
    os.makedirs(os.path.dirname(lower_bound_plot_path), exist_ok=True)
    plt.savefig(lower_bound_plot_path, dpi=300, bbox_inches='tight')
    plt.close()

    # Plot VRP upper bounds
    plt.figure(figsize=(10, 6))
    # Plot Chabi-Yo & Loudis (2020) VRP Unrestricted Upper Bound
    plt.plot(UBU2['Date'], UBU2['Upper_Bound'], label='CL20 Unrestricted Upper Bound (regularization)', color='blue', linewidth=2)
    # Plot Chabi-Yo & Loudis (2020) VRPRestricted Upper Bound
    plt.plot(UBR2['Date'], UBR2['Upper_Bound'], label='CL20 Restricted Upper Bound', color='green', linewidth=2)
    # Formatting the x-axis with yearly intervals and specific date limits
    plt.gca().xaxis.set_major_locator(mdates.YearLocator())  # Set major ticks to yearly intervals
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y'))  # Set the date format to just show the year
    
    # Convert date limits to the appropriate datetime format
    start_date = pd.to_datetime('2017-07-01')
    end_date = pd.to_datetime('2022-12-17')
    
    # Set limits for the x-axis
    plt.xlim(start_date, end_date)
    # Add labels and title
    plt.xlabel('Date', fontsize=18)
    plt.ylabel(r'$\mathrm{E}_t^P[R_T^2]-\mathrm{E}_t^Q[R_T^2]$', fontsize=18)
    plt.title('Time-Varying Bitcoin VRP by CL20 (regularization)', fontsize=18)
    # Rotate x-tick labels for better readability
    plt.xticks(rotation=45)
    # Add grid, legend, and show the plot
    plt.grid(True)
    plt.tight_layout()
    plt.legend(fontsize=12)
    # Save the plot
    upper_bound_plot_path = os.path.join(OUTPUT_DIR, "Chabi-Yo_UBU2_UBR2_B2.png")
    os.makedirs(os.path.dirname(upper_bound_plot_path), exist_ok=True)
    plt.savefig(upper_bound_plot_path, dpi=300, bbox_inches='tight')
    plt.close()

    # Save the lower bounds in csv
    MB.to_csv(os.path.join(OUTPUT_DIR, "Martin_MB.csv"), index=False)
    LBU.to_csv(os.path.join(OUTPUT_DIR, "Chabi-Yo_LBU.csv"), index=False)
    LBR.to_csv(os.path.join(OUTPUT_DIR, "Chabi-Yo_LBR.csv"), index=False)
    # Save the upper bounds in csv
    UBU2.to_csv(os.path.join(OUTPUT_DIR, "Chabi-Yo_UBU2.csv"), index=False)
    UBR2.to_csv(os.path.join(OUTPUT_DIR, "Chabi-Yo_UBR2.csv"), index=False)

    # Show preference parameters
    print(f"tau: {tau:.4f}, rho: {rho:.4f}, kappa: {kappa:.4f}")
    print(f"alpha1: {alpha1:.4f}, alpha2: {alpha2:.4f}, alpha3: {alpha3:.4f}")
    a0 = 1
    a1 = 1/tau
    a2 = (1 - rho) / (tau**2 )
    a3 = (1 - 2 * rho + kappa) / (tau**3)
    print(f"a0: {a0:.4f}, a1: {a1:.4f}, a2: {a2:.4f}, a3: {a3:.4f}")
    # Show the details of lower bounds
    print(f"Q first moment: {np.average(np.array(Moments['M1'])[:,1].astype(float)):.4f}")
    print(f"Q variance: {np.average(M2_array):.4f}")
    print(f"Skewness: {np.average(M3_array):.4f} std. {np.std(M3_array):.4f}")
    print(f"Kurtosis: {np.average(M4_array):.4f} std. {np.std(M4_array):.4f}")
    print(f"Martin (2017) lower bound: {np.average(MB['Lower_Bound']):.4f}")
    print(f"Chabi-Yo & Loudis (2020) unrestricted lower bound: {np.average(LBU['Lower_Bound']):.4f}")
    print(f"Chabi-Yo & Loudis (2020) restricted lower bound: {np.average(LBR['Lower_Bound']):.4f}")


    print(f"For unrestricted lower bound")
    theta1 = 1/(tau*R_f)
    theta2 = (1-rho)/(tau**2 * R_f **2)
    theta3 = (1-2*rho+kappa)/(tau**3*R_f**3)
    print(f"theta1: {theta1:.4f}, theta2: {theta2:.4f}, theta3: {theta3:.4f}")
    print(f"the numerator is theta1 * M2 + theta2 * M3 + theta3 * M4 = ")
    print(f"{np.average(theta1*M2_array + theta2*M3_array + theta3*M4_array)}")
    print(f"the denominator is 1 + theta2 * M2 + theta3 * M3 = ")
    print(f"{np.average(1 + theta2*M2_array + theta3*M3_array)}")

    print(f"For restricted lower bound")
    print(f"the numerator is M2/R_f - M3/R_f**2 + M4/R_f**3")
    print(f"{np.average(M2_array/R_f - M3_array/R_f**2 + M4_array/R_f**3)}")
    print(f"the denominator is 1 - M2/R_f**2 + M3/R_f**3")
    print(f"{np.average(1-M2_array/R_f**2 + M3_array/R_f**3)}")

    # Lower bounds for the two clusters: HV and LV
    dates_HV = pd.to_datetime(dates_Q[0])
    dates_LV = pd.to_datetime(dates_Q[1])

    # HV Bounds
    UBU2_HV = UBU2[UBU2['Date'].isin(dates_HV)]
    UBR2_HV = UBR2[UBR2['Date'].isin(dates_HV)]
    LBU_HV = LBU[LBU['Date'].isin(dates_HV)]
    LBR_HV = LBR[LBR['Date'].isin(dates_HV)]
    MB_HV = MB[MB['Date'].isin(dates_HV)]

    # LV Bounds
    UBU2_LV = UBU2[UBU2['Date'].isin(dates_LV)]
    UBR2_LV = UBR2[UBR2['Date'].isin(dates_LV)]
    LBU_LV = LBU[LBU['Date'].isin(dates_LV)]
    LBR_LV = LBR[LBR['Date'].isin(dates_LV)]
    MB_LV = MB[MB['Date'].isin(dates_LV)]

    summary_df = pd.DataFrame({
        'Metric': ['Mean', 'Median', 'Std'],
        'UBU2_OA': [UBU2['Upper_Bound'].mean(), UBU2['Upper_Bound'].median(), UBU2['Upper_Bound'].std()],
        'UBU2_HV': [UBU2_HV['Upper_Bound'].mean(), UBU2_HV['Upper_Bound'].median(), UBU2_HV['Upper_Bound'].std()],
        'UBU2_LV': [UBU2_LV['Upper_Bound'].mean(), UBU2_LV['Upper_Bound'].median(), UBU2_LV['Upper_Bound'].std()],
        'UBR2_OA': [UBR2['Upper_Bound'].mean(), UBR2['Upper_Bound'].median(), UBR2['Upper_Bound'].std()],
        'UBR2_HV': [UBR2_HV['Upper_Bound'].mean(), UBR2_HV['Upper_Bound'].median(), UBR2_HV['Upper_Bound'].std()],
        'UBR2_LV': [UBR2_LV['Upper_Bound'].mean(), UBR2_LV['Upper_Bound'].median(), UBR2_LV['Upper_Bound'].std()],
        'LBU_OA': [LBU['Lower_Bound'].mean(), LBU['Lower_Bound'].median(), LBU['Lower_Bound'].std()],
        'LBU_HV': [LBU_HV['Lower_Bound'].mean(), LBU_HV['Lower_Bound'].median(), LBU_HV['Lower_Bound'].std()],
        'LBU_LV': [LBU_LV['Lower_Bound'].mean(), LBU_LV['Lower_Bound'].median(), LBU_LV['Lower_Bound'].std()],
        'LBR_OA': [LBR['Lower_Bound'].mean(), LBR['Lower_Bound'].median(), LBR['Lower_Bound'].std()],
        'LBR_HV': [LBR_HV['Lower_Bound'].mean(), LBR_HV['Lower_Bound'].median(), LBR_HV['Lower_Bound'].std()],
        'LBR_LV': [LBR_LV['Lower_Bound'].mean(), LBR_LV['Lower_Bound'].median(), LBR_LV['Lower_Bound'].std()],
        'MB_OA': [MB['Lower_Bound'].mean(), MB['Lower_Bound'].median(), MB['Lower_Bound'].std()],
        'MB_HV': [MB_HV['Lower_Bound'].mean(), MB_HV['Lower_Bound'].median(), MB_HV['Lower_Bound'].std()],
        'MB_LV': [MB_LV['Lower_Bound'].mean(), MB_LV['Lower_Bound'].median(), MB_LV['Lower_Bound'].std()]
    })
    summary_df = summary_df.round(4)

    print(summary_df)

    summary_df.to_csv(os.path.join(OUTPUT_DIR, "BP_VRP_Martin_CL20_Summary.csv"), index=False)



    ########################### Calculate P density ###########################
    ## Inverse of PK: inv_PK(x) = 1 + theta_1 * (x - x0) + theta_2 * (x - x0)**2 + theta_3 * (x - x0)**3
    # x0 = 0
    # inv_PK(x) = 1 + theta_1 * x + theta_2 * x**2 + theta_3 * x**3
    x_grid = np.arange(-1, 1.01, 0.01)
    inv_PK = 1 + theta1 * x_grid + theta2 * x_grid**2 + theta3 * x_grid**3
    PK = 1 / inv_PK
    PK_df = pd.DataFrame({'x': x_grid, 'inv_PK': inv_PK, 'PK': PK})
    PK_df.to_csv(os.path.join(OUTPUT_DIR, "PK_CL20.csv"), index=False)

    mask = (PK_df['PK'] > -100) & (PK_df['PK'] < 100)

    # Plot the inv_PK
    plt.figure(figsize=(10, 6))
    plt.plot(PK_df['x'][mask], PK_df['inv_PK'][mask], label='inv_PK', color='k', linestyle='-.', linewidth=2)
    plt.xlabel('x', fontsize=18)
    plt.ylabel('inv_PK', fontsize=18)
    plt.title('inv_PK by CL20', fontsize=18)
    plt.grid(True)
    plt.tight_layout()
    plt.legend(fontsize=12)
    plt.savefig(os.path.join(OUTPUT_DIR, "inv_PK_CL20.png"), dpi=300, bbox_inches='tight')
    plt.close()

    # Plot the PK
    plt.figure(figsize=(10, 6))
    plt.plot(PK_df['x'][mask], PK_df['PK'][mask], label='PK', color='k', linestyle='-.', linewidth=2)
    plt.xlabel('x', fontsize=18)
    plt.ylabel('PK', fontsize=18)
    plt.title('PK by CL20', fontsize=18)
    plt.grid(True)
    plt.tight_layout()
    plt.legend(fontsize=12)
    plt.savefig(os.path.join(OUTPUT_DIR, "PK_CL20.png"), dpi=300, bbox_inches='tight')
    plt.close()

    # P density: P(x) = inv_PK(x) * Q(x)，Q(x) 为风险中性密度，按时间维度取平均
    date_cols = [c for c in Q_matrix.columns if c != 'Return']
    Q_avg = Q_matrix[date_cols].mean(axis=1).values
    Q_density_avg = np.interp(x_grid, Q_matrix['Return'].values, Q_avg, left=0, right=0)

    # Plot the Q density
    Q_density_avg = Q_density_avg / np.trapz(Q_density_avg, x_grid)
    print(f"Q_density integration: {np.trapz(Q_density_avg, x_grid)}")
    plt.figure(figsize=(10, 6))
    plt.plot(x_grid, Q_density_avg, label='Q_density', color='k', linestyle='-', linewidth=2)
    plt.xlabel('x', fontsize=18)
    plt.ylabel('Q_density', fontsize=18)
    plt.title('Q_density (average)', fontsize=18)
    plt.grid(True)
    plt.tight_layout()
    plt.legend(fontsize=12)
    plt.savefig(os.path.join(OUTPUT_DIR, "Q_density_average_CL20.png"), dpi=300, bbox_inches='tight')
    plt.close()

    #Q_density_avg[Q_density_avg < 0] = 0
    P_density = PK_df['inv_PK'].values * Q_density_avg
    P_density_df = pd.DataFrame({'x': x_grid, 'P_density': P_density})
    P_density_df.to_csv(os.path.join(OUTPUT_DIR, "P_density_CL20.csv"), index=False)

    # Plot the P density
    P_density_df['P_density'] = P_density_df['P_density'] / np.trapz(P_density_df['P_density'].values, x_grid)
    print(f"P_density integration: {np.trapz(P_density_df['P_density'].values, x_grid)}")
    plt.figure(figsize=(10, 6))
    plt.plot(P_density_df['x'][mask], P_density_df['P_density'][mask], label='P_density', color='k', linestyle='--', linewidth=2)
    plt.xlabel('x', fontsize=18)
    plt.ylabel('P_density', fontsize=18)
    plt.title('P_density by CL20', fontsize=18)
    plt.grid(True)
    plt.tight_layout()
    plt.legend(fontsize=12)
    plt.savefig(os.path.join(OUTPUT_DIR, "P_density_CL20.png"), dpi=300, bbox_inches='tight')
    plt.close()

    # Q density, P density, PK 画在一张图上（双 y 轴：左轴密度，右轴 PK）
    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.plot(x_grid, Q_density_avg, label='Q density', color='k', linestyle='-', linewidth=2)
    ax1.plot(x_grid, P_density_df['P_density'].values, label='P density', color='k', linestyle='--', linewidth=2)
    #ax1.set_xlabel('x', fontsize=18)
    ax1.set_ylabel('Density', fontsize=18)
    ax1.tick_params(axis='y', labelcolor='black')
    ax1.grid(False)
    ax1.set_ylim(-0.1, 4.0)
    ax1.set_xticks([-1, -0.6, -0.2, 0.2, 0.6, 1])
    ax1.set_xticklabels(['-1', '-0.6', '-0.2', '0.2', '0.6', '1'])
    ax1.set_xlim(-1, 1)
    ax2 = ax1.twinx()
    ax2.plot(x_grid[mask], PK_df['PK'][mask].values, label='PK', color='k', linewidth=2, linestyle='-.')
    ax2.set_ylabel('PK', fontsize=18)
    ax2.tick_params(axis='y', labelcolor='k')
    ax2.set_ylim(-1, 5)
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc='lower center', bbox_to_anchor=(0.1, 0.8), fontsize=12)
    plt.title('Q density, P density and PK by CL20', fontsize=18)
    fig.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "Q_P_density_PK_CL20.png"), dpi=300, bbox_inches='tight')
    plt.close()

    # Calculate the BP decomposition: BP(x) = E_P(x) - E_Q(x)
    BP = []
    BP_full = np.trapz(P_density_df['P_density'].values * x_grid, x_grid) - np.trapz(Q_density_avg * x_grid, x_grid)
    print(f"BP_full: {BP_full}")
    for x in x_grid:
        x_mask = (x_grid <= x) 
        BP_x = np.trapz(P_density_df['P_density'].values[x_mask] * x_grid[x_mask], x_grid[x_mask]) - np.trapz(Q_density_avg[x_mask] * x_grid[x_mask], x_grid[x_mask])
        BP.append(BP_x/BP_full)
    BP_df = pd.DataFrame({'x': x_grid, 'BP': BP})
    BP_df.to_csv(os.path.join(OUTPUT_DIR, "BP_CL20.csv"), index=False)

    # Plot the BP
    plt.figure(figsize=(10, 6))
    plt.plot(BP_df['x'], BP_df['BP'], label='BP', color='k', linestyle='-', linewidth=2)
    #plt.xlabel('x', fontsize=18)
    plt.ylabel('BP', fontsize=18)
    plt.title('BP by CL20', fontsize=18)
    plt.grid(True)
    plt.tight_layout()
    plt.legend(fontsize=12)
    plt.savefig(os.path.join(OUTPUT_DIR, "BP_CL20.png"), dpi=300, bbox_inches='tight')
    plt.close()


    # HV cluster: Q 按 HV 日期取平均，P = PK * Q_HV，PK 不变
    dates_HV_str = set(pd.Series(pd.to_datetime(dates_HV)).dt.strftime('%Y-%m-%d').tolist())
    HV_cols = [c for c in Q_matrix.columns if c != 'Return' and pd.to_datetime(c).strftime('%Y-%m-%d') in dates_HV_str]
    if len(HV_cols) > 0:
        Q_avg_HV = Q_matrix[HV_cols].mean(axis=1).values
        Q_density_HV = np.interp(x_grid, Q_matrix['Return'].values, Q_avg_HV, left=0, right=0)
        Q_density_HV[Q_density_HV < 0] = 0
        P_density_HV = PK_df['PK'].values * Q_density_HV
        fig, ax1 = plt.subplots(figsize=(10, 6))
        ax1.plot(x_grid, Q_density_HV, label='Q density', color='blue', linestyle='-', linewidth=2)
        ax1.plot(x_grid, P_density_HV, label='P density', color='blue', linestyle='--', linewidth=2)
        ax1.set_ylabel('Density', fontsize=18)
        ax1.tick_params(axis='y', labelcolor='black')
        ax1.grid(False)
        ax1.set_ylim(-0.1, 4.0)
        ax1.set_xticks([-1, -0.6, -0.2, 0.2, 0.6, 1])
        ax1.set_xticklabels(['-1', '-0.6', '-0.2', '0.2', '0.6', '1'])
        ax1.set_xlim(-1, 1)
        ax2 = ax1.twinx()
        ax2.plot(x_grid[mask], PK_df['PK'][mask].values, label='PK', color='blue', linewidth=2, linestyle='-.')
        ax2.set_ylabel('PK', fontsize=18)
        ax2.tick_params(axis='y', labelcolor='k')
        ax2.set_ylim(-1, 5)
        h1, l1 = ax1.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax1.legend(h1 + h2, l1 + l2, loc='lower center', bbox_to_anchor=(0.1, 0.8), prop={'size': 12, 'weight': 'bold'}, framealpha=1)
        plt.title('Q density, P density and PK by CL20 (HV cluster)', fontsize=18)
        fig.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "Q_P_density_PK_CL20_HV.png"), dpi=300, bbox_inches='tight')
        plt.close()

    # LV cluster: Q 按 LV 日期取平均，P = PK * Q_LV，PK 不变
    dates_LV_str = set(pd.Series(pd.to_datetime(dates_LV)).dt.strftime('%Y-%m-%d').tolist())
    LV_cols = [c for c in Q_matrix.columns if c != 'Return' and pd.to_datetime(c).strftime('%Y-%m-%d') in dates_LV_str]
    if len(LV_cols) > 0:
        Q_avg_LV = Q_matrix[LV_cols].mean(axis=1).values
        Q_density_LV = np.interp(x_grid, Q_matrix['Return'].values, Q_avg_LV, left=0, right=0)
        Q_density_LV[Q_density_LV < 0] = 0
        P_density_LV = PK_df['PK'].values * Q_density_LV
        fig, ax1 = plt.subplots(figsize=(10, 6))
        ax1.plot(x_grid, Q_density_LV, label='Q density', color='red', linestyle='-', linewidth=2)
        ax1.plot(x_grid, P_density_LV, label='P density', color='red', linestyle='--', linewidth=2)
        ax1.set_ylabel('Density', fontsize=18)
        ax1.tick_params(axis='y', labelcolor='black')
        ax1.grid(False)
        ax1.set_ylim(-0.1, 4.0)
        ax1.set_xticks([-1, -0.6, -0.2, 0.2, 0.6, 1])
        ax1.set_xticklabels(['-1', '-0.6', '-0.2', '0.2', '0.6', '1'])
        ax1.set_xlim(-1, 1)
        ax2 = ax1.twinx()
        ax2.plot(x_grid[mask], PK_df['PK'][mask].values, label='PK', color='red', linewidth=2, linestyle='-.')
        ax2.set_ylabel('PK', fontsize=18)
        ax2.tick_params(axis='y', labelcolor='k')
        ax2.set_ylim(-1, 5)
        h1, l1 = ax1.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax1.legend(h1 + h2, l1 + l2, loc='lower center', bbox_to_anchor=(0.1, 0.8), fontsize=12)
        plt.title('Q density, P density and PK by CL20 (LV cluster)', fontsize=18)
        fig.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "Q_P_density_PK_CL20_LV.png"), dpi=300, bbox_inches='tight')
        plt.close()

if __name__ == "__main__":
    main(estimation_execute = False)