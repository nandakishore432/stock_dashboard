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

    # ✅ Fix 1: Flatten MultiIndex columns introduced in yfinance >= 0.2.x
    # Without this, df['Close'] silently returns NaN for every row
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # ✅ Fix 2: Drop rows where Close is NaN (partial trading days / missing data)
    df = df.dropna(subset=['Close'])

    if df.empty:
        return df

    # ✅ Fix 3: Ensure index name is 'Date' for downstream px.bar x='Date'
    df.index.name = 'Date'

    # ✅ Fix 4: Add Symbol column (needed for pd.concat in bar chart)
    df['Symbol'] = ticker

    # ✅ Fix 5: Use min_periods=1 so rolling calcs never produce all-NaN
    #           for short periods like '7d'
    df['Daily_Return'] = df['Close'].pct_change() * 100
    df['Volatility']   = df['Daily_Return'].rolling(7, min_periods=1).std()
    df['7D_Avg']       = df['Close'].rolling(7, min_periods=1).mean()

    return df


def get_info(ticker: str) -> dict:
    try:
        return yf.Ticker(ticker).info
    except Exception:
        return {}


# ── Page Config ───────────────────────────────────────────────────────
st.set_page_config(page_title='Stock Dashboard', layout='wide', page_icon='📈')
st.title('📈 Live Stock Price Dashboard')
st.caption(f'Auto-refreshes every 30 minutes. Last run: {pd.Timestamp.now().strftime("%H:%M:%S")}')


# ── Sidebar Controls ──────────────────────────────────────────────────
with st.sidebar:
    st.header('Controls')
    selected = st.multiselect('Select Tickers', TICKERS, default=['AAPL', 'MSFT', 'TSLA'])
    period   = st.selectbox('Period', ['7d', '14d', '30d', '90d'], index=2)
    interval = st.selectbox('Interval', ['1d', '1h', '5m'], index=0)
    refresh  = st.slider('Auto-refresh (min)', 5, 60, 30)
    st.divider()
    st.caption('Data: Yahoo Finance (yfinance)')


# ── Load Data ─────────────────────────────────────────────────────────
@st.cache_data(ttl=refresh * 60)
def load_all(tickers, period, interval):
    return {t: get_stock_data(t, period, interval) for t in tickers}


with st.spinner('Fetching live data...'):
    data = load_all(tuple(selected), period, interval)


# ── KPI Row ───────────────────────────────────────────────────────────
kpi_cols = st.columns(len(selected))

for i, sym in enumerate(selected):
    df = data[sym]

    # ✅ Fix 6: Guard against empty or insufficient dataframes
    if df is None or len(df) < 2:
        kpi_cols[i].metric(label=sym, value='N/A', delta='No data')
        continue

    cur = df['Close'].iloc[-1]
    prv = df['Close'].iloc[-2]

    # ✅ Fix 7: Guard against NaN values before formatting
    if pd.isna(cur) or pd.isna(prv) or prv == 0:
        kpi_cols[i].metric(label=sym, value='N/A', delta='Insufficient data')
        continue

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


# ── Chart 1: Line — Closing Price Trend ──────────────────────────────
st.subheader('Closing Price Trend')
fig_line = go.Figure()

for sym in selected:
    df = data[sym]
    if df.empty:
        continue
    fig_line.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name=sym))
    fig_line.add_trace(go.Scatter(
        x=df.index, y=df['7D_Avg'], mode='lines',
        name=f'{sym} 7D Avg', line=dict(dash='dot', width=1)
    ))

fig_line.update_layout(hovermode='x unified', height=380)
st.plotly_chart(fig_line, use_container_width=True)


# ── Chart 2: Candlestick — OHLC ───────────────────────────────────────
st.subheader('Candlestick Chart (OHLC)')
cs_sym  = st.selectbox('Select ticker for candlestick', selected, key='cs')
df_cs   = data[cs_sym]

if not df_cs.empty:
    fig_cs = go.Figure(go.Candlestick(
        x=df_cs.index,
        open=df_cs['Open'], high=df_cs['High'],
        low=df_cs['Low'],   close=df_cs['Close'],
        name=cs_sym
    ))
    fig_cs.update_layout(xaxis_rangeslider_visible=False, height=360)
    st.plotly_chart(fig_cs, use_container_width=True)
else:
    st.warning(f'No OHLC data available for {cs_sym}.')


# ── Charts Row: Bar + Scatter ─────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader('Daily Return % (Bar Chart)')
    valid_dfs = [data[s] for s in selected if not data[s].empty]
    if valid_dfs:
        all_df  = pd.concat(valid_dfs)
        fig_bar = px.bar(
            all_df.reset_index(), x='Date', y='Daily_Return',
            color='Symbol', barmode='group',
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_bar.update_layout(height=320)
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.warning('No return data to display.')

with col2:
    st.subheader('Volatility vs Return (Scatter)')
    summary_rows = []
    for s in selected:
        df = data[s]
        if df.empty:
            continue
        summary_rows.append({
            'Symbol':     s,
            'Avg_Return': df['Daily_Return'].mean(),
            'Volatility': df['Volatility'].mean(),
            'Avg_Volume': df['Volume'].mean()
        })

    if summary_rows:
        summary = pd.DataFrame(summary_rows)
        fig_sc  = px.scatter(
            summary, x='Volatility', y='Avg_Return', text='Symbol',
            size='Avg_Volume', color='Symbol',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_sc.update_traces(textposition='top center')
        fig_sc.update_layout(height=320)
        st.plotly_chart(fig_sc, use_container_width=True)
    else:
        st.warning('No volatility data to display.')


# ── Chart: Area — Volume ──────────────────────────────────────────────
st.subheader('Volume Over Time (Area Chart)')
fig_area = go.Figure()

for sym in selected:
    df = data[sym]
    if df.empty:
        continue
    fig_area.add_trace(go.Scatter(
        x=df.index, y=df['Volume'],
        fill='tozeroy', name=sym, mode='lines'
    ))

fig_area.update_layout(height=300)
st.plotly_chart(fig_area, use_container_width=True)


# ── Chart: Heatmap — Weekly Return ────────────────────────────────────
st.subheader('Return Heatmap (by Day)')
hm_sym = st.selectbox('Ticker for heatmap', selected, key='hm')
df_hm  = data[hm_sym].copy()

if not df_hm.empty and 'Daily_Return' in df_hm.columns:
    df_hm['DayName'] = df_hm.index.strftime('%a')
    df_hm['Week']    = df_hm.index.isocalendar().week.values
    pivot = df_hm.pivot_table(
        values='Daily_Return', index='DayName', columns='Week', aggfunc='mean'
    )
    fig_hm = px.imshow(
        pivot, color_continuous_scale='RdYlGn', aspect='auto',
        labels={'color': 'Return %'}
    )
    fig_hm.update_layout(height=280)
    st.plotly_chart(fig_hm, use_container_width=True)
else:
    st.warning(f'Not enough data to build heatmap for {hm_sym}.')


# ── Anomaly Alerts Table ──────────────────────────────────────────────
st.subheader('Anomaly Alerts (Z-Score > 2)')
alerts = []

for sym in selected:
    df = data[sym].copy()
    if df.empty or len(df) < 3:
        continue
    std = df['Daily_Return'].std()
    if std == 0 or pd.isna(std):
        continue
    df['Z']     = (df['Daily_Return'] - df['Daily_Return'].mean()) / std
    flagged     = df[abs(df['Z']) > 2][['Close', 'Daily_Return', 'Z']].copy()
    flagged['Symbol'] = sym
    flagged['Signal'] = flagged['Daily_Return'].apply(
        lambda x: '🔺 Surge' if x > 0 else '🔻 Drop'
    )
    alerts.append(flagged)

if alerts:
    result = pd.concat(alerts).sort_index(ascending=False).head(20)
    st.dataframe(
        result[['Symbol', 'Close', 'Daily_Return', 'Z', 'Signal']],
        use_container_width=True
    )
else:
    st.success('No anomalies detected in the selected period.')


# ── Auto-refresh ──────────────────────────────────────────────────────
st.divider()
if st.button('🔄 Refresh Now'):
    st.cache_data.clear()
    st.rerun()

time.sleep(refresh * 60)
st.rerun()
