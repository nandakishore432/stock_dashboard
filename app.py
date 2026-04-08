import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import time
import pytz
from utils import get_stock_data, get_info, TICKERS

# ── Classic font & color theme ─────────────────────────────
CLASSIC_FONT = "Playfair Display, Georgia, 'Times New Roman', serif"
BG_COLOR     = "#0e1117"
CARD_BG      = "#1a1d2e"
ACCENT       = "#c9a84c"
GRID_COLOR   = "#2a2d3e"
TEXT_COLOR   = "#e8e0d0"

STOCK_COLORS = {
    "AAPL" : "#4f8ef7",
    "MSFT" : "#50C878",
    "GOOGL": "#FF6B6B",
    "AMZN" : "#FFD700",
    "TSLA" : "#FF4500",
    "NVDA" : "#9B59B6",
}

# ── Page Config ──────────────────────────────────────────────────────
st.set_page_config(page_title='Stock Dashboard', layout='wide', page_icon='📈')
st.title('📈 Live Stock Price Dashboard')
# ── Dynamic Timezone Logic ──────────────────────────────────────────
tz = pytz.timezone('Asia/Kolkata') 
now_time = pd.Timestamp.now(tz=tz).strftime("%H:%M:%S")

st.caption(f'🚀 Last updated: {now_time} (IST) | Auto-refreshes every 30 min')
# ────────────────────────────────────────────────────────────────────
#st.caption(f'Auto-refreshes every 30 minutes. Last run: {pd.Timestamp.now().strftime("%H:%M:%S")}')

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

# ── KPI Section Header ────────────────────────────────────────────────
st.markdown(
    """
    <div style="
        background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
        padding: 15px;
        border-radius: 15px;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        text-align: center;
    ">
        <h1 style="
            color: white; 
            font-family: 'Inter', sans-serif; 
            font-weight: 800; 
            letter-spacing: 2px;
            margin: 0;
            text-transform: uppercase;
            font-size: 1.8rem;
        ">
            📌 Live Market Updates
        </h1>
    </div>
    """, 
    unsafe_allow_html=True
)

# ── KPI Row Logic ─────────────────────────────────────────────────────
kpi_cols = st.columns(len(selected))

for i, sym in enumerate(selected):
    df = data[sym]
    if df.empty:
        continue
        
    # Data Extraction
    cur = df['Close'].iloc[-1]
    prv = df['Close'].iloc[-2]
    chg = cur - prv
    pct = (chg / prv) * 100
    hi  = df['High'].max()
    lo  = df['Low'].min()
    vol = df['Volume'].iloc[-1]
    
    # Logic for Colors and Symbols
    color = "#27ae60" if chg >= 0 else "#e74c3c"  # Professional Green/Red
    symbol = "▲" if chg >= 0 else "▼"
    
    # Fetch Market Cap
    try:
        mkt_cap = yf.Ticker(sym).info.get('marketCap', 0)
        mkt_cap_str = f"{mkt_cap / 1e9:.2f}B" if mkt_cap > 1e9 else f"{mkt_cap / 1e6:.2f}M"
    except:
        mkt_cap_str = "N/A"

    # ── Individual KPI Cards ──────────────────────────────────────────
    kpi_cols[i].markdown(
        f"""
        <div style="
            background-color: #f3e5f5; 
            border: 3px solid #2c3e50; 
            border-radius: 12px; 
            padding: 15px; 
            text-align: center;
            box-shadow: 2px 4px 8px rgba(0,0,0,0.1);
        ">
            <h3 style="margin: 0; color: #1a1a2e; font-size: 1.2rem;">{sym}</h3>
            <div style="font-size: 1.6rem; font-weight: 800; margin: 5px 0; color: #1a1a2e;">${cur:.2f}</div>
            <div style="color: {color}; font-weight: 700; font-size: 1.1rem; margin-bottom: 10px;">
                {symbol} {abs(chg):.2f} ({abs(pct):.2f}%)
            </div>
            <div style="text-align: left; font-size: 0.85rem; line-height: 1.8; border-top: 1px solid #d1c4e9; pt: 8px;">
                <div style="display: flex; justify-content: space-between;"><b>High:</b> <span>${hi:.2f}</span></div>
                <div style="display: flex; justify-content: space-between;"><b>Low:</b> <span>${lo:.2f}</span></div>
                <div style="display: flex; justify-content: space-between;"><b>Volume:</b> <span>{vol/1e6:.1f}M</span></div>
                <div style="display: flex; justify-content: space-between;"><b>Mkt Cap:</b> <span>{mkt_cap_str}</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
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
fig_line.update_layout(
    height=400,
    paper_bgcolor='skyblue',
    plot_bgcolor='lavender',
    margin=dict(l=10, r=10, t=10, b=10)
)
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
fig_cs.update_layout(
    height=400,
    paper_bgcolor='#FFFFFF',
    plot_bgcolor='#F0F2F6',
    margin=dict(l=10, r=10, t=10, b=10)
)
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

# ── Chart: Heatmap — Weekly Return ────────────────────────────────────
# Ensure this matches your CSS classes defined at the top
st.markdown('<div class="chart-card card-heatmap">', unsafe_allow_html=True)

# 1. Styled Gradient Title (Centered and Bold)
st.markdown(
    """
    <div style="
        background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        text-align: center;
    ">
        <h2 style="
            color: white; 
            font-family: 'Inter', sans-serif; 
            font-weight: 800; 
            letter-spacing: 1.5px;
            margin: 0;
            text-transform: uppercase;
            font-size: 1.6rem;
        ">
            🧮 RETURN HEATMAP (BY DAY)
        </h2>
    </div>
    """, 
    unsafe_allow_html=True
)

# Selector for the user to pick which stock to analyze
hm_sym = st.selectbox('Focus Ticker for Heatmap Analysis', selected, key='hm_select')
df_hm = data[hm_sym].copy()

if not df_hm.empty and 'Daily_Return' in df_hm.columns:
    # Prepare data for the Heatmap
    df_hm['DayName'] = df_hm.index.strftime('%a')
    # Using %V for ISO week or %U for US week to ensure chronological order
    df_hm['Week'] = df_hm.index.strftime('%U') 
    
    pivot = df_hm.pivot_table(
        values='Daily_Return', 
        index='DayName', 
        columns='Week', 
        aggfunc='mean'
    )
    
    # Reorder index to ensure Monday-Friday sequence
    day_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    pivot = pivot.reindex([d for d in day_order if d in pivot.index])

    # 2. Modern Color Palette (Using 'Viridis' or 'Magma' for attractiveness)
    fig_hm = px.imshow(
        pivot, 
        color_continuous_scale='Viridis', 
        aspect='auto',
        labels={'color': 'Avg Return %'},
        template='plotly_white'
    )

    # 3. Transparent Layout to show the card background
    fig_hm.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis_title="Week Number",
        yaxis_title=""
    )

    st.plotly_chart(fig_hm, use_container_width=True)
else:
    st.warning(f'Insufficient data to generate heatmap for {hm_sym}.')

st.markdown('</div>', unsafe_allow_html=True)

# ── Anomaly Alerts Section ────────────────────────────────────────────
st.markdown('<div class="chart-card card-anomaly">', unsafe_allow_html=True)

# 1. Main Centered Title
st.markdown(
    """
    <div style="text-align: center;">
        <h2 style="font-weight: 800; color: #1a1a2e; margin-bottom: 20px;">
            🚨 ANOMALY ALERTS (Z-SCORE > 2)
        </h2>
    </div>
    """, 
    unsafe_allow_html=True
)

alerts = []
for sym in selected:
    df = data[sym].copy()
    if df.empty or len(df) < 2:
        continue
    
    std = df['Daily_Return'].std()
    if std > 0:
        df['Z'] = (df['Daily_Return'] - df['Daily_Return'].mean()) / std
        flagged = df[abs(df['Z']) > 2][['Close','Daily_Return','Z']].copy()
        flagged['Symbol'] = sym
        flagged['Signal'] = flagged['Daily_Return'].apply(lambda x: '🔺 Surge' if x > 0 else '🔻 Drop')
        alerts.append(flagged)

if alerts:
    result = pd.concat(alerts).sort_index(ascending=False).head(20)
    display_df = result[['Symbol','Close','Daily_Return','Z','Signal']]

    # 2. Table Styling (Blue Lines + Skyblue Bold Headers)
    styled_table = display_df.style.set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', '#87CEEB'), 
            ('color', 'black'), 
            ('font-weight', 'bold'),
            ('border', '2px solid #0000FF'),
            ('text-align', 'center')
        ]},
        {'selector': 'td', 'props': [
            ('border', '1px solid #0000FF'),
            ('text-align', 'center'),
            ('padding', '10px')
        ]},
        {'selector': '', 'props': [
            ('border-collapse', 'collapse'),
            ('width', '100%'),
            ('margin-left', 'auto'),
            ('margin-right', 'auto')
        ]}
    ]).format({
        'Close': '${:.2f}',
        'Daily_Return': '{:.2f}%',
        'Z': '{:.2f}'
    })

    # Display using st.write to render the Styler object correctly
    st.write(styled_table.to_html(), unsafe_allow_html=True)
else:
    st.success('No anomalies detected in the selected period.')

st.markdown('</div>', unsafe_allow_html=True)

st.divider()
st.markdown(
    f"<p style='text-align:center;font-family:{CLASSIC_FONT};color:#555;font-size:13px;'>"
    "Data Source is: Yahoo Finance (yfinance) · No API key required · "
    "Built with Streamlit & Plotly</p>",
    unsafe_allow_html=True,
)
# ── Auto-refresh ──────────────────────────────────────────────────────
st.divider()
if st.button('🔄 Refresh Now'):
    st.cache_data.clear()
    st.rerun()
time.sleep(refresh * 60)
st.rerun()
