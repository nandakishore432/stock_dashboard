import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import time
from utils import get_stock_data, get_info, TICKERS

# ── Page Config ──────────────────────────────────────────────────────
st.set_page_config(page_title='Stock Dashboard', layout='wide', page_icon='📈')
st.title('📈 Live Stock Price Dashboard')
st.caption(f'Auto-refreshes every 30 minutes. Last run: {pd.Timestamp.now().strftime("%H:%M:%S")}')

# ── The "No-Fail" CSS ────────────────────────────────────────────────
# This targets Streamlit's internal div structure directly
st.markdown(
    """
    <style>
    /* 1. Page Background */
    .stApp { background-color: #f0f2f6; }

    /* 2. Target every Streamlit Block to create the Card effect */
    /* This ensures the border is actually AROUND the content */
    [data-testid="stVerticalBlock"] > div:has(div.stPlotlyChart),
    [data-testid="stVerticalBlock"] > div:has(div[data-testid="metric-container"]) {
        background-color: white;
        border: 2px solid #2d3436; /* Your 2px thickness requirement */
        border-radius: 15px;      /* Your rounded requirement */
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }

    /* 3. Color variants for specific charts */
    /* We use nth-of-type to color individual containers since we can't label them easily */
    .main .block-container > div:nth-of-type(2) { background-color: #ffffff; } /* KPI */
    .main .block-container > div:nth-of-type(3) { background-color: #fef6e4; } /* Line Chart */

    /* 4. Formatting Titles */
    .custom-title {
        font-weight: 800;
        font-size: 1.2rem;
        color: #1a1a2e;
        margin-bottom: 10px;
        border-bottom: 1px solid #eee;
        padding-bottom: 5px;
    }
    </style>
    """, 
    unsafe_allow_html=True
)

# ── Sidebar Controls ─────────────────────────────────────────────────
with st.sidebar:
    st.header('Controls')
    selected = st.multiselect('Select Tickers', TICKERS, default=['AAPL','MSFT','TSLA'])
    period   = st.selectbox('Period', ['7d','14d','30d','90d'], index=2)
    interval = st.selectbox('Interval', ['1d','1h','5m'], index=0)
    refresh  = st.slider('Auto-refresh (min)', 5, 60, 30)
    st.divider()
    st.caption('Data: Yahoo Finance (yfinance)')

# ── Load Data ────────────────────────────────────────────────────────
@st.cache_data(ttl=refresh*60)
def load_all(tickers, period, interval):
    return {t: get_stock_data(t, period, interval) for t in tickers}

with st.spinner('Fetching live data...'):
    data = load_all(tuple(selected), period, interval)

# ── KPI Row ──────────────────────────────────────────────────────────
kpi_cols = st.columns(len(selected))
for i, sym in enumerate(selected):
    df  = data[sym]
    cur = df['Close'].iloc[-1]
    prv = df['Close'].iloc[-2]
    chg = cur - prv
    pct = chg / prv * 100
    vol = df['Volatility'].iloc[-1]
    kpi_cols[i].metric(
        label=sym,
        value=f'${cur:.2f}',
        delta=f'{chg:+.2f} ({pct:+.2f}%)',
        delta_color='normal'
    )

st.divider()

# ── Chart 1: Line — 30-Day Price Trend ───────────────────────────────
st.subheader('30-Day Closing Price Trend')
fig_line = go.Figure()
for sym in selected:
    df = data[sym]
    fig_line.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name=sym))
    fig_line.add_trace(go.Scatter(x=df.index, y=df['7D_Avg'], mode='lines',
        name=f'{sym} 7D Avg', line=dict(dash='dot', width=1)))
fig_line.update_layout(hovermode='x unified', height=380)
st.plotly_chart(fig_line, use_container_width=True)

# ── Chart 2: Candlestick — OHLC ──────────────────────────────────────
st.subheader('Candlestick Chart (OHLC)')
cs_sym = st.selectbox('Select ticker for candlestick', selected, key='cs')
df_cs = data[cs_sym]
fig_cs = go.Figure(go.Candlestick(
    x=df_cs.index, open=df_cs['Open'], high=df_cs['High'],
    low=df_cs['Low'], close=df_cs['Close'], name=cs_sym),
)
fig_cs.update_layout(xaxis_rangeslider_visible=False, height=360)
st.plotly_chart(fig_cs, use_container_width=True)

# ── Charts Row: Bar + Scatter ─────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader('Daily Return % (Bar Chart)')
    all_df = pd.concat([data[s] for s in selected])
    fig_bar = px.bar(all_df.reset_index(), x='Date', y='Daily_Return',
                     color='Symbol', barmode='group',
                     color_discrete_sequence=px.colors.qualitative.Set2)
    fig_bar.update_layout(height=320)
    st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    st.subheader('Volatility vs Return (Scatter)')
    summary = pd.DataFrame([{
        'Symbol': s,
        'Avg_Return': data[s]['Daily_Return'].mean(),
        'Volatility': data[s]['Volatility'].mean(),
        'Avg_Volume': data[s]['Volume'].mean()
    } for s in selected])
    fig_sc = px.scatter(summary, x='Volatility', y='Avg_Return', text='Symbol',
                        size='Avg_Volume', color='Symbol',
                        color_discrete_sequence=px.colors.qualitative.Pastel)
    fig_sc.update_traces(textposition='top center')
    fig_sc.update_layout(height=320)
    st.plotly_chart(fig_sc, use_container_width=True)

# ── Chart: Area — Volume ──────────────────────────────────────────────
st.subheader('Volume Over Time (Area Chart)')
fig_area = go.Figure()
for sym in selected:
    df = data[sym]
    fig_area.add_trace(go.Scatter(x=df.index, y=df['Volume'], fill='tozeroy',
                                  name=sym, mode='lines'))
fig_area.update_layout(height=300)
st.plotly_chart(fig_area, use_container_width=True)

# ── Chart: Heatmap — Weekly Return ───────────────────────────────────
st.subheader('Return Heatmap (by Day)')
hm_sym = st.selectbox('Ticker for heatmap', selected, key='hm')
df_hm = data[hm_sym].copy()
df_hm['DayName'] = df_hm.index.strftime('%a')
df_hm['Week']    = df_hm.index.isocalendar().week.values
pivot = df_hm.pivot_table(values='Daily_Return', index='DayName', columns='Week', aggfunc='mean')
fig_hm = px.imshow(pivot, color_continuous_scale='RdYlGn', aspect='auto',
                   labels={'color':'Return %'})
fig_hm.update_layout(height=280)
st.plotly_chart(fig_hm, use_container_width=True)

# ── Anomaly Alerts Table ─────────────────────────────────────────────
st.subheader('Anomaly Alerts (Z-Score > 2)')
alerts = []
for sym in selected:
    df = data[sym].copy()
    df['Z'] = (df['Daily_Return'] - df['Daily_Return'].mean()) / df['Daily_Return'].std()
    flagged = df[abs(df['Z']) > 2][['Close','Daily_Return','Z']].copy()
    flagged['Symbol'] = sym
    flagged['Signal'] = flagged['Daily_Return'].apply(lambda x: '🔺 Surge' if x>0 else '🔻 Drop')
    alerts.append(flagged)
if alerts:
    result = pd.concat(alerts).sort_index(ascending=False).head(20)
    st.dataframe(result[['Symbol','Close','Daily_Return','Z','Signal']],
                 use_container_width=True)
else:
    st.success('No anomalies detected in the selected period.')

# ── Auto-refresh ──────────────────────────────────────────────────────
st.divider()
if st.button('🔄 Refresh Now'):
    st.cache_data.clear()
    st.rerun()
time.sleep(refresh * 60)
st.rerun()
