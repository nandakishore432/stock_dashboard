import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import yfinance as yf
import time

# ── Page Config ───────────────────────────────────────────────────────
st.set_page_config(
    page_title='Stock Analytics Dashboard',
    layout='wide',
    initial_sidebar_state="expanded",
    page_icon='📈'
)

# ── Global CSS & Styling ──────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* 1. Page Background */
    .stApp {
        background-color: #f0f2f6;
    }

    /* 2. Main Card Wrapper */
    .chart-card {
        border: 2px solid #d1d1d1;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 25px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
    }

    /* 3. Specific Background Colors */
    .card-kpi     { background-color: #ffffff; border-color: #2d3436; }
    .card-line    { background-color: #fef6e4; border-color: #f3d0a7; }
    .card-candle  { background-color: #e8f8f0; border-color: #b2d8c3; }
    .card-bar     { background-color: #f4e8ff; border-color: #d1b3ff; }
    .card-scatter { background-color: #fff3e0; border-color: #ffcc80; }
    .card-volume  { background-color: #e8eeff; border-color: #b3c7ff; }
    .card-heatmap { background-color: #fffde7; border-color: #fff176; }
    .card-anomaly { background-color: #fff5f5; border-color: #feb2b2; }

    /* 4. Title Styling */
    .card-title {
        font-size: 1.15rem;
        font-weight: 800;
        color: #1a1a2e;
        margin-bottom: 15px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* 5. Metric Container Fix */
    div[data-testid="metric-container"] {
        background-color: rgba(255, 255, 255, 0.6);
        border: 1px solid #eee;
        border-radius: 10px;
        padding: 10px;
    }
    </style>
    """, 
    unsafe_allow_html=True
)

# ── Constants & Data ──────────────────────────────────────────────────
TICKERS = ['AAPL', 'MSFT', 'TSLA', 'GOOGL', 'AMZN', 'META', 'NVDA', 'NFLX']

def get_stock_data(ticker, period='30d', interval='1d'):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna(subset=['Close'])
        df['Symbol'] = ticker
        df['Daily_Return'] = df['Close'].pct_change() * 100
        df['Volatility'] = df['Daily_Return'].rolling(7, min_periods=1).std()
        df['7D_Avg'] = df['Close'].rolling(7, min_periods=1).mean()
        return df
    except:
        return pd.DataFrame()

# ── Sidebar ───────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Settings")
    selected = st.multiselect('Tickers', TICKERS, default=['AAPL', 'MSFT', 'TSLA', 'NFLX'])
    period = st.selectbox('Period', ['7d', '14d', '30d', '90d'], index=2)
    refresh = st.slider('Auto-refresh (min)', 5, 60, 30)

@st.cache_data(ttl=refresh * 60)
def load_all(tickers, period):
    return {t: get_stock_data(t, period) for t in tickers}

data = load_all(tuple(selected), period)

# ── Dashboard Layout ──────────────────────────────────────────────────
st.title('📈 Real-Time Stock Analytics')

# 1. MARKET OVERVIEW (KPIs)
st.markdown('<div class="chart-card card-kpi">', unsafe_allow_html=True)
st.markdown('<div class="card-title">📊 Market Overview</div>', unsafe_allow_html=True)
k_cols = st.columns(len(selected))
for i, s in enumerate(selected):
    df = data[s]
    if not df.empty:
        curr, prev = df['Close'].iloc[-1], df['Close'].iloc[-2]
        k_cols[i].metric(s, f"${curr:.2f}", f"{(curr-prev)/prev*100:+.2f}%")
st.markdown('</div>', unsafe_allow_html=True)

# 2. PRICE TREND
st.markdown('<div class="chart-card card-line">', unsafe_allow_html=True)
st.markdown('<div class="card-title">📈 Price Action & 7D Moving Average</div>', unsafe_allow_html=True)
fig_line = go.Figure()
for s in selected:
    df = data[s]
    fig_line.add_trace(go.Scatter(x=df.index, y=df['Close'], name=s, line=dict(width=2.5)))
fig_line.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig_line, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# 3. CANDLESTICK & HEATMAP (Side by Side)
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="chart-card card-candle">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">🕯️ Candlestick Analysis</div>', unsafe_allow_html=True)
    focus = st.selectbox("Focus Ticker", selected, key="focus_candle")
    df_c = data[focus]
    fig_c = go.Figure(go.Candlestick(x=df_c.index, open=df_c['Open'], high=df_c['High'], low=df_c['Low'], close=df_c['Close']))
    fig_c.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_c, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="chart-card card-bar">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📊 Daily Returns Comparison</div>', unsafe_allow_html=True)
    all_df = pd.concat([data[s] for s in selected])
    fig_bar = px.bar(all_df.reset_index(), x='Date', y='Daily_Return', color='Symbol', barmode='group')
    fig_bar.update_layout(height=335, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig_bar, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── Auto-Refresh ──────────────────────────────────────────────────────
time.sleep(refresh * 60)
st.rerun()
