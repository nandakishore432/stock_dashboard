import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import yfinance as yf
import time

# ── Constants ─────────────────────────────────────────────────────────
TICKERS = ['AAPL', 'MSFT', 'TSLA', 'GOOGL', 'AMZN', 'META', 'NVDA', 'NFLX']

# ── Data Utilities ────────────────────────────────────────────────────
def get_stock_data(ticker: str, period: str = '30d', interval: str = '1d') -> pd.DataFrame:
    df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna(subset=['Close'])
    if df.empty: return df
    df.index.name = 'Date'
    df['Symbol'] = ticker
    df['Daily_Return'] = df['Close'].pct_change() * 100
    df['Volatility']   = df['Daily_Return'].rolling(7, min_periods=1).std()
    df['7D_Avg']       = df['Close'].rolling(7, min_periods=1).mean()
    return df

# ── Page Config ───────────────────────────────────────────────────────
st.set_page_config(page_title='Stock Dashboard', layout='wide', initial_sidebar_state="expanded", page_icon='📈')

# ── Enhanced Global CSS ───────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* 1. Page Background Color */
    .stApp {
        background-color: #f8f9fa;
    }

    /* 2. Rounded Borders & Spacing for Chart Cards */
    .chart-card {
        border: 2px solid #e0e0e0;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }

    /* Specific Card Colors */
    .card-kpi     { background-color: #ffffff; border-color: #000000; } 
    .card-line    { background-color: #fef6e4; border-color: #f3d0a7; }
    .card-candle  { background-color: #e8f8f0; border-color: #b2d8c3; }
    .card-bar     { background-color: #f4e8ff; border-color: #d1b3ff; }
    .card-scatter { background-color: #fff3e0; border-color: #ffcc80; }
    .card-volume  { background-color: #e8eeff; border-color: #b3c7ff; }
    .card-heatmap { background-color: #fffde7; border-color: #fff176; }
    .card-anomaly { background-color: #fff5f5; border-color: #feb2b2; }

    /* KPI metric containers */
    div[data-testid="metric-container"] {
        border: 1px solid #d1d1d1 !important;
        border-radius: 10px !important;
        padding: 10px !important;
        background-color: #ffffff !important;
    }

    .card-title {
        font-size: 1.2rem;
        font-weight: 800;
        color: #2d3436;
        margin-bottom: 15px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    </style>
    """, 
    unsafe_allow_html=True
)

st.title('📈 Live Stock Price Dashboard')

# ── Sidebar Controls ──────────────────────────────────────────────────
with st.sidebar:
    st.header('Controls')
    selected = st.multiselect('Select Tickers', TICKERS, default=['AAPL', 'MSFT', 'TSLA'])
    period   = st.selectbox('Period', ['7d', '14d', '30d', '90d'], index=2)
    interval = st.selectbox('Interval', ['1d', '1h', '5m'], index=0)
    refresh  = st.slider('Auto-refresh (min)', 5, 60, 30)

@st.cache_data(ttl=refresh * 60)
def load_all(tickers, period, interval):
    return {t: get_stock_data(t, period, interval) for t in tickers}

with st.spinner('Fetching live data...'):
    data = load_all(tuple(selected), period, interval)

# ── KPI Row ───────────────────────────────────────────────────────────
st.markdown('<div class="chart-card card-kpi">', unsafe_allow_html=True)
st.markdown('<div class="card-title">📊 Market Overview</div>', unsafe_allow_html=True)
cols = st.columns(len(selected))
for i, sym in enumerate(selected):
    df = data[sym]
    if not df.empty and len(df) >= 2:
        cur, prv = df['Close'].iloc[-1], df['Close'].iloc[-2]
        cols[i].metric(label=sym, value=f'${cur:.2f}', delta=f'{(cur-prv)/prv*100:+.2f}%')
st.markdown('</div>', unsafe_allow_html=True)

# ── Chart 1: Line Chart ───────────────────────────────────────────────
st.markdown('<div class="chart-card card-line">', unsafe_allow_html=True)
st.markdown('<div class="card-title">📈 Price Action & 7D Moving Average</div>', unsafe_allow_html=True)
fig_line = go.Figure()
for sym in selected:
    df = data[sym]
    fig_line.add_trace(go.Scatter(x=df.index, y=df['Close'], name=sym, line=dict(width=3)))
fig_line.update_layout(
    hovermode='x unified', height=400,
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=0, r=0, t=0, b=0)
)
st.plotly_chart(fig_line, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# ── Chart 2: Candlestick ──────────────────────────────────────────────
st.markdown('<div class="chart-card card-candle">', unsafe_allow_html=True)
st.markdown('<div class="card-title">🕯️ Technical Analysis (OHLC)</div>', unsafe_allow_html=True)
cs_sym = st.selectbox('Ticker focus', selected)
df_cs = data[cs_sym]
fig_cs = go.Figure(go.Candlestick(x=df_cs.index, open=df_cs['Open'], high=df_cs['High'], low=df_cs['Low'], close=df_cs['Close']))
fig_cs.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_rangeslider_visible=False)
st.plotly_chart(fig_cs, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# ── Charts Row: Bar + Scatter ─────────────────────────────────────────
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="chart-card card-bar">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📊 Daily Returns</div>', unsafe_allow_html=True)
    all_df = pd.concat([data[s] for s in selected])
    fig_bar = px.bar(all_df.reset_index(), x='Date', y='Daily_Return', color='Symbol', barmode='group', color_discrete_sequence=px.colors.qualitative.Bold)
    fig_bar.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_bar, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="chart-card card-scatter">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">🔵 Volatility vs Performance</div>', unsafe_allow_html=True)
    summary = pd.DataFrame([{ 'Symbol': s, 'Return': data[s]['Daily_Return'].mean(), 'Volatility': data[s]['Volatility'].mean() } for s in selected])
    fig_sc = px.scatter(summary, x='Volatility', y='Return', text='Symbol', color='Symbol', size_max=60)
    fig_sc.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_sc, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── Auto-refresh Logic ───────────────────────────────────────────────
time.sleep(refresh * 60)
st.rerun()
