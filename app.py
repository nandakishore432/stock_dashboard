import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import time
from utils import get_stock_data, TICKERS

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Live Stock Dashboard", layout="wide", page_icon="📈")

# ── Global CSS: Background + Chart Borders + Fonts ────────────────────────────
st.markdown("""
<style>
/* ── BACKGROUND: Stock exchange scenery with animated ticker feel ── */
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(ellipse at 10% 20%, rgba(0,212,255,0.08) 0%, transparent 50%),
        radial-gradient(ellipse at 90% 80%, rgba(0,255,136,0.07) 0%, transparent 50%),
        radial-gradient(ellipse at 50% 50%, rgba(99,102,241,0.05) 0%, transparent 70%),
        linear-gradient(135deg, #0a0e1a 0%, #0d1b2a 30%, #0f2440 60%, #0a1628 100%);
    min-height: 100vh;
}

/* Animated stock-ticker grid lines in the background */
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background-image:
        repeating-linear-gradient(0deg, transparent, transparent 60px, rgba(0,212,255,0.03) 60px, rgba(0,212,255,0.03) 61px),
        repeating-linear-gradient(90deg, transparent, transparent 80px, rgba(0,255,136,0.02) 80px, rgba(0,255,136,0.02) 81px);
    pointer-events: none;
    z-index: 0;
}

/* Decorative stock exchange skyline at bottom */
[data-testid="stAppViewContainer"]::after {
    content: '';
    position: fixed;
    bottom: 0; left: 0; right: 0;
    height: 120px;
    background:
        linear-gradient(to top, rgba(10,14,26,0.9), transparent),
        repeating-linear-gradient(90deg,
            transparent 0px, transparent 18px,
            rgba(0,212,255,0.06) 18px, rgba(0,212,255,0.06) 20px,
            transparent 20px, transparent 38px,
            rgba(0,255,136,0.04) 38px, rgba(0,255,136,0.04) 40px
        );
    pointer-events: none;
    z-index: 0;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1b2a 0%, #0a1628 100%) !important;
    border-right: 1px solid rgba(0,212,255,0.2);
}

/* Main block */
[data-testid="block-container"] { position: relative; z-index: 1; }

/* ── TITLE ── */
h1 { color: #00d4ff !important; text-shadow: 0 0 30px rgba(0,212,255,0.4); }
h2, h3 { color: #e2e8f0 !important; }
p, label, .stMarkdown { color: #cbd5e1 !important; }

/* ── KPI METRIC CARDS ── */
[data-testid="metric-container"] {
    background: linear-gradient(135deg, rgba(13,27,42,0.9) 0%, rgba(15,36,64,0.9) 100%);
    border: 1px solid rgba(0,212,255,0.3);
    border-radius: 16px;
    padding: 16px !important;
    box-shadow: 0 0 20px rgba(0,212,255,0.1), inset 0 1px 0 rgba(255,255,255,0.05);
}
[data-testid="metric-container"] label { color: #94a3b8 !important; font-size: 13px !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #00d4ff !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
}

/* ── CHART BORDERS — each chart gets a unique glowing border ── */
.chart-line {
    border: 2px solid #00d4ff;
    border-radius: 20px;
    padding: 18px 12px 8px;
    background: rgba(0,212,255,0.04);
    box-shadow: 0 0 24px rgba(0,212,255,0.15), inset 0 1px 0 rgba(0,212,255,0.1);
    margin-bottom: 8px;
}
.chart-candle {
    border: 2px solid #a78bfa;
    border-radius: 20px;
    padding: 18px 12px 8px;
    background: rgba(167,139,250,0.04);
    box-shadow: 0 0 24px rgba(167,139,250,0.15), inset 0 1px 0 rgba(167,139,250,0.1);
    margin-bottom: 8px;
}
.chart-bar {
    border: 2px solid #34d399;
    border-radius: 20px;
    padding: 18px 12px 8px;
    background: rgba(52,211,153,0.04);
    box-shadow: 0 0 24px rgba(52,211,153,0.15), inset 0 1px 0 rgba(52,211,153,0.1);
    margin-bottom: 8px;
}
.chart-scatter {
    border: 2px solid #fb923c;
    border-radius: 20px;
    padding: 18px 12px 8px;
    background: rgba(251,146,60,0.04);
    box-shadow: 0 0 24px rgba(251,146,60,0.15), inset 0 1px 0 rgba(251,146,60,0.1);
    margin-bottom: 8px;
}
.chart-area {
    border: 2px solid #f472b6;
    border-radius: 20px;
    padding: 18px 12px 8px;
    background: rgba(244,114,182,0.04);
    box-shadow: 0 0 24px rgba(244,114,182,0.15), inset 0 1px 0 rgba(244,114,182,0.1);
    margin-bottom: 8px;
}
.chart-heatmap {
    border: 2px solid #fbbf24;
    border-radius: 20px;
    padding: 18px 12px 8px;
    background: rgba(251,191,36,0.04);
    box-shadow: 0 0 24px rgba(251,191,36,0.15), inset 0 1px 0 rgba(251,191,36,0.1);
    margin-bottom: 8px;
}
.chart-alert {
    border: 2px solid #f87171;
    border-radius: 20px;
    padding: 18px 12px 8px;
    background: rgba(248,113,113,0.04);
    box-shadow: 0 0 24px rgba(248,113,113,0.15), inset 0 1px 0 rgba(248,113,113,0.1);
    margin-bottom: 8px;
}

/* Chart explanation text */
.chart-caption {
    color: #64748b !important;
    font-size: 13px;
    font-style: italic;
    margin-top: 4px;
    padding: 0 6px 8px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}

/* Sidebar labels */
[data-testid="stSidebar"] label { color: #94a3b8 !important; }
[data-testid="stSidebar"] .stSelectbox, [data-testid="stSidebar"] .stMultiSelect { color: #e2e8f0; }

/* Refresh button */
.stButton > button {
    background: linear-gradient(135deg, #0ea5e9, #6366f1) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 8px 24px !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 15px rgba(14,165,233,0.3) !important;
}

/* Divider */
hr { border-color: rgba(0,212,255,0.15) !important; }

/* Dataframe */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(248,113,113,0.3) !important;
    border-radius: 12px !important;
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)

# ── Plotly dark template base ─────────────────────────────────────────────────
PLOT_BG   = "rgba(10,14,26,0)"
PAPER_BG  = "rgba(10,14,26,0)"
GRID_CLR  = "rgba(255,255,255,0.06)"
FONT_CLR  = "#94a3b8"

def base_layout(**kwargs):
    return dict(
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color=FONT_CLR, family="Inter, sans-serif"),
        xaxis=dict(gridcolor=GRID_CLR, linecolor="rgba(255,255,255,0.1)", tickfont=dict(size=11)),
        yaxis=dict(gridcolor=GRID_CLR, linecolor="rgba(255,255,255,0.1)", tickfont=dict(size=11)),
        margin=dict(l=12, r=12, t=24, b=12),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
        **kwargs
    )

# ── Per-chart color palettes (distinct for each chart) ────────────────────────
COLORS_LINE    = ["#00d4ff", "#a78bfa", "#34d399", "#fb923c", "#f472b6", "#fbbf24"]
COLORS_CANDLE  = {"up": "#34d399", "down": "#f87171", "wick_up": "#6ee7b7", "wick_down": "#fca5a5"}
COLORS_BAR     = ["#34d399", "#fb923c", "#a78bfa", "#f472b6", "#fbbf24", "#00d4ff"]
COLORS_SCATTER = ["#fb923c", "#00d4ff", "#f472b6", "#34d399", "#a78bfa", "#fbbf24"]
COLORS_AREA    = ["#f472b6", "#c084fc", "#fb7185", "#e879f9", "#f9a8d4", "#f0abfc"]
COLORS_HEATMAP = "RdYlGn"

# ── Title ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:1.5rem 0 0.5rem;">
  <h1 style="font-size:2.4rem;margin:0;">📈 Live Stock Price Dashboard</h1>
  <p style="color:#64748b;font-size:0.95rem;margin-top:6px;">
    Real-time market intelligence · Auto-refresh · Yahoo Finance
  </p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Dashboard Controls")
    selected = st.multiselect("🏷️ Select Tickers", TICKERS, default=["AAPL","MSFT","TSLA"])
    period   = st.selectbox("📅 Period", ["7d","14d","30d","90d"], index=2)
    interval = st.selectbox("⏱️ Interval", ["1d","1h","5m"], index=0)
    refresh  = st.slider("🔄 Auto-refresh (min)", 5, 60, 30)
    st.divider()
    st.markdown("<span style='color:#475569;font-size:12px;'>Data: Yahoo Finance · yfinance</span>", unsafe_allow_html=True)

# ── Load Data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=refresh * 60)
def load_all(tickers, period, interval):
    return {t: get_stock_data(t, period, interval) for t in tickers}

with st.spinner("⚡ Fetching live market data..."):
    data = load_all(tuple(selected), period, interval)

# ── KPI Row ───────────────────────────────────────────────────────────────────
kpi_cols = st.columns(len(selected))
for i, sym in enumerate(selected):
    df  = data[sym]
    cur = df["Close"].iloc[-1]
    prv = df["Close"].iloc[-2]
    chg = cur - prv
    pct = chg / prv * 100
    kpi_cols[i].metric(sym, f"${cur:.2f}", f"{chg:+.2f} ({pct:+.2f}%)")

st.divider()

# ════════════════════════════════════════════════════════════════
# CHART 1 — Line Chart: Price Trend
# ════════════════════════════════════════════════════════════════
st.markdown('<div class="chart-line">', unsafe_allow_html=True)
st.subheader("📉 Closing Price Trend")
fig_line = go.Figure()
for i, sym in enumerate(selected):
    df  = data[sym]
    clr = COLORS_LINE[i % len(COLORS_LINE)]
    fig_line.add_trace(go.Scatter(
        x=df.index, y=df["Close"], mode="lines", name=sym,
        line=dict(color=clr, width=2.5),
        hovertemplate=f"<b>{sym}</b><br>Date: %{{x|%b %d}}<br>Close: $%{{y:.2f}}<extra></extra>"
    ))
    fig_line.add_trace(go.Scatter(
        x=df.index, y=df["7D_Avg"], mode="lines", name=f"{sym} 7D Avg",
        line=dict(color=clr, width=1, dash="dot"), opacity=0.5,
        hovertemplate=f"<b>{sym} 7D Avg</b><br>$%{{y:.2f}}<extra></extra>"
    ))
fig_line.update_layout(**base_layout(height=360, hovermode="x unified"))
st.plotly_chart(fig_line, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<p class="chart-caption">📌 Solid lines show daily closing prices; dotted lines show the 7-day rolling average to highlight short-term momentum.</p>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# CHART 2 — Candlestick Chart
# ════════════════════════════════════════════════════════════════
st.markdown('<div class="chart-candle">', unsafe_allow_html=True)
st.subheader("🕯️ Candlestick Chart (OHLC)")
cs_sym = st.selectbox("Select ticker", selected, key="cs")
df_cs  = data[cs_sym]
fig_cs = go.Figure(go.Candlestick(
    x=df_cs.index,
    open=df_cs["Open"], high=df_cs["High"],
    low=df_cs["Low"],   close=df_cs["Close"],
    name=cs_sym,
    increasing_line_color=COLORS_CANDLE["up"],
    decreasing_line_color=COLORS_CANDLE["down"],
    increasing_fillcolor=COLORS_CANDLE["up"],
    decreasing_fillcolor=COLORS_CANDLE["down"],
))
fig_cs.update_layout(**base_layout(height=360, xaxis_rangeslider_visible=False))
st.plotly_chart(fig_cs, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<p class="chart-caption">📌 Green candles = price closed higher than open (bullish); Red candles = price closed lower (bearish). Wicks show intraday High/Low range.</p>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# CHART 3 & 4 — Bar + Scatter (side by side)
# ════════════════════════════════════════════════════════════════
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="chart-bar">', unsafe_allow_html=True)
    st.subheader("📊 Daily Return % (Bar)")
    all_df = pd.concat([data[s].assign(Symbol=s) for s in selected]).reset_index()
    fig_bar = go.Figure()
    for i, sym in enumerate(selected):
        sub = all_df[all_df["Symbol"] == sym]
        fig_bar.add_trace(go.Bar(
            x=sub["Date"], y=sub["Daily_Return"], name=sym,
            marker_color=COLORS_BAR[i % len(COLORS_BAR)],
            hovertemplate=f"<b>{sym}</b><br>%{{y:+.2f}}%<extra></extra>"
        ))
    fig_bar.update_layout(**base_layout(height=320, barmode="group"))
    st.plotly_chart(fig_bar, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<p class="chart-caption">📌 Each bar represents the daily % price change per ticker — positive bars signal gains, negative bars signal losses for that session.</p>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="chart-scatter">', unsafe_allow_html=True)
    st.subheader("🔵 Volatility vs Avg Return")
    summary = pd.DataFrame([{
        "Symbol":     s,
        "Avg_Return": data[s]["Daily_Return"].mean(),
        "Volatility": data[s]["Volatility"].mean(),
        "Avg_Volume": data[s]["Volume"].mean()
    } for s in selected])
    fig_sc = go.Figure()
    for i, row in summary.iterrows():
        fig_sc.add_trace(go.Scatter(
            x=[row["Volatility"]], y=[row["Avg_Return"]],
            mode="markers+text",
            name=row["Symbol"],
            text=[row["Symbol"]],
            textposition="top center",
            marker=dict(size=max(12, row["Avg_Volume"]/2e7), color=COLORS_SCATTER[i % len(COLORS_SCATTER)],
                        line=dict(color="white", width=1)),
            hovertemplate=f"<b>{row['Symbol']}</b><br>Volatility: %{{x:.2f}}<br>Avg Return: %{{y:.2f}}%<extra></extra>"
        ))
    fig_sc.update_layout(**base_layout(height=320, showlegend=False))
    st.plotly_chart(fig_sc, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<p class="chart-caption">📌 Bubble size reflects average trading volume — stocks in the upper-left quadrant offer higher returns with lower risk.</p>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# CHART 5 — Area Chart: Volume
# ════════════════════════════════════════════════════════════════
st.markdown('<div class="chart-area">', unsafe_allow_html=True)
st.subheader("📐 Volume Over Time (Area Chart)")
fig_area = go.Figure()
for i, sym in enumerate(selected):
    df  = data[sym]
    clr = COLORS_AREA[i % len(COLORS_AREA)]
    fig_area.add_trace(go.Scatter(
        x=df.index, y=df["Volume"], fill="tozeroy", mode="lines",
        name=sym, line=dict(color=clr, width=1.5),
        fillcolor=clr.replace(")", ",0.15)").replace("rgb", "rgba") if clr.startswith("rgb") else clr + "26",
        hovertemplate=f"<b>{sym}</b><br>Vol: %{{y:,.0f}}<extra></extra>"
    ))
fig_area.update_layout(**base_layout(height=300))
st.plotly_chart(fig_area, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<p class="chart-caption">📌 Volume spikes often precede or confirm major price moves — elevated volume with a price surge signals strong institutional interest.</p>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# CHART 6 — Heatmap: Daily Returns by Day
# ════════════════════════════════════════════════════════════════
st.markdown('<div class="chart-heatmap">', unsafe_allow_html=True)
st.subheader("🌡️ Return Heatmap (by Calendar Day)")
hm_sym = st.selectbox("Ticker for heatmap", selected, key="hm")
df_hm  = data[hm_sym].copy()
df_hm["DayName"] = df_hm.index.strftime("%a")
df_hm["Week"]    = df_hm.index.isocalendar().week.values
pivot = df_hm.pivot_table(values="Daily_Return", index="DayName", columns="Week", aggfunc="mean")
day_order = ["Mon","Tue","Wed","Thu","Fri"]
pivot = pivot.reindex([d for d in day_order if d in pivot.index])
fig_hm = go.Figure(go.Heatmap(
    z=pivot.values, x=[f"W{c}" for c in pivot.columns],
    y=pivot.index.tolist(),
    colorscale=COLORS_HEATMAP,
    hovertemplate="Day: %{y}<br>Week: %{x}<br>Return: %{z:.2f}%<extra></extra>",
    zmid=0
))
fig_hm.update_layout(**base_layout(height=280))
st.plotly_chart(fig_hm, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<p class="chart-caption">📌 Green cells = positive return days, Red = negative — reveals weekly seasonality patterns and the best/worst performing days of the week.</p>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# CHART 7 — Anomaly Alerts
# ════════════════════════════════════════════════════════════════
st.markdown('<div class="chart-alert">', unsafe_allow_html=True)
st.subheader("🚨 Anomaly Alerts (Z-Score > 2σ)")
alerts = []
for sym in selected:
    df = data[sym].copy()
    df["Z"] = (df["Daily_Return"] - df["Daily_Return"].mean()) / df["Daily_Return"].std()
    flagged = df[abs(df["Z"]) > 2][["Close","Daily_Return","Volatility","Z"]].copy()
    flagged["Symbol"] = sym
    flagged["Signal"] = flagged["Daily_Return"].apply(lambda x: "🔺 SURGE" if x > 0 else "🔻 DROP")
    alerts.append(flagged)

if alerts:
    result = pd.concat(alerts).sort_index(ascending=False).head(20)
    result = result[["Symbol","Close","Daily_Return","Volatility","Z","Signal"]]
    result.columns = ["Ticker","Close $","Daily Return %","Volatility","Z-Score","Signal"]
    result["Close $"] = result["Close $"].map("${:.2f}".format)
    result["Daily Return %"] = result["Daily Return %"].map("{:+.2f}%".format)
    result["Z-Score"] = result["Z-Score"].map("{:.2f}".format)
    st.dataframe(result, use_container_width=True)
else:
    st.success("✅ No anomalies detected in the selected period.")
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<p class="chart-caption">📌 Flags any trading day where the return exceeded 2 standard deviations from the mean — these are statistically unusual price events worth investigating.</p>', unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
fcol1, fcol2 = st.columns([3, 1])
with fcol1:
    st.markdown(f"<span style='color:#334155;font-size:12px;'>⏱️ Auto-refresh every {refresh} min · Last run: {pd.Timestamp.now().strftime('%H:%M:%S IST')}</span>", unsafe_allow_html=True)
with fcol2:
    if st.button("🔄 Refresh Now"):
        st.cache_data.clear()
        st.rerun()

time.sleep(refresh * 60)
st.rerun()
