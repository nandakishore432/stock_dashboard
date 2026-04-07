import yfinance as yf
import pandas as pd

TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA']

def get_stock_data(symbol: str, period: str = '30d', interval: str = '1d') -> pd.DataFrame:
    """Fetch OHLCV data from Yahoo Finance via yfinance."""
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df['Symbol'] = symbol
    df['Daily_Return'] = df['Close'].pct_change() * 100
    df['7D_Avg'] = df['Close'].rolling(7).mean()
    df['Volatility'] = df['Close'].rolling(7).std()
    return df

def get_info(symbol: str) -> dict:
    """Fetch static info: market cap, sector, etc."""
    return yf.Ticker(symbol).info

def build_date_table(df: pd.DataFrame) -> pd.DataFrame:
    """Creates a Date dimension table from the index."""
    dates = df.index.unique()
    return pd.DataFrame({
        'Date':       dates,
        'Year':       dates.year,
        'Month':      dates.strftime('%b %Y'),
        'Week':       dates.isocalendar().week.values,
        'DayOfWeek':  dates.strftime('%a'),
        'Quarter':    dates.quarter,
        'IsWeekday':  dates.weekday < 5
    })
