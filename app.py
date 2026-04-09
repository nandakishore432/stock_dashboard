import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf                          # FIX #8 — was missing, caused mkt_cap crash
import time
import pytz
from datetime import date, timedelta
from utils import get_stock_data, get_info, TICKERS

# ── streamlit-autorefresh (pip install streamlit-autorefresh) ──────────
# FIX #1 — replaces the blocking time.sleep(refresh*60) + st.rerun() pattern
try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_AVAILABLE = True
except ImportError:
    AUTOREFRESH_AVAILABLE = False

# ── Page Config ───────────────────────────────────────────────────────
st.set_page_config(page_title='Stock Dashboard', layout='wide', page_icon='📈')

# ── Classic font & color theme ────────────────────────────────────────
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

# ── The "No-Fail" CSS ─────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .stApp { background-color: #f0f2f6; }
    [data-testid="stVerticalBlock"] > div:has(div.stPlotlyChart),
    [data-testid="stVerticalBlock"] > div:has(div[data-testid="metric-container"]) {
        background-color: white;
        border: 2px solid #2d3436;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
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

# ── Sidebar Controls ──────────────────────────────────────────────────
with st.sidebar:
    st.header('⚙️ Controls')

    selected = st.multiselect('Select Tickers', TICKERS, default=['AAPL', 'MSFT', 'TSLA', 'NFLX'])

    # ── FIX #7 — Date Range Selector with preset buttons ──────────────
    st.subheader('📅 Date Range')
    preset_col1, preset_col2, preset_col3, preset_col4 = st.columns(4)
    today = date.today()

    if preset_col1.button('1M'):
        st.session_state['start_date'] = today - timedelta(days=30)
        st.session_state['end_date']   = today
    if preset_col2.button('3M'):
        st.session_state['start_date'] = today - timedelta(days=90)
        st.session_state['end_date']   = today
    if preset_col3.button('6M'):
        st.session_state['start_date'] = today - timedelta(days=180)
        st.session_state['end_date']   = today
    if preset_col4.button('1Y'):
        st.session_state['start_date'] = today - timedelta(days=365)
        st.session_state['end_date']   = today

    default_start = st.session_state.get('start_date', today - timedelta(days=30))
    default_end   = st.session_state.get('end_date',   today)

    start_date = st.date_input('Start Date', value=default_start)
    end_date   = st.date_input('End Date',   value=default_end)

    # Keep legacy period/interval for utils compatibility
    interval = st.selectbox('Interval', ['1d', '1h', '5m'], index=0)

    # ── FIX #1 — Auto-refresh slider (non-blocking) ───────────────────
    st.subheader('🔄 Auto-Refresh')
    refresh = st.slider('Refresh interval (min)', 5, 60, 30)

    st.divider()
    st.caption('Data: Yahoo Finance (yfinance)')

# ── FIX #1 — Non-blocking auto-refresh via streamlit-autorefresh ──────
if AUTOREFRESH_AVAILABLE:
    count = st_autorefresh(interval=refresh * 60 * 1000, key="autorefresh")
else:
    # Graceful fallback: show a manual refresh button if package not installed
    if st.sidebar.button('🔄 Refresh Now'):
        st.cache_data.clear()
        st.rerun()

# ── Header ────────────────────────────────────────────────────────────
tz       = pytz.timezone('Asia/Kolkata')
now_time = pd.Timestamp.now(tz=tz).strftime("%H:%M:%S")

st.title('📈 Live Stock Price Dashboard')
st.caption(f'🚀 Last updated: {now_time} (IST) | Auto-refreshes every {refresh} min')


# ─────────────────────────────────────────────────────────────────────
# FIX #4 — Proper caching: TTL is a static constant (300s), not a
#           runtime variable. Market-cap uses fast_info (reliable).
# FIX #5 — Error handling: try/except on every data fetch with
#           st.error() messages shown to the user.
# ─────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_stock(ticker, start, end, interval):
    """Fetch OHLCV data for a single ticker with proper error handling."""
    try:
        df = yf.download(ticker, start=start, end=end,
                         interval=interval, progress=False, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index.name = 'Date'
        df['Symbol']       = ticker
        df['Daily_Return'] = df['Close'].pct_change() * 100
        df['7D_Avg']       = df['Close'].rolling(7).mean()
        df['Volatility']   = df['Daily_Return'].rolling(7).std()
        # ── Technical Indicators (FIX #3) ─────────────────────────────
        # RSI-14
        delta   = df['Close'].diff()
        gain    = delta.clip(lower=0).rolling(14).mean()
        loss    = (-delta.clip(upper=0)).rolling(14).mean()
        rs      = gain / loss.replace(0, np.nan)
        df['RSI'] = 100 - (100 / (1 + rs))
        # MACD (12/26/9)
        ema12        = df['Close'].ewm(span=12, adjust=False).mean()
        ema26        = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD']         = ema12 - ema26
        df['MACD_Signal']  = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist']    = df['MACD'] - df['MACD_Signal']
        return df
    except Exception as e:
        st.error(f"❌ Failed to load data for **{ticker}**: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_market_cap(sym):
    """Fetch market cap using fast_info (FIX #8 — reliable, avoids .info timeout)."""
    try:
        fi = yf.Ticker(sym).fast_info
        mkt_cap = getattr(fi, 'market_cap', None)
        if mkt_cap and mkt_cap > 0:
            if mkt_cap >= 1e12:
                return f"${mkt_cap/1e12:.2f}T"
            elif mkt_cap >= 1e9:
                return f"${mkt_cap/1e9:.2f}B"
            else:
                return f"${mkt_cap/1e6:.2f}M"
    except Exception:
        pass
    return "N/A"


# ── Guard: require at least one ticker ───────────────────────────────
if not selected:
    st.warning('⚠️ Please select at least one ticker from the sidebar.')
    st.stop()

# ── Load all data ─────────────────────────────────────────────────────
with st.spinner('Fetching live data...'):
    data = {}
    for t in selected:
        df = load_stock(t, str(start_date), str(end_date), interval)
        if not df.empty:
            data[t] = df

if not data:
    st.error('❌ No data could be loaded. Please check your ticker symbols and date range.')
    st.stop()

active = list(data.keys())   # tickers that loaded successfully

# ── KPI Section Header ────────────────────────────────────────────────
st.markdown(
    """
    <div style="
        background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
        padding: 15px; border-radius: 15px; margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2); text-align: center;">
        <h1 style="color: white; font-family: 'Inter', sans-serif;
            font-weight: 800; letter-spacing: 2px; margin: 0;
            text-transform: uppercase; font-size: 1.8rem;">
            📌 Live Market Updates
        </h1>
    </div>
    """,
    unsafe_allow_html=True
)

# ── FIX #8 — KPI Metrics Row ─────────────────────────────────────────
kpi_cols = st.columns(len(active))

for i, sym in enumerate(active):
    df  = data[sym]
    cur = float(df['Close'].iloc[-1])
    prv = float(df['Close'].iloc[-2]) if len(df) > 1 else cur
    chg = cur - prv
    pct = (chg / prv) * 100 if prv else 0
    hi  = float(df['High'].max())
    lo  = float(df['Low'].min())
    vol = float(df['Volume'].iloc[-1])

    color  = "#27ae60" if chg >= 0 else "#e74c3c"
    symbol = "▲" if chg >= 0 else "▼"

    mkt_cap_str = get_market_cap(sym)          # FIX #8 — now uses fast_info

    kpi_cols[i].markdown(
        f"""
        <div style="background-color:#f3e5f5; border:3px solid #2c3e50;
            border-radius:12px; padding:15px; text-align:center;
            box-shadow:2px 4px 8px rgba(0,0,0,0.1);">
            <h3 style="margin:0; color:#1a1a2e; font-size:1.2rem;">{sym}</h3>
            <div style="font-size:1.6rem; font-weight:800; margin:5px 0;
                color:#1a1a2e;">${cur:.2f}</div>
            <div style="color:{color}; font-weight:700; font-size:1.1rem;
                margin-bottom:10px;">
                {symbol} {abs(chg):.2f} ({abs(pct):.2f}%)
            </div>
            <div style="text-align:left; font-size:0.85rem; line-height:1.8;
                border-top:1px solid #d1c4e9; padding-top:8px;">
                <div style="display:flex; justify-content:space-between;">
                    <b>High:</b> <span>${hi:.2f}</span></div>
                <div style="display:flex; justify-content:space-between;">
                    <b>Low:</b> <span>${lo:.2f}</span></div>
                <div style="display:flex; justify-content:space-between;">
                    <b>Volume:</b> <span>{vol/1e6:.1f}M</span></div>
                <div style="display:flex; justify-content:space-between;">
                    <b>Mkt Cap:</b> <span>{mkt_cap_str}</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.divider()

# ── FIX #9 — CSV Export ───────────────────────────────────────────────
st.subheader('📥 Export Data')
export_sym = st.selectbox('Select ticker to export', active, key='export_sel')
if export_sym in data:
    csv_data = data[export_sym].reset_index().to_csv(index=False).encode('utf-8')
    st.download_button(
        label=f'⬇️ Download {export_sym} CSV',
        data=csv_data,
        file_name=f'{export_sym}_{start_date}_{end_date}.csv',
        mime='text/csv'
    )

st.divider()

# ── Chart 1: Line — Multi-stock Price Trend ───────────────────────────
st.subheader('📈 Closing Price Trend (Multi-Ticker)')
fig_line = go.Figure()
for sym in active:
    df = data[sym]
    color = STOCK_COLORS.get(sym, None)
    fig_line.add_trace(go.Scatter(
        x=df.index, y=df['Close'], mode='lines', name=sym,
        line=dict(color=color, width=2)
    ))
    fig_line.add_trace(go.Scatter(
        x=df.index, y=df['7D_Avg'], mode='lines',
        name=f'{sym} 7D Avg', line=dict(dash='dot', width=1, color=color),
        opacity=0.6
    ))
fig_line.update_layout(
    hovermode='x unified', height=400,
    paper_bgcolor='skyblue', plot_bgcolor='lavender',
    margin=dict(l=10, r=10, t=30, b=10),
    title='Closing Prices with 7-Day Moving Average'
)
st.plotly_chart(fig_line, use_container_width=True)

# ── Chart 2: Candlestick — OHLC ───────────────────────────────────────
st.subheader('🕯️ Candlestick Chart (OHLC)')
cs_sym = st.selectbox('Select ticker for candlestick', active, key='cs')
df_cs  = data[cs_sym]

fig_cs = go.Figure(go.Candlestick(
    x=df_cs.index,
    open=df_cs['Open'], high=df_cs['High'],
    low=df_cs['Low'],   close=df_cs['Close'],
    name=cs_sym,
    increasing_line_color='#26a69a',
    decreasing_line_color='#ef5350'
))
fig_cs.update_layout(
    xaxis_rangeslider_visible=False, height=400,
    paper_bgcolor='#FFFFFF', plot_bgcolor='#F0F2F6',
    margin=dict(l=10, r=10, t=30, b=10),
    title=f'{cs_sym} — OHLC Candlestick'
)
st.plotly_chart(fig_cs, use_container_width=True)

# ── FIX #3 — RSI & MACD Subplot Panel ────────────────────────────────
st.subheader('📉 RSI & MACD Technical Indicators')
ind_sym = st.selectbox('Select ticker for indicators', active, key='ind')
df_ind  = data[ind_sym].dropna(subset=['RSI', 'MACD'])

if not df_ind.empty:
    fig_ind = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.5, 0.25, 0.25],
        vertical_spacing=0.04,
        subplot_titles=(
            f'{ind_sym} — Close Price',
            'RSI (14)',
            'MACD (12 / 26 / 9)'
        )
    )

    # Row 1 — Close price
    fig_ind.add_trace(
        go.Scatter(x=df_ind.index, y=df_ind['Close'],
                   mode='lines', name='Close',
                   line=dict(color=STOCK_COLORS.get(ind_sym, '#4f8ef7'), width=2)),
        row=1, col=1
    )

    # Row 2 — RSI
    fig_ind.add_trace(
        go.Scatter(x=df_ind.index, y=df_ind['RSI'],
                   mode='lines', name='RSI 14',
                   line=dict(color='#FF9800', width=1.5)),
        row=2, col=1
    )
    # Overbought / oversold reference lines
    fig_ind.add_hline(y=70, line_dash='dash', line_color='red',
                      annotation_text='Overbought (70)', row=2, col=1)
    fig_ind.add_hline(y=30, line_dash='dash', line_color='green',
                      annotation_text='Oversold (30)',   row=2, col=1)

    # Row 3 — MACD
    colors_hist = ['#26a69a' if v >= 0 else '#ef5350'
                   for v in df_ind['MACD_Hist']]
    fig_ind.add_trace(
        go.Bar(x=df_ind.index, y=df_ind['MACD_Hist'],
               name='MACD Histogram', marker_color=colors_hist, opacity=0.6),
        row=3, col=1
    )
    fig_ind.add_trace(
        go.Scatter(x=df_ind.index, y=df_ind['MACD'],
                   mode='lines', name='MACD',
                   line=dict(color='#1565C0', width=1.5)),
        row=3, col=1
    )
    fig_ind.add_trace(
        go.Scatter(x=df_ind.index, y=df_ind['MACD_Signal'],
                   mode='lines', name='Signal',
                   line=dict(color='#E91E63', width=1.5, dash='dot')),
        row=3, col=1
    )

    fig_ind.update_layout(
        height=650,
        paper_bgcolor='#FFFFFF', plot_bgcolor='#F8F9FA',
        margin=dict(l=10, r=10, t=50, b=10),
        showlegend=True,
        hovermode='x unified'
    )
    fig_ind.update_yaxes(title_text='Price', row=1, col=1)
    fig_ind.update_yaxes(title_text='RSI',   row=2, col=1, range=[0, 100])
    fig_ind.update_yaxes(title_text='MACD',  row=3, col=1)

    st.plotly_chart(fig_ind, use_container_width=True)
else:
    st.warning(f'⚠️ Not enough data to compute RSI/MACD for **{ind_sym}**. Try a longer date range.')

# ── Charts Row: Bar + Scatter ─────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader('📊 Daily Return % (Bar Chart)')
    all_df  = pd.concat([data[s] for s in active])
    fig_bar = px.bar(
        all_df.reset_index(), x='Date', y='Daily_Return',
        color='Symbol', barmode='group',
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig_bar.update_layout(height=320)
    st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    st.subheader('🔵 Volatility vs Return (Scatter)')
    summary = pd.DataFrame([{
        'Symbol':     s,
        'Avg_Return': data[s]['Daily_Return'].mean(),
        'Volatility': data[s]['Volatility'].mean(),
        'Avg_Volume': data[s]['Volume'].mean()
    } for s in active])
    fig_sc = px.scatter(
        summary, x='Volatility', y='Avg_Return', text='Symbol',
        size='Avg_Volume', color='Symbol',
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig_sc.update_traces(textposition='top center')
    fig_sc.update_layout(height=320)
    st.plotly_chart(fig_sc, use_container_width=True)

# ── Chart: Area — Volume ──────────────────────────────────────────────
st.subheader('📦 Volume Over Time (Area Chart)')
fig_area = go.Figure()
for sym in active:
    df = data[sym]
    fig_area.add_trace(go.Scatter(
        x=df.index, y=df['Volume'], fill='tozeroy',
        name=sym, mode='lines',
        line=dict(color=STOCK_COLORS.get(sym, None))
    ))
fig_area.update_layout(height=300)
st.plotly_chart(fig_area, use_container_width=True)

# ── Chart: Heatmap — Weekly Return ───────────────────────────────────
st.markdown(
    """
    <div style="background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
        padding:15px; border-radius:12px; margin-bottom:20px;
        box-shadow:0 4px 12px rgba(0,0,0,0.2); text-align:center;">
        <h2 style="color:white; font-family:'Inter',sans-serif; font-weight:800;
            letter-spacing:1.5px; margin:0; text-transform:uppercase;
            font-size:1.6rem;">🧮 RETURN HEATMAP (BY DAY)</h2>
    </div>
    """,
    unsafe_allow_html=True
)

hm_sym = st.selectbox('Focus Ticker for Heatmap Analysis', active, key='hm_select')
df_hm  = data[hm_sym].copy()

if not df_hm.empty and 'Daily_Return' in df_hm.columns:
    df_hm['DayName'] = df_hm.index.strftime('%a')
    df_hm['Week']    = df_hm.index.strftime('%U')
    pivot = df_hm.pivot_table(
        values='Daily_Return', index='DayName', columns='Week', aggfunc='mean'
    )
    day_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    pivot = pivot.reindex([d for d in day_order if d in pivot.index])
    fig_hm = px.imshow(
        pivot, color_continuous_scale='Viridis', aspect='auto',
        labels={'color': 'Avg Return %'}, template='plotly_white'
    )
    fig_hm.update_layout(
        height=320, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis_title="Week Number", yaxis_title=""
    )
    st.plotly_chart(fig_hm, use_container_width=True)
else:
    st.warning(f'Insufficient data to generate heatmap for {hm_sym}.')

# ── Anomaly Alerts ────────────────────────────────────────────────────
st.markdown(
    """
    <div style="text-align:center;">
        <h2 style="font-weight:800; color:#1a1a2e; margin-bottom:20px;">
            🚨 ANOMALY ALERTS (Z-SCORE &gt; 2)
        </h2>
    </div>
    """,
    unsafe_allow_html=True
)

alerts = []
for sym in active:
    df  = data[sym].copy()
    if df.empty or len(df) < 2:
        continue
    std = df['Daily_Return'].std()
    if std > 0:
        df['Z']     = (df['Daily_Return'] - df['Daily_Return'].mean()) / std
        flagged     = df[abs(df['Z']) > 2][['Close', 'Daily_Return', 'Z']].copy()
        flagged['Symbol'] = sym
        flagged['Signal'] = flagged['Daily_Return'].apply(
            lambda x: '🔺 Surge' if x > 0 else '🔻 Drop'
        )
        alerts.append(flagged)

if alerts:
    result     = pd.concat(alerts).sort_index(ascending=False).head(20)
    display_df = result[['Symbol', 'Close', 'Daily_Return', 'Z', 'Signal']]
    styled_table = display_df.style.set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', '#87CEEB'), ('color', 'black'),
            ('font-weight', 'bold'), ('border', '2px solid #0000FF'),
            ('text-align', 'center')
        ]},
        {'selector': 'td', 'props': [
            ('border', '1px solid #0000FF'),
            ('text-align', 'center'), ('padding', '10px')
        ]},
        {'selector': '', 'props': [
            ('border-collapse', 'collapse'),
            ('width', '100%'), ('margin-left', 'auto'), ('margin-right', 'auto')
        ]}
    ]).format({'Close': '${:.2f}', 'Daily_Return': '{:.2f}%', 'Z': '{:.2f}'})
    st.write(styled_table.to_html(), unsafe_allow_html=True)
else:
    st.success('✅ No anomalies detected in the selected period.')

# ── Footer ────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    f"<p style='text-align:center; font-family:{CLASSIC_FONT}; "
    "color:#555; font-size:13px;'>"
    "Data Source: Yahoo Finance (yfinance) · No API key required · "
    "Built with Streamlit &amp; Plotly</p>",
    unsafe_allow_html=True
)

# ── FIX #1 — Manual Refresh Button (backup if autorefresh unavailable) 
st.divider()
if st.button('🔄 Refresh Now'):
    st.cache_data.clear()
    st.rerun()
# NOTE: The old   time.sleep(refresh * 60) + st.rerun()   has been REMOVED.
# That pattern froze the entire app thread. st_autorefresh handles this now.
