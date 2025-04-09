import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz
import numpy as np

# Asset mappings to their respective tickers
ASSET_MAPPINGS = {
    "Bitcoin": "BTC-USD",
    "MSTR": "MSTR",
    "S&P 500": "^GSPC",
    "Gold": "GC=F",
    "Cash": "USD"
}

def fetch_stock_data(tickers, start_date, end_date):
    """Fetch historical stock data using yfinance"""
    data = {}
    for ticker in tickers:
        if ticker == "USD":
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
    tz = pytz.UTC
    start_date = start_date.replace(tzinfo=tz)
    end_date = end_date.replace(tzinfo=tz)
    
    if ticker == "USD":
        # For cash, create dates based on frequency directly
        if frequency == "Daily":
            dates = pd.date_range(start=start_date, end=end_date, freq='D', tz=tz)
        elif frequency == "Weekly":
            dates = pd.date_range(start=start_date, end=end_date, freq='W-MON', tz=tz)
        else:  # Monthly
            dates = pd.date_range(start=start_date, end=end_date, freq='M', tz=tz)
        df = pd.DataFrame(index=dates)
        df['USD'] = 1.0
    else:
        df = data[[ticker]].copy()
    
    # Resample based on frequency (for non-cash assets)
    if ticker != "USD":
        if frequency == "Daily":
            df_resampled = df
        elif frequency == "Weekly":
            df_resampled = df.resample('W-MON').mean()
        else:  # Monthly
            df_resampled = df.resample('M').mean()
    else:
        df_resampled = df
    
    # Calculate shares bought and total investment
    df_resampled['Shares'] = amount / df_resampled[ticker]
    df_resampled['Cumulative_Shares'] = df_resampled['Shares'].cumsum()
    
    # For cash, Total_Invested should exactly match the number of periods * amount
    if ticker == "USD":
        # Use the length of the DataFrame to determine number of periods
        periods = np.arange(1, len(df_resampled) + 1)
        df_resampled['Total_Invested'] = amount * periods
    else:
        time_deltas = (df_resampled.index - start_date).days
        if frequency == "Weekly":
            df_resampled['Total_Invested'] = amount * (time_deltas // 7)
        else:  # Monthly
            df_resampled['Total_Invested'] = amount * (time_deltas // 30)
    
    df_resampled['Portfolio_Value'] = (
        df_resampled['Cumulative_Shares'] if ticker == "USD" 
        else df_resampled['Cumulative_Shares'] * df_resampled[ticker]
    )
    
    return df_resampled

def main():
    st.title("DCA Comparison Tool")
    
    # Sidebar configuration
    st.sidebar.header("DCA Parameters")
    
    # Asset selection
    selected_assets = []
    st.sidebar.subheader("Select Assets")
    for asset in ASSET_MAPPINGS.keys():
        if st.sidebar.checkbox(asset, value=(asset in ["Bitcoin", "S&P 500", "Cash"])):
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
        ["Weekly", "Monthly"]
    )
    
    # Automatic analysis
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
                    frequency, start_date, end_date
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
                        f'{asset} Value: $%{{y:.2f}}<br>' +
                        'Shares: %{customdata:.4f}<br>',
                        customdata=df['Cumulative_Shares'],
                        line=dict(width=3)
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df['Total_Invested'],
                        name=f"{asset} Invested",
                        line=dict(dash='dash', width=3),
                        opacity=0.5
                    )
                )
            
            fig.update_layout(
                title=dict(
                    text=f"DCA Comparison ({frequency} ${investment_amount} investments)",
                    font=dict(size=24)
                ),
                xaxis_title=dict(
                    text="Date",
                    font=dict(size=18)
                ),
                yaxis_title=dict(
                    text="Value ($)",
                    font=dict(size=18)
                ),
                legend_title=dict(
                    text="Assets",
                    font=dict(size=16)
                ),
                legend=dict(
                    font=dict(size=14)
                ),
                hovermode="x unified",
                width=1000,
                height=600,
                font=dict(size=14),
                hoverlabel=dict(font_size=14)
            )
            
            fig.update_xaxes(tickfont=dict(size=14))
            fig.update_yaxes(tickfont=dict(size=14))
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Display summary statistics
            st.subheader("Summary Statistics")
            summary_data = {}
            for asset, df in results.items():
                ticker = ASSET_MAPPINGS[asset]
                final_value = df['Portfolio_Value'].iloc[-1]
                total_invested = df['Total_Invested'].iloc[-1]
                summary_data[asset] = {
                    'Final Value': final_value,
                    'Total Invested': total_invested,
                    'Gain': final_value - total_invested,
                    'ROI (%)': ((final_value / total_invested) - 1) * 100 if ticker != "USD" else 0.0
                }
            
            st.dataframe(
                pd.DataFrame(summary_data).T.style.format({
                    'Final Value': '${:,.2f}',
                    'Total Invested': '${:,.2f}',
                    'Gain': '${:,.2f}',
                    'ROI (%)': '{:.2f}%'
                })
            )

if __name__ == "__main__":
    main()
