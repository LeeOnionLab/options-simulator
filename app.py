import streamlit as st
import numpy as np
import plotly.graph_objects as go
from scipy.stats import norm

# --- BLACK-SCHOLES & GREEKS FORMULAS ---
def bsm_greeks(S, K, T, r, sigma, option_type="call"):
    """Calculate price and Greeks for a single option leg."""
    if T <= 0:
        T = 1e-5  # Prevent division by zero close to expiry
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type == "call":
        price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        delta = norm.cdf(d1)
        theta = (- (S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) 
                 - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
    else: # put
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        delta = norm.cdf(d1) - 1
        theta = (- (S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) 
                 + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365
        
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    vega = (S * norm.pdf(d1) * np.sqrt(T)) / 100 # Per 1% change in IV
    
    return {"price": price, "delta": delta, "gamma": gamma, "theta": theta, "vega": vega}

# --- APPLAYOUT ---
st.set_page_config(layout="wide", page_title="Options Greeks Workspace")
st.title("📊 Visual Options Strategy & Greeks Machine")

# --- SIDEBAR CONTROL PANEL ---
st.sidebar.header("1. Global Parameters")
underlying = st.sidebar.number_input("Current Stock Price ($)", value=100.0, step=1.0)
iv = st.sidebar.slider("Implied Volatility (IV %)", min_value=5, max_value=150, value=30) / 100.0
days_to_expiry = st.sidebar.slider("Days to Expiration (DTE)", min_value=1, max_value=365, value=30)
view_mode = st.sidebar.radio("Select View Profile", ["P&L at Expiration", "Delta Profile", "Gamma Profile", "Theta Profile", "Vega Profile"])

st.sidebar.header("2. Strategy Layout")
strategy = st.sidebar.selectbox("Strategy Setup", ["Iron Condor", "Long Butterfly"])

# Generate stock price range for the X-axis
sT = np.linspace(underlying * 0.7, underlying * 1.3, 500)
net_profile = np.zeros_like(sT)
T = days_to_expiry / 365.0
r = 0.05 # 5% Risk-free interest rate

# --- STRATEGY COMPILER ---
legs = []
if strategy == "Iron Condor":
    # Structuring standard 4 legs for an IC centered around the stock price
    legs = [
        {"strike": underlying - 10, "type": "put", "pos": "long", "prem": 0.5},
        {"strike": underlying - 5, "type": "put", "pos": "short", "prem": 1.5},
        {"strike": underlying + 5, "type": "call", "pos": "short", "prem": 1.5},
        {"strike": underlying + 10, "type": "call", "pos": "long", "prem": 0.5}
    ]
elif strategy == "Long Butterfly":
    legs = [
        {"strike": underlying - 5, "type": "call", "pos": "long", "prem": 5.0},
        {"strike": underlying, "type": "call", "pos": "short", "prem": 2.5},
        {"strike": underlying, "type": "call", "pos": "short", "prem": 2.5},
        {"strike": underlying + 5, "type": "call", "pos": "long", "prem": 1.0}
    ]

# Calculate chosen metric across the whole price array
for i, price_point in enumerate(sT):
    total_val = 0
    for leg in legs:
        greeks = bsm_greeks(price_point, leg["strike"], T, r, iv, leg["type"])
        mult = 1 if leg["pos"] == "long" else -1
        
        if view_mode == "P&L at Expiration":
            # Simple expiration P&L logic
            if leg["type"] == "call":
                payoff = np.maximum(price_point - leg["strike"], 0) - leg["prem"]
            else:
                payoff = np.maximum(leg["strike"] - price_point, 0) - leg["prem"]
            total_val += payoff * mult
        else:
            # Map out selected Greek
            metric_key = view_mode.split()[0].lower() # extracts 'delta', 'gamma', etc.
            total_val += greeks[metric_key] * mult
            
    net_profile[i] = total_val

# --- GRAPH RENDERING ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=sT, y=net_profile, mode='lines', line=dict(color='#00FFCC', width=3), name=view_mode))

# Formatting aesthetics
fig.add_vline(x=underlying, line_dash="dash", line_color="yellow", annotation_text="Current Price")
fig.update_layout(
    title=f"Strategy {view_mode} Curve",
    xaxis_title="Stock Price ($)",
    yaxis_title=view_mode,
    template="plotly_dark"
)
st.plotly_chart(fig, use_container_width=True)
