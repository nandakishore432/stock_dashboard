import yfinance as yf
import pandas as pd

TICKERS = ['AAPL', 'MSFT', 'TSLA', 'GOOGL', 'AMZN', 'META', 'NVDA', 'NFLX']

def get_stock_data(ticker: str, period: str = '30d', interval: str = '1d') -> pd.DataFrame:
    df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)

    # ✅ Fix 1: Flatten MultiIndex columns (yfinance >= 0.2.x)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # ✅ Fix 2: Drop rows with no Close price
    df = df.dropna(subset=['Close'])

    # ✅ Fix 3: Add Symbol column for concat in charts
    df['Symbol'] = ticker
    df.index.name = 'Date'

    # ✅ Fix 4: Compute derived columns with min_periods=1 to avoid NaN
    df['Daily_Return'] = df['Close'].pct_change() * 100
    df['Volatility'] = df['Daily_Return'].rolling(7, min_periods=1).std()
    df['7D_Avg'] = df['Close'].rolling(7, min_periods=1).mean()

    return df


def get_info(ticker: str) -> dict:
    try:
        return yf.Ticker(ticker).info
    except Exception:
        return {}
