#!/usr/bin/env python
# coding: utf-8

# # Code for conditional preference based decomposition
# ### Throughout the code we have taken inspiration from the code accompanying the Chabi-Yo and Loudis (2023) paper available online

# # Moment estimation
# - Code to estimate risk neutral moments
# - Code to estimate physical moments

# In[11]:


# Code to estimate truncated and centered risk neutral moments, structure from Chabi-Yo and Loudis (2023)
import pandas as pd
import numpy as np
from numpy import trapezoid as integrate
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
#input_csv = r"C:\Users\Yara Staal\Downloads\Yara - Data\Filtered_RND_tau30.csv"
#moments_csv = r"C:\Users\Yara Staal\Downloads\Yara - Data\RND_raw_moments_tau30.csv"
input_csv = os.path.join(current_dir, "data", "Filtered_RND_27day.csv")
moments_csv = os.path.join(current_dir, "data", "RND_raw_moments_27day.csv")
out_dir = os.path.join(current_dir, "results","0d9_1d1_fixed_studens_param")
os.makedirs(out_dir, exist_ok=True)


scale = 1  # Annualize later; we keep moments monthly for now
# Returns on which we centralize the distribution
x_0_centers = [-0.15, 0, 0.15]
#truncation_band = 0.15
max_order = 7  # Up to 7th raw moment just to be sure; we only use the first 5 moments in the end 

#Grid of returns 
df_rnd = pd.read_csv(input_csv)
r_grid = sorted([float(col) for col in df_rnd.columns if col != "date"])
r_grid_np = np.array(r_grid) 
r_grid_str = [f"{x:.5f}" for x in r_grid]
shift = 0 # set to zero as we do not want to shift the grid 
r_shifted = r_grid_np - shift             

# Function to compute raw moments over full distribution; we follow Chabi-Yo and Loudis and use raw moments in all estimations. Moments are centered in up and down region
def full_mom(r, q_r, order, center=None):
    q_r = q_r / integrate(q_r, r)
    if center is not None:
        r = r - center
    return [integrate(q_r * r**n, r) * scale for n in range(1, order + 1)]

# Function to estimate the raw truncated moments
def trun_mom(r, q_r, lower, upper, order):
    q_r = q_r / integrate(q_r, r)
    mask = (r >= lower) & (r <= upper)
    r_trunc = r[mask]
    q_trunc = q_r[mask]
    q_trunc = q_trunc / integrate(q_trunc, r_trunc)
    return [integrate(q_trunc * r_trunc**n, r_trunc) * scale for n in range(1, order + 1)]

# Function to estimate what the probability is of entering a certain region
def trunc_probs(r, q_r, lower, upper):
    q_r = q_r / integrate(q_r, r)
    prob_down = integrate(q_r[r <= lower], r[r <= lower])
    prob_center = integrate(q_r[(r > lower) & (r <= upper)], r[(r > lower) & (r <= upper)])
    prob_up = integrate(q_r[r > upper], r[r > upper])
    return prob_down, prob_center, prob_up


moment_rows = []

for _, row in df_rnd.iterrows():
    q_vals = row[r_grid_str].values.astype(float)
    # Shift q(r) to q_shifted(r') = q(r' - shift)
    #q_shifted = np.interp(r_shifted, r_grid_np, q_vals, left=0, right=0)
    row_data = {"date": row["date"]}

    for idx, x0 in enumerate(x_0_centers):
        suffix = ["down", "center", "up"][idx]

        # Fill the total centred moments; we cut the return space into returns smaller than -0.2, between -0.2 and 0.2, above 0.2
        f_mom = full_mom(r_shifted, q_vals, max_order, center=x0)
        for n, val in enumerate(f_mom, 1):
            row_data[f"moment_{n}_untr_{suffix}"] = val

        if suffix == "down":
            lower, upper = -np.inf, -0.1
        elif suffix == "center":
            lower, upper = -0.1, 0.1
        elif suffix == "up":
            lower, upper = 0.1, np.inf

        # Filling in the truncated moments 
        trunc_moments = trun_mom(r_shifted, q_vals, lower, upper, max_order)

        for n, val in enumerate(trunc_moments, 1):
            row_data[f"moment_{n}_{suffix}"] = val

        # Fill in the probabilities 
        # prob_down, prob_center, prob_up = trunc_probs(
        #     r_shifted, q_vals, x0 - truncation_band, x0 + truncation_band
        # )
        prob_down, prob_center, prob_up = trunc_probs(
        r_shifted, q_vals, x_0_centers[0], x_0_centers[2] )
        if suffix == "down":
            row_data["prob_down"] = prob_down
        elif suffix == "center":
            row_data["prob_center"] = prob_center
        elif suffix == "up":
            row_data["prob_up"] = prob_up

    moment_rows.append(row_data)

df_moments = pd.DataFrame(moment_rows)
df_moments.to_csv(moments_csv, index=False)
# print(df_moments.head())

# We plot some days of the distribution just to see if truncation has gone right 
# import matplotlib.pyplot as plt

# n_samples = 3
# x_0_centers = [-0.15, 0.0, 0.15]
# #truncation_band = 0.15
# suffixes = ["down", "center", "up"]

# for idx in range(n_samples):
#     q_vals = df_rnd.loc[idx, r_grid_str].values.astype(float)
#     q_plot = q_vals / integrate(q_vals, r_shifted)

#     fig, ax = plt.subplots(figsize=(10, 4))
#     ax.plot(r_shifted, q_plot, label="RND", color="black")
#     colors = {"down": "red", "center": "orange", "up": "green"}

#     for i, x0 in enumerate(x_0_centers):
#         suffix = suffixes[i]
#         if suffix == "down":
#             lower, upper = -np.inf, -0.1
#         elif suffix == "center":
#             lower, upper = -0.1, 0.1
#         elif suffix == "up":
#             lower, upper = 0.1, np.inf

#         mask = (r_shifted >= lower) & (r_shifted < upper)
#         ax.fill_between(r_shifted[mask], q_plot[mask], color=colors[suffix], alpha=0.3, label=f"{suffix} region")

#     for x0 in x_0_centers:
#         ax.axvline(x0, color="gray", linestyle="--", linewidth=0.8)

#     date = df_rnd.loc[idx, "date"]
#     ax.set_title(f"RND on {date}")
#     ax.set_xlabel(" Return")
#     ax.set_ylabel("Density")
#     ax.legend(loc="upper right")
#     plt.tight_layout()
#     plt.show()



# In[12]:


# Code to estimate truncated physical moments; also some plotting to exclude some extreme dates to improve subsequent optimization
days = 27
# The student's code uses 365/30 to annualize
ANNUALIZATION_FACTOR = 365.0 / days
rw = 5         
rb = {"down": (None, -0.10), "center": (-0.10, 0.10), "up": (0.10, None)}

# Forward returns are computed in a similar way to unconditional decomposition 
def compute_returns(prices_df, dtm=30):

    df = prices_df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.floor("D")
    df["index"] = pd.to_numeric(df["index"], errors="coerce")
    df = df.dropna(subset=["date", "index"])

    # Average index per day; here we also take the average just be sure but the index for each day should be the same 
    daily_prices = df.groupby("date").agg({"index": "mean"}).reset_index().sort_values("date")

    # Reindex to full daily date range; we need to do this if we want to have 30 returns - should be redundant as in BTC all days are trading days
    full_dates = pd.date_range(start=daily_prices["date"].min(), end=daily_prices["date"].max(), freq="D")
    daily_prices = (
        daily_prices.set_index("date")
        .reindex(full_dates)
        .rename_axis("date")
        .reset_index()
        .sort_values("date") )

    # forward returns
    prices = daily_prices["index"].values
    returns = np.full_like(prices, np.nan, dtype=np.float64)

    for i in range(len(prices) - dtm):
        p_now = prices[i]
        p_future = prices[i + dtm]
        if np.isfinite(p_now) and np.isfinite(p_future) and p_now != 0:
            returns[i] = p_future / p_now - 1

    # not include last 30 days as no data there; named gross return but net returns used in the end 
    daily_prices = daily_prices.iloc[:len(prices) - dtm].copy()
    daily_prices["gross_return_30d"] = returns[:len(daily_prices)]
    return daily_prices

# Regions for truncated moments 
def region_func(R):
    if R < -0.10:
        return "down"
    elif R < 0.10:
        return "center"
    else:
        return "up"

# We compute moments per region with rolling window of 5 (as in Chabi-Yo) to reduce some extreme noise in the empirical moments. 
# Also needed for 'more' data per day -> one day can have info on multiple regions -> better for optimization later 
def phys_moments(df_returns, window=5):
    # Classify the region returns per day 
    df_returns["region"] = df_returns["gross_return_30d"].apply(region_func)
    results = []

    # Apply rolling window 
    for i in range(window - 1, len(df_returns)):
        wslice = df_returns.iloc[i - window + 1: i + 1]
        day_res = {"date": df_returns.iloc[i]["date"]}

        # Untruncated moments over all returns 
        full_returns = wslice["gross_return_30d"].dropna().values
        for n in range(1, 4):
            moment = np.mean(full_returns ** n) if len(full_returns) > 0 else np.nan
            day_res[f"moment_{n}"] = moment  # e.g., moment_1, moment_2, ...

        # Truncate moments per region
        for region, (low, high) in rb.items():
            region_returns = wslice.loc[wslice["region"] == region, "gross_return_30d"].dropna().values
            if len(region_returns) == 0:
                for n in range(1, 4):
                    day_res[f"moment_{n}_{region}"] = np.nan
                continue

            for n in range(1, 4):
                moment = np.mean(region_returns ** n)
                day_res[f"moment_{n}_{region}"] = moment

        results.append(day_res)
        #print("="*100)
        #print(f"day_res: {day_res}")
        #print("="*100)

    return pd.DataFrame(results)


# main function 
def main_phys(prices_csv_path):
    df = pd.read_csv(prices_csv_path)
    # Support Quandl format: Date, Adj.Close -> date, index
    if "date" not in df.columns and "Date" in df.columns:
        df = df.rename(columns={"Date": "date", "Adj.Close": "index"})
    df = df[["date", "index"]]
    df_returns = compute_returns(df, dtm=days)
    df_moments = phys_moments(df_returns, window=rw)
    return df_moments


btc_price_path = os.path.join(current_dir, "data", "BTC_USD_Quandl_2011_2023.csv")
df_output = main_phys(btc_price_path)
output_path = os.path.join(out_dir, "Physical_Moments_27day.csv")
df_output.to_csv(output_path, index=False)
#print(df_output.head())


# We plot the moments and exclude extreme dates based on the plot 
import matplotlib.pyplot as plt

df_prices = pd.read_csv(btc_price_path)
if "date" not in df_prices.columns and "Date" in df_prices.columns:
    df_prices = df_prices.rename(columns={"Date": "date", "Adj.Close": "index"})
df_prices = df_prices[["date", "index"]]
df_returns_raw = compute_returns(df_prices, dtm=days)
df_moments_raw = phys_moments(df_returns_raw, window=rw)

# Function to filter, we define moment limits based on the plot of the total returns 
def filter_mom(df, moment_limits):
    df_cleaned = df.copy()
    for moment, (lower, upper) in moment_limits.items():
        df_cleaned = df_cleaned[df_cleaned[moment].between(lower, upper)]
    return df_cleaned

# # thresholds 
# moment_thresholds = {
#     "moment_1": (0.5, 2.0),     
#     "moment_2": (0.0, 5.50),      
#     "moment_3": (0, 4)    
# }

# Thresholds
moment_thresholds = {
    "moment_1": (-0.5, 1.0),      
    "moment_2": (0.0, 0.50),      
    "moment_3": (-0.5, 0.5)     }

df_moments_filtered = filter_mom(df_output, moment_thresholds)

# new one saved under same name
output_path = os.path.join(current_dir, "data", "Physical_Moments_27day.csv")
df_moments_filtered.to_csv(output_path, index=False)
print(f"df_output: {df_output.head()}")

# Plot before and after filtering to check data 
fig, axes = plt.subplots(2, 1, figsize=(13, 10), sharex=True)

axes[0].plot(pd.to_datetime(df_moments_raw["date"]), df_moments_raw["moment_1"], label="1st")
axes[0].plot(pd.to_datetime(df_moments_raw["date"]), df_moments_raw["moment_2"], label="2nd")
axes[0].plot(pd.to_datetime(df_moments_raw["date"]), df_moments_raw["moment_3"], label="3rd")
axes[0].set_title(" Moments before filtering")
axes[0].legend()
axes[0].grid(True)

axes[1].plot(pd.to_datetime(df_moments_filtered["date"]), df_moments_filtered["moment_1"], label="1st")
axes[1].plot(pd.to_datetime(df_moments_filtered["date"]), df_moments_filtered["moment_2"], label="2nd")
axes[1].plot(pd.to_datetime(df_moments_filtered["date"]), df_moments_filtered["moment_3"], label="3rd")
axes[1].set_title("Moments after filtering")
axes[1].set_xlabel("Date")
axes[1].legend()
axes[1].grid(True)

plt.tight_layout()
plt.savefig(os.path.join(out_dir, "Moments_before_and_after_filtering.png"))
#plt.show()
plt.close()

# # Preference parameter estimation
# - Code with relevant functions
# - Code for multistrart optimization
# - Bootstrap 

# In[13]:


# Function without any weighting and no two-step estimation; some of the needed functions for the optimization 
from scipy.optimize import minimize
from math import comb  
import math
import pandas as pd

rnd_path = os.path.join(current_dir, "data", "RND_raw_moments_27day.csv")
phys_path = os.path.join(current_dir, "data", "Physical_Moments_27day.csv")
df_rnd = pd.read_csv(rnd_path, parse_dates=["date"])
df_phys = pd.read_csv(phys_path, parse_dates=["date"])

# Function to get theta_1, theta_2, theta_3 from preference params 
def theta_coeffs(x_s, tau, rho, kappa):
    theta_1 = 1 / (x_s * tau)
    theta_2 = (1 - rho) / (x_s**2 * tau**2)
    theta_3 = (1 - 2 * rho + kappa) / (x_s**3 * tau**3)
    return {1: theta_1, 2: theta_2, 3: theta_3}

# Function for lambda in SDF specification 
def lambda_term(k, j, x_s, theta_k):
    coeff = math.comb(k, j) 
    return coeff * theta_k * ((-1) ** j) * (x_s ** j) 

# Represents formula in Corollary 1; n is the moment order to predict; x_s is expansion point; tau, rho, kappa the preference params;
# rn_moments_trunc and rn_moments_untrunc the truncated and untruncated risk-neutral moments; max_k the maximum k used in expansion -> number of factors of the Taylor expansion
def predict_physical_moment(n, x_s, tau, rho, kappa, rn_moments_trunc,  rn_moments_untrunc,  max_k=3):
    M_star_n = rn_moments_trunc.get(n, np.nan)
    if not np.isfinite(M_star_n):
        return np.nan
    theta = theta_coeffs(x_s, tau, rho, kappa)
    numerator = 0.0
    denominator = 1.0

    for k in range(1, max_k + 1):
        theta_k = theta.get(k, 0.0)
        for j in range(0, k + 1):
            lam = lambda_term(k, j, x_s, theta_k)

            # Moment indices
            m1 = n + k - j
            m2 = k - j

            # Needed moments 
            M_star_m1_trunc = rn_moments_trunc.get(m1, np.nan)
            M_star_m2_untrunc = rn_moments_untrunc.get(m2, np.nan)
            M_star_n_trunc = M_star_n

            if not all(np.isfinite(val) for val in [M_star_m1_trunc, M_star_m2_untrunc, M_star_n_trunc]):
                continue

            # Actual function 
            numerator += lam * (M_star_m1_trunc - M_star_m2_untrunc * M_star_n_trunc)
            denominator += lam * M_star_m2_untrunc

    # Some debugging, not needed anymore because we changed expansion points 
    if abs(denominator) < 1e-6:
        return np.nan
    phys_n = M_star_n + numerator / denominator

    return phys_n

    #return M_star_n + numerator / denominator if denominator != 0 else np.nan




# In[14]:


# Code to run the optimization with multiple starting points, also possible to change the optimization method per region
import itertools
import pandas as pd
import numpy as np

rnd_path = os.path.join(current_dir, "data", "RND_raw_moments_27day.csv")
phys_path = os.path.join(current_dir, "data", "Physical_Moments_27day.csv")
df_rnd = pd.read_csv(rnd_path, parse_dates=["date"])
df_phys = pd.read_csv(phys_path, parse_dates=["date"])


# Setting to test if we need regularization of standardized errors for better optimization -> in the end off for all regions produces best results 
REGULARIZATION_BY_REGION = {
    "down": 0,   # 1e-3
    "center": 0, # 1e-5
    "up": 0      # 1e-5
}

STANDARDIZE_BY_REGION = {
    "down": False,
    "center": False, 
    "up": False }

# Centered moments, take the moment from one instead of from zero here to make sure division in theta_coeffs works 
REGION_INFO = {
    "down": {"x_s": 0.90},   # -0.1 in return
    "center": {"x_s": 1.00},
    "up": {"x_s": 1.10} }    # 0.1 in return

# If True, use loaded/specified preference parameters and skip optimization; if False, estimate from data
# When True: prefer parameters from 'Estimated_Static_Preferences_Tuned.csv' if it exists, else use FIXED_PREFERENCE_PARAMS below
USE_FIXED_PREFERENCES = True
FIXED_PREFERENCE_PARAMS = {
    "down":   {"tau": 1.55, "rho": 0.71, "kappa": 0.29},
    "center": {"tau": 2.05, "rho": 2.60, "kappa": 0.71},
    "up":     {"tau": 2.01, "rho": 2.56, "kappa": 0.00},
}

def _load_preference_params():
    """Prefer CSV (Estimated_Static_Preferences_Tuned.csv); if missing, use FIXED_PREFERENCE_PARAMS."""
    csv_path = os.path.join(out_dir, "Estimated_Static_Preferences_Tuned.csv")
    if os.path.isfile(csv_path):
        try:
            df = pd.read_csv(csv_path, index_col=0)
            required = ["tau", "rho", "kappa"]
            if all(c in df.columns for c in required) and all(r in df.index for r in REGION_INFO):
                params = {}
                for region in REGION_INFO:
                    params[region] = {
                        "tau": float(df.loc[region, "tau"]),
                        "rho": float(df.loc[region, "rho"]),
                        "kappa": float(df.loc[region, "kappa"]),
                    }
                print(f"Using preference parameters from {csv_path}")
                return params
        except Exception as e:
            print(f"Could not load {csv_path}: {e}, using FIXED_PREFERENCE_PARAMS.")
    else:
        print(f"File not found: {csv_path}, using FIXED_PREFERENCE_PARAMS.")
    return {r: FIXED_PREFERENCE_PARAMS[r].copy() for r in REGION_INFO}

# Function so we can run the optimization on each region specifically; need to make sure we only use dates that have both a physical and a risk-neutral moment
def region_data(region):
    rows = []
    for _, row_rnd in df_rnd.iterrows():
        date = row_rnd["date"]
        row_phys = df_phys[df_phys["date"] == date]
        if row_phys.empty:
            continue

        rn_trunc = {n: row_rnd.get(f"moment_{n}_{region}", np.nan) for n in range(1, 7)}
        rn_untrunc = {n: row_rnd.get(f"moment_{n}_untr_{region}", np.nan) for n in range(0, 6)}
        #physical = {n: row_phys.iloc[0].get(f"moment_{n}_{region}", np.nan) for n in range(1, 4)}
        physical = {n: row_phys.iloc[0].get(f"moment_{n}_{region}", np.nan) for n in [1, 2, 3]} 

        if all(np.isfinite(list(physical.values()))):
            rows.append({"rn_trunc": rn_trunc, "rn_untrunc": rn_untrunc, "physical": physical})
    return rows

# Loss function 
def pooled_loss(params, x_s, data, use_moments=[1, 2], lambda_reg=1e-3, standardize=True):
    tau, rho, kappa = params
    loss = 0
    count = 0

    for d in data:
        for n in use_moments:
            pred = predict_physical_moment(n, x_s, tau, rho, kappa, d["rn_trunc"], d["rn_untrunc"])
            obs = d["physical"].get(n, np.nan)

            if not (np.isfinite(pred) and np.isfinite(obs)) or abs(obs) < 1e-8:
                return 1e6

            residual = (pred - obs) / obs if standardize else (pred - obs)
            loss += residual**2
            count += 1

    if count == 0:
        return 1e6

    reg_term = lambda_reg * (tau**2 + rho**2 + kappa**2)
    return loss / count + reg_term

# We found start values change the outcome of the optimization a lot; multistart optimization. Do this one time, use best start values in bootstrap
def multistart_optimization(loss_fn, args, bounds, n_tau=3, n_rho=3, n_kappa=2):
    grid = list(itertools.product(np.linspace(0.3, 1.5, n_tau),  np.linspace(0.5, 5.0, n_rho),  np.linspace(0.5, 5.0, n_kappa)  ))

    best = None
    for i, x0 in enumerate(grid):
        res = minimize(loss_fn, x0, args=args, bounds=bounds, method="L-BFGS-B")
        if res.success and (best is None or res.fun < best.fun):
            best = res
        print(f"Start {i+1}/{len(grid)}: x0={x0}, loss={res.fun:.4f}, success={res.success}")
    return best

# main function
results = {}

if USE_FIXED_PREFERENCES:
    # Use params from CSV if available, else FIXED_PREFERENCE_PARAMS; skip optimization
    loaded = _load_preference_params()
    for region in REGION_INFO:
        results[region] = loaded[region]
    print("Using loaded/fixed preference parameters (no estimation).")
else:
    for region, meta in REGION_INFO.items():
        print(f"region: {region.upper()}")
        data = region_data(region)
        x_s = meta["x_s"]

        lambda_reg = REGULARIZATION_BY_REGION[region]
        standardize = STANDARDIZE_BY_REGION[region]

        def loss_func(params, x_s, data):
            return pooled_loss(params, x_s, data, use_moments=[1, 2], lambda_reg=lambda_reg, standardize=standardize )

        res = multistart_optimization(loss_func, args=(x_s, data), bounds=[(1e-3, 10), (0, 10), (0, 10)] )

        if res.success:
            results[region] = {
                "tau": res.x[0],
                "rho": res.x[1],
                "kappa": res.x[2],
                "loss": res.fun,
                "n_obs": len(data),
                "lambda_reg": lambda_reg,
                "standardized": standardize
            }
        else:
            results[region] = FIXED_PREFERENCE_PARAMS[region].copy()

df_est = pd.DataFrame(results).T
df_est.index.name = "region"
output_path = os.path.join(out_dir, "Estimated_Static_Preferences_Tuned.csv")
df_est.to_csv(output_path)
#print(df_est)
"""
             tau       rho     kappa      loss n_obs lambda_reg standardized
region                                                                      
down      4.6744       0.0      10.0  0.004943   533          0        False
center  0.905907   0.87876  0.218304  0.001375   813          0        False
up      2.172978  3.410214       0.0  0.011415   563          0        False
"""

# In[ ]:





# In[15]:


# Function for bootstrap so we can use median as point estimates
import matplotlib.pyplot as plt

def bootstrap_est(region, B=100, seed=42):
    np.random.seed(seed)
    regi = REGION_INFO[region]
    x_s = regi["x_s"]
    data_full = region_data(region)
    lambda_reg = REGULARIZATION_BY_REGION[region]
    standardize = STANDARDIZE_BY_REGION[region]

    # Based on multistart optimization
    # x0_dict = {
    #     "down":   [1.5, 2.75, 0.5],
    #     "center": [0.9, 2.75, 0.5],
    #     "up":     [1.5, 2.75, 0.5]
    # }
    # x0_dict = {
    #     "down":   (0.9, 2.75, 0.5),
    #     "center": (1.5, 2.75, 0.5),
    #     "up":     (1.5, 2.75, 0.5)
    #     }
    x0_dict = {
        "down":   (1.5, 0.5, 0.5),
        "center": (1.5, 2.75, 0.5),
        "up":     (1.5, 2.75, 0.5)
        }
    x0 = x0_dict[region]
    estimates = []

    # Use extended loss function to play around with regularization and standardization -> all off in the end 
    def loss_func(params):
        return pooled_loss(
            params,
            x_s,
            sample,  # changes per loop in bootstrap 
            use_moments=[1, 2],
            lambda_reg=lambda_reg,
            standardize=standardize )

    # We re-arrange the data per to see if we get the same results, run the bootstrap and save relevant metrics 
    for b in range(B):
        sample = [data_full[i] for i in np.random.choice(len(data_full), size=len(data_full), replace=True)]

        try:
            res = minimize(loss_func, x0=x0, bounds=[(1e-3, 10), (0, 10), (0, 10)], method="L-BFGS-B")
            if res.success:
                estimates.append(res.x)
        except Exception as e:
            print(f" Bootstrap failed")
            continue

    estimates = np.array(estimates)
    return {
        "tau": {
            "median": np.median(estimates[:, 0]),
            "ci_5": np.percentile(estimates[:, 0], 5),
            "ci_95": np.percentile(estimates[:, 0], 95),
            "all": estimates[:, 0]
        },
        "rho": {
            "median": np.median(estimates[:, 1]),
            "ci_5": np.percentile(estimates[:, 1], 5),
            "ci_95": np.percentile(estimates[:, 1], 95),
            "all": estimates[:, 1]
        },
        "kappa": {
            "median": np.median(estimates[:, 2]),
            "ci_5": np.percentile(estimates[:, 2], 5),
            "ci_95": np.percentile(estimates[:, 2], 95),
            "all": estimates[:, 2]
        },
        "n_successful": len(estimates),
    }


bootstrap_results = {}

# Main loop for the bootstrap
for region in REGION_INFO:
    print(f"region: {region}")
    result = bootstrap_est(region, B=10)
    bootstrap_results[region] = result

summary = []
for region, res in bootstrap_results.items():
    summary.append({
        "region": region,
        "tau_median": res["tau"]["median"],
        "tau_ci": f"[{res['tau']['ci_5']:.2f}, {res['tau']['ci_95']:.2f}]",
        "rho_median": res["rho"]["median"],
        "rho_ci": f"[{res['rho']['ci_5']:.2f}, {res['rho']['ci_95']:.2f}]",
        "kappa_median": res["kappa"]["median"],
        "kappa_ci": f"[{res['kappa']['ci_5']:.2f}, {res['kappa']['ci_95']:.2f}]",})

df_summary = pd.DataFrame(summary)
print(f"df_summary: {df_summary}")

# We also plot to see the distribution of results; in the end plain optimization produced the best bell shapes. 
try:
    import seaborn as sns
    _use_seaborn = True
except ImportError:
    _use_seaborn = False

for region, res in bootstrap_results.items():
    for param in ['tau', 'rho', 'kappa']:
        plt.figure()
        if _use_seaborn:
            sns.histplot(res[param]['all'])
        else:
            plt.hist(res[param]['all'], bins=30, edgecolor='gray', alpha=0.7)
        plt.axvline(res[param]['median'], color='red', linestyle='--', label='Median')
        plt.title(f"{param.upper()} Bootstrap Distribution – {region}")
        plt.xlabel(param)
        plt.ylabel("Frequency")
        plt.legend()
        plt.grid(True)
        plt.savefig(os.path.join(out_dir, f"{param}_Bootstrap_Distribution_{region}.png"))
        #plt.show()
        plt.close()


# # BTC return premium and VRP estimation
# - Debugging code
# - Estimation and plot of RP
# - Estimation and plot of VRP 

# In[17]:


# Function for some additional debugging on the estimated moment for the upside region 

# Same input parameters as normal predict_physical_moment function 
def predict_physical_moment_debug(n, x_s, tau, rho, kappa, rn_moments_trunc, rn_moments_untrunc, max_k=3):
    M_star_n = rn_moments_trunc.get(n, np.nan)
    if not np.isfinite(M_star_n):
        return np.nan

    theta = theta_coeffs(x_s, tau, rho, kappa)
    numerator = 0.0
    denominator = 1.0
    details = []  

    for k in range(1, max_k + 1):
        theta_k = theta.get(k, 0.0)
        for j in range(0, k + 1):
            lam = lambda_term(k, j, x_s, theta_k)
            m1 = n + k - j
            m2 = k - j

            M_star_m1_trunc = rn_moments_trunc.get(m1, np.nan)
            M_star_m2_untrunc = rn_moments_untrunc.get(m2, np.nan)
            M_star_n_trunc = M_star_n

            if not all(np.isfinite(val) for val in [M_star_m1_trunc, M_star_m2_untrunc, M_star_n_trunc]):
                continue

            term_numerator = lam * (M_star_m1_trunc - M_star_m2_untrunc * M_star_n_trunc)
            term_denominator = lam * M_star_m2_untrunc

            # Get all the info so we can see what is happening with what component; is everything being obtained right 
            details.append({
                "k": k,
                "j": j,
                "lambda": lam,
                "m1": m1,
                "m2": m2,
                "rn_m1_trunc": M_star_m1_trunc,
                "rn_m2_untrunc": M_star_m2_untrunc,
                "term_numerator": term_numerator,
                "term_denominator": term_denominator })

            numerator += term_numerator
            denominator += term_denominator

    phys_n = M_star_n - (numerator / denominator)
    #print("M_star_n", M_star_n)
    #print("numerator", numerator)
    #print("denomenator", denominator) 
    #print("correction term", (numerator / denominator))
    #print("physical moment", phys_n)
    return phys_n, details


# In[ ]:


# Code to estimate and plot decomposed RP over time 

# Preference parameters -> from estimation results or FIXED_PREFERENCE_PARAMS
region_params = {r: results[r] for r in results if results[r] is not None}

print(f"region_params: {region_params}") 
regions = ["down", "center", "up"]
x_s_values = {"down": 0.85, "center": 1.00, "up": 1.15}


result_rows = []

print(f"df_rnd: {df_rnd.head()}")

for _, row in df_rnd.iterrows():
    date = row["date"]
    row_phys = df_phys[df_phys["date"] == date]
    if row_phys.empty:
        continue

    row_result = {"date": date}

    # for each day and region we estimate the phys moment and the corresponding risk premium 
    for region in regions:
        x_s = x_s_values[region]
        tau = region_params[region]["tau"]
        rho = region_params[region]["rho"]
        kappa = region_params[region]["kappa"]

        rn_trunc = {n: row.get(f"moment_{n}_{region}", np.nan) for n in range(1, 7)}
        rn_untrunc = {n: row.get(f"moment_{n}_untr_{region}", np.nan) for n in range(0, 6)}
        rn_1 = rn_trunc.get(1, np.nan)

        # Debug for up region
        if region == "up":
            phys_1, debug_terms = predict_physical_moment_debug(1, x_s, tau, rho, kappa, rn_trunc, rn_untrunc)
            debug_df = pd.DataFrame(debug_terms)
            #print(f" Debug on {row['date']} ")
            #print(debug_df)
        else:
            phys_1 = predict_physical_moment(1, x_s, tau, rho, kappa, rn_trunc, rn_untrunc)

        # Test with global line, not used in the end (use region_params so it works with both fixed and estimated prefs)
        x_s = 1.0
        rn_trunc_total = {n: row.get(f"moment_{n}_untr_center", np.nan) for n in range(1, 7)}
        rn_untrunc_total = {n: row.get(f"moment_{n}_untr_center", np.nan) for n in range(0, 6)}
        _tau, _rho, _kappa = region_params["center"]["tau"], region_params["center"]["rho"], region_params["center"]["kappa"]
        phys_total = predict_physical_moment(1, x_s, _tau, _rho, _kappa, rn_trunc_total, rn_untrunc_total)

        # Risk premium = physical - risk-neutral
        rp_1 = phys_1 - rn_1 
        row_result[f"rn_{region}"] = rn_1
        row_result[f"phys_{region}"] = phys_1
        row_result[f"rp_{region}"] = rp_1 * ANNUALIZATION_FACTOR

    result_rows.append(row_result)

# Make total as sum of individual risk premia 
df_rp = pd.DataFrame(result_rows).sort_values("date").reset_index(drop=True)
df_rp["rp_global_sum"] = (df_rp["rp_down"] + df_rp["rp_center"] + df_rp["rp_up"])

df_rp = df_rp.iloc[2:]

# Risk premia over time
plt.figure(figsize=(10, 5))
plt.plot(df_rp["date"], df_rp["rp_global_sum"], label="Total", linewidth=2.0, color = "black")
for region in ["rp_down", "rp_center", "rp_up"]:
    plt.plot(df_rp["date"], df_rp[region], label=region.replace("rp_", "").capitalize(), alpha=0.6)
plt.axhline(0, linestyle="--", color="gray", linewidth=1)
#plt.xlabel("Date")
plt.ylabel("Bitcoin Premium")
plt.title("Bitcoin Premium Over Time")
plt.grid(True)
plt.legend(
    ncol=4,
    loc="upper center",
    bbox_to_anchor=(0.5, -0.18),
    framealpha=0.95,
)
plt.tight_layout()
plt.subplots_adjust(bottom=0.22)
plt.savefig(os.path.join(out_dir, "Risk_Premia_Over_Time.png"))
# 同图无图例版（用于排版/论文）
ax = plt.gca()
leg = ax.get_legend()
if leg is not None:
    leg.remove()
plt.tight_layout()
plt.subplots_adjust(bottom=0.12)
plt.savefig(os.path.join(out_dir, "Risk_Premia_Over_Time_no_legend.png"))
plt.close()  # 关闭第一张图，保证下一段画在新图上

# Moments over time
plt.figure(figsize=(10, 5))
for region in ["down", "center", "up"]:
    plt.plot(df_rp["date"], df_rp[f"phys_{region}"], label=f"Physical ({region})", linewidth=1.8)
    plt.plot(df_rp["date"], df_rp[f"rn_{region}"], label=f"Risk-Neutral ({region})", linestyle="--")

#plt.xlabel("Date")
plt.ylabel("First Moment")
plt.title("Physical vs Risk-Neutral Moments Over Time")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(out_dir, "Physical_vs_Risk-Neutral_Moments_Over_Time.png"))
#plt.show()
plt.close()

# Raw Bitcoin premium over time (phys moment_1 minus rn by region; no preference params; align by date)
df_rp["date"] = pd.to_datetime(df_rp["date"])
df_phys["date"] = pd.to_datetime(df_phys["date"])
df_phys_1 = df_phys[["date", "moment_1"]].copy()
df_rn_1 = df_rp[["date", "rn_down", "rn_center", "rn_up"]].copy()
df_moments_raw = pd.merge(df_rn_1, df_phys_1, on="date", how="inner")
df_moments_raw["bp_raw"] = (
    df_moments_raw["moment_1"] # 5days's average of 1st moment under physical measure E^P[R_i]
    - df_moments_raw["rn_down"]
    - df_moments_raw["rn_center"]
    - df_moments_raw["rn_up"]
)
plt.figure(figsize=(10, 5))
plt.plot(df_moments_raw["date"], df_moments_raw["bp_raw"], label="Raw Bitcoin Premium", linewidth=2.0, color="black")
plt.axhline(0, linestyle="-", color="black", linewidth=1)
#plt.xlabel("Date")
plt.ylabel("Bitcoin Premium")
plt.title("Bitcoin Premium Raw Over Time")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(out_dir, "Bitcoin_Premium_Raw_Over_Time.png"))
#plt.show()
plt.close()


# Some averages
rp_vals = {
    region: df_rp[f"rp_{region}"].mean()
    for region in ["down", "center", "up"] }
rp_total_abs = sum(abs(v) for v in rp_vals.values())

for region, val in rp_vals.items():
    share = abs(val) / rp_total_abs
    print(f"{region}: {val} | Abs Share: {share}")

# only average here 
average_rp = {
    region: df_rp[f"rp_{region}"].mean(skipna=True)
    for region in ["global_sum", "down", "center", "up"]}

for region, avg in average_rp.items():
    print(f"  {region}: {avg}")

# Making clusters based on the Q-var
df_rp["date"] = pd.to_datetime(df_rp["date"])
df_moments["date"] = pd.to_datetime(df_moments["date"])

df_varq = df_moments[["date", "moment_2_untr_center"]].copy()
df_merged = pd.merge(df_rp, df_varq, on="date", how="inner")

median_var_q = df_merged["moment_2_untr_center"].median()

df_merged["regime_qvar"] = (df_merged["moment_2_untr_center"] >= median_var_q).astype(int)

rp_columns = ["rp_down", "rp_center", "rp_up", "rp_global_sum"]

avg_rp_by_regime = df_merged.groupby("regime_qvar")[rp_columns].mean()
avg_rp_by_regime.index = ["Low q var", "High q var"]

print("Av RP per regime:")
print(avg_rp_by_regime.round(2))

# Keep a copy of RP before VRP section overwrites df_rp
df_RP = df_rp.copy()


# In[27]:


# Code for the variance risk decomposition

# Also from the bootstrap estimation -> same as above 
region_params = {r: results[r] for r in results if results[r] is not None}

print(region_params) 
regions = ["down", "center", "up"]
x_s_values = {"down": 0.85, "center": 1.0, "up": 1.15}


result_rows = []

for _, row in df_rnd.iterrows():
    date = row["date"]
    row_phys = df_phys[df_phys["date"] == date]
    if row_phys.empty:
        continue

    row_result = {"date": date}

    # We need the first and second physical moment for each day for each region
    region_moments_phys_1 = {}
    region_moments_phys_2 = {}

    for region in regions:
        x_s = x_s_values[region]
        tau = region_params[region]["tau"]
        rho = region_params[region]["rho"]
        kappa = region_params[region]["kappa"]

        rn_trunc = {n: row.get(f"moment_{n}_{region}", np.nan) for n in range(1, 7)}
        rn_untrunc = {n: row.get(f"moment_{n}_untr_{region}", np.nan) for n in range(0, 6)}
        rn_1 = rn_trunc.get(1, np.nan)
        rn_2 = rn_trunc.get(2, np.nan)

        # Debug for up region
        if region == "up":
            phys_1, debug_terms = predict_physical_moment_debug(1, x_s, tau, rho, kappa, rn_trunc, rn_untrunc)
            phys_2, debug_terms = predict_physical_moment_debug(2, x_s, tau, rho, kappa, rn_trunc, rn_untrunc)
            debug_df = pd.DataFrame(debug_terms)
            #print(f"Debug on {row['date']}")
            #print(debug_df)
        else:
            phys_1 = predict_physical_moment(1, x_s, tau, rho, kappa, rn_trunc, rn_untrunc)
            phys_2 = predict_physical_moment(2, x_s, tau, rho, kappa, rn_trunc, rn_untrunc)

        region_moments_phys_1[region] = phys_1
        region_moments_phys_2[region] = phys_2

        # We need to get some info to compute RP_2
        # First we need the estimated phys_total_1
        row_result[f"rn1_{region}"] = rn_1
        row_result[f"rn_{region}"] = rn_2       # 2nd moment of risk-neutral returns on this region E^Q[R_i^2]
        row_result[f"phys_{region}"] = phys_2 
        row_result[f"phys1_{region}"] = phys_1

    # Total physical moments as sum of regions
    phys_total_1 = sum(region_moments_phys_1[reg] for reg in regions if np.isfinite(region_moments_phys_1[reg]))
    phys_total_2 = sum(region_moments_phys_2[reg] for reg in regions if np.isfinite(region_moments_phys_2[reg]))

    # RP_2 per region
    for region in regions:
        rn_1 = row_result[f"rn1_{region}"]     # 1st moment of risk-neutral returns on this region E^Q[R_i]
        rn_2 = row_result[f"rn_{region}"]      # 2nd moment of risk-neutral returns on this region E^Q[R_i^2]
        phys_1 = region_moments_phys_1[region] # 1st moment of physical returns on this region E^P[R_i]
        phys_2 = region_moments_phys_2[region] # 2nd moment of physical returns on this region E^P[R_i^2]

        # Chabi-yo's definition of VRP is P - Q as in eq.(29) in CL23
        # we use Q - P
        if all(np.isfinite(v) for v in [phys_total_1, phys_1, phys_2, rn_2, rn_1]):
            physical_term = phys_2 - 2 * phys_total_1 * phys_1 + phys_total_1 ** 2
            # phys_2 - 2 * phys_total_1 * phys_1 + phys_total_1 ** 2 := E^P[R_i^2] - 2 * E^P[R] * E^P[R_i] + E^P[R]^2
            #                                                         = E^P[(R_i - E^P[R]) ^ 2]
            # second_term = 2 * phys_total_1 * phys_1 
            # phys_total_squared = phys_total_1 ** 2
            rp_2_moment = physical_term - rn_2
            rp_2 = - (rp_2_moment) # + phys_1 ** 2 - rn_1 ** 2) # we take the negative here as we use different definition
        else:
            rp_2 = np.nan

        row_result[f"rp_{region}"] = rp_2 * ANNUALIZATION_FACTOR  # annualized

    result_rows.append(row_result)

# Define VRP as df_rp since here
df_rp = pd.DataFrame(result_rows).sort_values("date").reset_index(drop=True)
df_rp["rp_global_sum"] = (
    df_rp["rp_down"] + df_rp["rp_center"] + df_rp["rp_up"]
)
df_rp = df_rp.iloc[2:]

# Some extremes occur due numerical instability, so we filter out these days 
threshold = 1
mask = df_rp[['rp_down', 'rp_center', 'rp_up', 'rp_global_sum']].abs().le(threshold).all(axis=1)
df_rp = df_rp[mask]

plt.figure(figsize=(10, 5))
plt.plot(df_rp["date"], df_rp["rp_global_sum"], label="Total", linewidth=2.5, color = "black")
for region in ["rp_down", "rp_center", "rp_up"]:
    plt.plot(df_rp["date"], df_rp[region], label=region.replace("rp_", "").capitalize(), alpha=0.6)

plt.axhline(0, linestyle="--", color="gray", linewidth=1)
#plt.xlabel("Date")
plt.ylabel("Variance Risk Premium")
plt.title("Variance Risk Premia Over Time")
plt.grid(True)
plt.legend(
    ncol=4,
    loc="upper center",
    bbox_to_anchor=(0.5, -0.18),
    framealpha=0.95,
)
plt.tight_layout()
plt.subplots_adjust(bottom=0.22)
plt.savefig(os.path.join(out_dir, "VRP_distribution.png"))
#plt.show()
plt.close()


# Some stats -> only average here 
average_rp = {
    region: df_rp[f"rp_{region}"].mean(skipna=True)
    for region in ["global_sum", "down", "center", "up"]}

for region, avg in average_rp.items():
    print(f"  {region}: {avg}")


# Making clusters based on the Q-var
df_rp["date"] = pd.to_datetime(df_rp["date"])
df_moments["date"] = pd.to_datetime(df_moments["date"])

df_varq = df_moments[["date", "moment_2_untr_center"]].copy()
df_merged = pd.merge(df_rp, df_varq, on="date", how="inner")

median_var_q = df_merged["moment_2_untr_center"].median()

df_merged["regime_qvar"] = (df_merged["moment_2_untr_center"] >= median_var_q).astype(int)

rp_columns = ["rp_down", "rp_center", "rp_up", "rp_global_sum"]

avg_rp_by_regime = df_merged.groupby("regime_qvar")[rp_columns].mean()
if len(avg_rp_by_regime) == 2:
    avg_rp_by_regime.index = ["Low q var", "High q var"]

print("Av VRP per regime:")
print(avg_rp_by_regime.round(3))

# Summary table: BP & VRP, unconditional + down/center/up, columns Overall / HV / LV
df_RP["date"] = pd.to_datetime(df_RP["date"])
df_RP_merged = pd.merge(df_RP, df_varq, on="date", how="inner")
df_RP_merged["regime_qvar"] = (df_RP_merged["moment_2_untr_center"] >= median_var_q).astype(int)

def _col_means(df, cols, regime_mask=None):
    if regime_mask is not None:
        df = df.loc[regime_mask]
    return [float(df[c].mean()) if c in df.columns else np.nan for c in cols]

cols = ["rp_global_sum", "rp_down", "rp_center", "rp_up"]
# Overall
bp_overall = _col_means(df_RP, cols)
vrp_overall = _col_means(df_rp, cols)
# HV = high variance (regime_qvar == 1), LV = low variance (regime_qvar == 0)
bp_hv = _col_means(df_RP_merged, cols, df_RP_merged["regime_qvar"] == 1)
bp_lv = _col_means(df_RP_merged, cols, df_RP_merged["regime_qvar"] == 0)
vrp_hv = _col_means(df_merged, cols, df_merged["regime_qvar"] == 1)
vrp_lv = _col_means(df_merged, cols, df_merged["regime_qvar"] == 0)

summary_data = [
    ("BP",      [bp_overall[0],  bp_hv[0],  bp_lv[0]]),
    ("  down",  [bp_overall[1],   bp_hv[1],  bp_lv[1]]),
    ("  center",[bp_overall[2],  bp_hv[2],  bp_lv[2]]),
    ("  up",    [bp_overall[3],   bp_hv[3],  bp_lv[3]]),
    ("VRP",     [vrp_overall[0], vrp_hv[0], vrp_lv[0]]),
    ("  down",  [vrp_overall[1], vrp_hv[1], vrp_lv[1]]),
    ("  center",[vrp_overall[2], vrp_hv[2], vrp_lv[2]]),
    ("  up",    [vrp_overall[3], vrp_hv[3], vrp_lv[3]]),
]
df_summary = pd.DataFrame(
    [row[1] for row in summary_data],
    index=[row[0] for row in summary_data],
    columns=["Overall", "HV", "LV"],
).round(3)

# Save BP, VRP, and Summary to Excel
excel_path = os.path.join(out_dir, "BP_and_VRP.xlsx")
with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
    df_RP.to_excel(writer, sheet_name="BP", index=False)
    df_rp.to_excel(writer, sheet_name="VRP", index=False)
    df_summary.to_excel(writer, sheet_name="Summary")
print(f"Saved BP, VRP, and Summary to {excel_path}")






# In[ ]:


# Code to get the SDF for each day and median based on the formula for the inverse SDF and the preference params
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from math import comb
from numpy import trapezoid as integrate

df_moments = pd.read_csv(os.path.join(current_dir, "data", "RND_raw_moments_27day.csv"))
# df_moments might not have been used 
#df_moments = pd.read_csv(r"C:\Users\Yara Staal\Downloads\Yara - Data\RND_raw_moments_tau30.csv")
df_rnd = pd.read_csv(os.path.join(current_dir, "data", "Filtered_RND_27day.csv"))
r_grid = sorted([float(col) for col in df_rnd.columns if col != "date"])
r_shifted = np.array(r_grid)
r_grid_str = [f"{x:.5f}" for x in r_grid]

# consistent with RND truncate, phys_moments(rb), REGION_INFO:  ±0.1
region_params = {r: results[r] for r in results if results[r] is not None}
x_map = {"down": 0.90, "center": 1.0, "up": 1.10}
region_bounds = {"down": (-np.inf, -0.1), "center": (-0.1, 0.1), "up": (0.1, np.inf)}

def theta_coeffs(x_s, tau, rho, kappa):
    theta_1 = 1 / (x_s * tau)
    theta_2 = (1 - rho) / (x_s**2 * tau**2)
    theta_3 = (1 - 2 * rho + kappa) / (x_s**3 * tau**3)
    return {1: theta_1, 2: theta_2, 3: theta_3}

# Function g_xs needed for inverse SDF, we assume k = 3
# the same as eq.(19) in CL23 
# R := R_{M, t\to T} - R_{f, t\to T}
# x_s := x_s - R_{f, t\to T}
def g_xs(R, x_s, theta_dict, rq_moments):
    numerator = 1.0
    denominator = 1.0
    for k in range(1, 4):
        theta = theta_dict[k]
        poly_num = sum(comb(k, j) * (-1)**j * x_s**j * R**(k - j) for j in range(k + 1))
        poly_den = sum(comb(k, j) * (-1)**j * x_s**j * rq_moments[k - j - 1] for j in range(k + 1))
        numerator += theta * poly_num
        denominator += theta * poly_den
    return numerator / denominator


sdf_matrix = []

plt.figure(figsize=(10, 5))

# Define the inverse SDF for each day
for idx, row in df_moments.iterrows():
    q_vals = df_rnd.loc[idx, r_grid_str].values.astype(float)
    q_vals = q_vals / integrate(q_vals, r_shifted)

    inverse_sdf = []
    for R in r_shifted:
        # r_shifted := -1:0.01:1
        for region, x_s in x_map.items():
            # x_map = {"down": 0.75, "center": 1.0, "up": 1.25}
            lower, upper = region_bounds[region]
            if lower < R <= upper:
                params = region_params[region]
                theta_dict = theta_coeffs(x_s, params["tau"], params["rho"], params["kappa"])
                rq_moments = [row[f"moment_{k}_untr_center"] for k in range(1, 4)]
                g_val = g_xs(R, x_s, theta_dict, rq_moments)
                inverse_sdf.append(g_val)
                break

    inverse_sdf = np.array(inverse_sdf)
    # From inverse to normal
    sdf = 1 / inverse_sdf
    sdf = sdf / integrate(sdf * q_vals, r_shifted)
    sdf_matrix.append(sdf)

    plt.plot(r_shifted, sdf, color='grey', alpha=0.4, linewidth=0.7)

sdf_matrix = np.array(sdf_matrix)
sdf_median = np.median(sdf_matrix, axis=0)
plt.plot(r_shifted, sdf_median, color='red', linewidth=1.5, label='Median SDF')
plt.title("-")
plt.xlabel("Return (R)")
plt.grid(True, linestyle='--', alpha=0.5)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(out_dir, "SDF_distribution.png"))
#plt.show()
plt.close()


# In[ ]:




