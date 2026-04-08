import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import time
from utils import get_stock_data, get_info, TICKERS

# ── Page Config ──────────────────────────────────────────────────────
st.set_page_config(page_title='Stock Dashboard', layout='wide', page_icon='📈')

# CSS for 1.5pt (2px) thick black border and unique padding
st.markdown("""
    <style>
    .chart-box {
        border: 2px solid black;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 25px;
        background-color: white;
    }
    .kpi-box {
        border: 2px solid black;
        border-radius: 10px;
        padding: 10px;
        background-color: #F0F2F6; /* Light Grey for KPIs */
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

st.title('📈 Live Stock Price Dashboard')
st.caption(f'Auto-refreshes every 30 minutes. Last run: {pd.Timestamp.now().strftime("%H:%M:%S")}')

# ── Sidebar Controls ─────────────────────────────────────────────────
with st.sidebar:
    st.header('Controls')
    selected = st.multiselect('Select Tickers', TICKERS, default=['AAPL','MSFT','TSLA'])
    period   = st.selectbox('Period', ['7d','14d','30d','90d'], index=2)
    interval = st.selectbox('Interval', ['1d','1h','5m'], index=0)
    refresh  = st.slider('Auto-refresh (min)', 5, 60, 30)

@st.cache_data(ttl=refresh*60)
def load_all(tickers, period, interval):
    return {t: get_stock_data(t, period, interval) for t in tickers}

with st.spinner('Fetching live data...'):
    data = load_all(tuple(selected), period, interval)

# ── KPI Row (Updated with Borders) ───────────────────────────────────
st.markdown('<div class="chart-box" style="background-color: #FAFAFA;">', unsafe_allow_html=True)
kpi_cols = st.columns(len(selected))
for i, sym in enumerate(selected):
    df = data[sym]
    cur, prv = df['Close'].iloc[-1], df['Close'].iloc[-2]
    chg = cur - prv
    pct = chg / prv * 100
    with kpi_cols[i]:
        st.markdown(f'<div class="kpi-box">', unsafe_allow_html=True)
        st.metric(label=sym, value=f'${cur:.2f}', delta=f'{chg:+.2f} ({pct:+.2f}%)')
        st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ── Chart 1: Line (Pale Pink Background) ─────────────────────────────
st.markdown('<div class="chart-box">', unsafe_allow_html=True)
st.subheader('30-Day Closing Price Trend')
fig_line = go.Figure()
for sym in selected:
    df = data[sym]
    fig_line.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name=sym))
    fig_line.add_trace(go.Scatter(x=df.index, y=df['7D_Avg'], mode='lines', name=f'{sym} 7D Avg', line=dict(dash='dot', width=1)))
fig_line.update_layout(hovermode='x unified', height=380, plot_bgcolor='#FFF0F5', paper_bgcolor='rgba(0,0,0,0)')
st.plotly_chart(fig_line, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# ── Chart 2: Candlestick (Alice Blue Background) ──────────────────────
st.markdown('<div class="chart-box">', unsafe_allow_html=True)
st.subheader('Candlestick Chart (OHLC)')
cs_sym = st.selectbox('Select ticker for candlestick', selected, key='cs')
fig_cs = go.Figure(go.Candlestick(x=data[cs_sym].index, open=data[cs_sym]['Open'], high=data[cs_sym]['High'], low=data[cs_sym]['Low'], close=data[cs_sym]['Close'], name=cs_sym))
fig_cs.update_layout(xaxis_rangeslider_visible=False, height=360, plot_bgcolor='#F0F8FF', paper_bgcolor='rgba(0,0,0,0)')
st.plotly_chart(fig_cs, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# ── Charts Row: Bar (Mint) + Scatter (Ivory) ──────────────────────────
col1, col2 = st.columns(2)
with col1:
    st.markdown('<div class="chart-box">', unsafe_allow_html=True)
    st.subheader('Daily Return %')
    all_df = pd.concat([data[s] for s in selected])
    fig_bar = px.bar(all_df.reset_index(), x='Date', y='Daily_Return', color='Symbol', barmode='group')
    fig_bar.update_layout(height=320, plot_bgcolor='#F5FFFA', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_bar, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="chart-box">', unsafe_allow_html=True)
    st.subheader('Volatility vs Return')
    summary = pd.DataFrame([{'Symbol': s, 'Avg_Return': data[s]['Daily_Return'].mean(), 'Volatility': data[s]['Volatility'].mean(), 'Avg_Volume': data[s]['Volume'].mean()} for s in selected])
    fig_sc = px.scatter(summary, x='Volatility', y='Avg_Return', text='Symbol', size='Avg_Volume', color='Symbol')
    fig_sc.update_layout(height=320, plot_bgcolor='#FFFFF0', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_sc, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── Chart: Area (Lavender Background) ──────────────────────────────────
st.markdown('<div class="chart-box">', unsafe_allow_html=True)
st.subheader('Volume Over Time')
fig_area = go.Figure()
for sym in selected:
    fig_area.add_trace(go.Scatter(x=data[sym].index, y=data[sym]['Volume'], fill='tozeroy', name=sym))
fig_area.update_layout(height=300, plot_bgcolor='#E6E6FA', paper_bgcolor='rgba(0,0,0,0)')
st.plotly_chart(fig_area, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# ── Chart: Heatmap (Lemon Chiffon Background) ─────────────────────────
st.markdown('<div class="chart-box">', unsafe_allow_html=True)
st.subheader('Return Heatmap (by Day)')
hm_sym = st.selectbox('Ticker for heatmap', selected, key='hm')
df_hm = data[hm_sym].copy()
df_hm['DayName'] = df_hm.index.strftime('%a')
df_hm['Week'] = df_hm.index.isocalendar().week.values
pivot = df_hm.pivot_table(values='Daily_Return', index='DayName', columns='Week', aggfunc='mean')
fig_hm = px.imshow(pivot, color_continuous_scale='RdYlGn', aspect='auto')
fig_hm.update_layout(height=280, plot_bgcolor='#FFFACD', paper_bgcolor='rgba(0,0,0,0)')
st.plotly_chart(fig_hm, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# ── Anomaly Alerts (Honeydew Background) ──────────────────────────────
st.markdown('<div class="chart-box" style="background-color: #F0FFF0;">', unsafe_allow_html=True)
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
    st.dataframe(result[['Symbol','Close','Daily_Return','Z','Signal']], use_container_width=True)
else:
    st.success('No anomalies detected.')
st.markdown('</div>', unsafe_allow_html=True)

# ── Auto-refresh ──
if st.button('🔄 Refresh Now'):
    st.cache_data.clear()
    st.rerun()
