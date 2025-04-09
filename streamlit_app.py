import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz

# Asset mappings to their respective tickers
ASSET_MAPPINGS = {
    "Bitcoin": "BTC-USD",
    "MSTR": "MSTR",
    "S&P 500": "^GSPC",
    "Gold": "GC=F",
    "Cash": "USD"  # Special case - will be handled separately
}

def fetch_stock_data(tickers, start_date, end_date):
    """Fetch historical stock data using yfinance"""
    data = {}
    for ticker in tickers:
        if ticker == "USD":  # Handle cash separately
            continue
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(start=start_date, end=end_date)
            data[ticker] = df['Close']
        except Exception as e:
            st.error(f"Error fetching data for {ticker}: {str(e)}")
    return pd.DataFrame(data)

def calculate_dca(asset, ticker, data, amount, frequency, start_date, end_date):
    """Calculate Dollar Cost Averaging returns"""
    # Ensure timezone consistency
    tz = pytz.UTC
    start_date = start_date.replace(tzinfo=tz)
    end_date = end_date.replace(tzinfo=tz)
    
    if ticker == "USD":  # Handle capitalism
        dates = pd.date_range(start=start_date, end=end_date, freq='D', tz=tz)
        df = pd.DataFrame(index=dates)
        df['USD'] = 1.0  # Cash value remains constant
    else:
        df = data[[ticker]].copy()
    
    # Resample based on frequency
    if frequency == "Daily":
        df_resampled = df
    elif frequency == "Weekly":
        df_resampled = df.resample('W-MON').mean()
    else:  # Monthly
        df_resampled = df.resample('M').mean()
    
    # Calculate shares bought and total investment
    df_resampled['Shares'] = amount / df_resampled[ticker]
    df_resampled['Cumulative_Shares'] = df_resampled['Shares'].cumsum()
    
    # Calculate number of periods based on frequency
    time_deltas = (df_resampled.index - start_date).days
    if frequency == "Daily":
        df_resampled['Total_Invested'] = amount * time_deltas
    elif frequency == "Weekly":
        df_resampled['Total_Invested'] = amount * (time_deltas // 7)
    else:  # Monthly
        df_resampled['Total_Invested'] = amount * (time_deltas // 30)
    
    df_resampled['Portfolio_Value'] = (
        df_resampled['Cumulative_Shares'] if ticker == "USD" 
        else df_resampled['Cumulative_Shares'] * df_resampled[ticker]
    )
    
    return df_resampled

def main():
    st.title("Dollar Cost Averaging Comparison Tool")
    
    # Sidebar configuration
    st.sidebar.header("DCA Parameters")
    
    # Asset selection
    selected_assets = []
    st.sidebar.subheader("Select Assets")
    for asset in ASSET_MAPPINGS.keys():
        if st.sidebar.checkbox(asset, value=(asset in ["Bitcoin", "S&P 500"])):
            selected_assets.append(asset)
    
    if not selected_assets:
        st.warning("Please select at least one asset")
        return
    
    # Date selection
    default_start = datetime(2020, 1, 1)
    start_date = st.sidebar.date_input(
        "Start Date",
        value=default_start,
        min_value=datetime(2000, 1, 1),
        max_value=datetime.now() - timedelta(days=1)
    )
    end_date = datetime.now()
    
    # Convert to datetime objects if they aren't already
    if not isinstance(start_date, datetime):
        start_date = datetime.combine(start_date, datetime.min.time())
    if not isinstance(end_date, datetime):
        end_date = datetime.combine(end_date, datetime.min.time())
    
    # Investment parameters
    investment_amount = st.sidebar.number_input(
        "Investment amount per period ($)", 
        min_value=10.0, 
        value=100.0, 
        step=10.0
    )
    
    frequency = st.sidebar.selectbox(
        "Investment frequency",
        ["Daily", "Weekly", "Monthly"]
    )
    
    # Fetch data and run analysis
    if st.sidebar.button("Run Analysis"):
        with st.spinner("Fetching data and calculating..."):
            tickers = [ASSET_MAPPINGS[asset] for asset in selected_assets]
            data = fetch_stock_data(tickers, start_date, end_date)
            
            if not data.empty or "USD" in tickers:
                # Calculate DCA for each asset
                results = {}
                for asset in selected_assets:
                    ticker = ASSET_MAPPINGS[asset]
                    results[asset] = calculate_dca(
                        asset, ticker, data, investment_amount, 
                        frequency, start робота_date, end_date
                    )
                
                # Create visualization
                fig = go.Figure()
                
                for asset, df in results.items():
                    ticker = ASSET_MAPPINGS[asset]
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df['Portfolio_Value'],
                            name=f"{asset} Value",
                            hovertemplate=
                            '<b>%{x}</b><br>' +
                            f'{asset}
