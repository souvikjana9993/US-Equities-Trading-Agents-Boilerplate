from strands import tool
import yfinance as yf
import pandas as pd
import numpy as np
import talib
import logging
from typing import Dict, Any, List

logger = logging.getLogger("TechnicalTool")

@tool
def get_comprehensive_technical_analysis(ticker: str) -> str:
    """
    Comprehensive technical analysis using TA-Lib.
    Similar to investing.com technical analysis page.
    """
    # No auto-suffixing to avoid breaking US tickers like TSM
    ns_ticker = ticker
    logger.info(f"Fetching comprehensive technicals for {ns_ticker}...")
    
    try:
        stock = yf.Ticker(ns_ticker)
        hist = stock.history(period="1y")
        
        if hist.empty or len(hist) < 50:
            return "Error: Insufficient data"
        
        close = hist['Close']
        high = hist['High']
        low = hist['Low']
        volume = hist['Volume']
        
        if isinstance(close, pd.DataFrame):
            close, high, low, volume = close.iloc[:, -1], high.iloc[:, -1], low.iloc[:, -1], volume.iloc[:, -1]
        
        close_arr = close.values.astype('float64')
        high_arr = high.values.astype('float64')
        low_arr = low.values.astype('float64')
        volume_arr = volume.values.astype('float64')
        current_price = float(close_arr[-1])
        
        # HELPERS (From User Request)
        def safe_value(arr, idx=-1):
            if arr is None or (hasattr(arr, '__len__') and len(arr) == 0): return None
            try:
                val = arr[idx] if hasattr(arr, '__getitem__') else arr
                val = float(val)
                return val if not np.isnan(val) and not np.isinf(val) else None
            except: return None

        def safe_round(val, decimals=2):
            if val is None: return None
            try: return round(float(val), decimals)
            except: return None

        def trend_direction(current, ma):
            if current is None or ma is None: return "NEUTRAL"
            return "BULLISH" if current > ma else "BEARISH"

        # INDICATORS
        sma_50 = talib.SMA(close_arr, 50)
        sma_100 = talib.SMA(close_arr, 100)
        sma_200 = talib.SMA(close_arr, 200)
        ema_20 = talib.EMA(close_arr, 20)
        ema_50 = talib.EMA(close_arr, 50)
        macd, macd_signal, macd_hist = talib.MACD(close_arr, 26, 52, 9)
        rsi_21 = talib.RSI(close_arr, 21)
        rsi_14 = talib.RSI(close_arr, 14)
        slowk, slowd = talib.STOCH(high_arr, low_arr, close_arr, 21, 5, 0, 5, 0)
        cci = talib.CCI(high_arr, low_arr, close_arr, 21)
        willr = talib.WILLR(high_arr, low_arr, close_arr, 21)
        upper_bb, middle_bb, lower_bb = talib.BBANDS(close_arr, 30, 2, 2)
        atr = talib.ATR(high_arr, low_arr, close_arr, 14)
        adx = talib.ADX(high_arr, low_arr, close_arr, 21)
        obv = talib.OBV(close_arr, volume_arr)
        
        # PIVOTS
        last_high, last_low, last_close = high_arr[-1], low_arr[-1], close_arr[-1]
        pp = (last_high + last_low + last_close) / 3
        r1, s1 = 2 * pp - last_low, 2 * pp - last_high
        r2, s2 = pp + (last_high - last_low), pp - (last_high - last_low)
        r3, s3 = last_high + 2 * (pp - last_low), last_low - 2 * (last_high - pp)

        results = {
            "ticker": ticker,
            "current_price": current_price,
            "timestamp": str(close.index[-1]),
            "sma": {
                "sma_50": safe_round(safe_value(sma_50)),
                "sma_100": safe_round(safe_value(sma_100)),
                "sma_200": safe_round(safe_value(sma_200)),
            },
            "ema": {
                "ema_20": safe_round(safe_value(ema_20)),
                "ema_50": safe_round(safe_value(ema_50)),
            },
            "trend": {
                "price_vs_sma50": trend_direction(current_price, safe_value(sma_50)),
                "price_vs_sma200": trend_direction(current_price, safe_value(sma_200)),
                "sma_50_vs_200": "GOLDEN CROSS" if (safe_value(sma_50) and safe_value(sma_200) and safe_value(sma_50) > safe_value(sma_200)) else "DEATH CROSS" if (safe_value(sma_50) and safe_value(sma_200) and safe_value(sma_50) < safe_value(sma_200)) else "NEUTRAL",
            },
            "macd": {
                "macd_line": safe_round(safe_value(macd), 4),
                "signal_line": safe_round(safe_value(macd_signal), 4),
                "histogram": safe_round(safe_value(macd_hist), 4),
            },
            "rsi": {
                "rsi_21": safe_round(safe_value(rsi_21)),
                "rsi_14": safe_round(safe_value(rsi_14)),
            },
            "stochastic": {"k": safe_round(safe_value(slowk)), "d": safe_round(safe_value(slowd))},
            "bollinger_bands": {
                "upper": safe_round(safe_value(upper_bb)),
                "middle": safe_round(safe_value(middle_bb)),
                "lower": safe_round(safe_value(lower_bb)),
            },
            "atr": safe_round(safe_value(atr)),
            "adx": safe_round(safe_value(adx)),
            "cci": safe_round(safe_value(cci)),
            "williams_r": safe_round(safe_value(willr)),
            "pivot_points": {
                "pp": safe_round(pp), "r1": safe_round(r1), "r2": safe_round(r2), "r3": safe_round(r3),
                "s1": safe_round(s1), "s2": safe_round(s2), "s3": safe_round(s3)
            },
            "volume": {
                "current": int(safe_value(volume_arr[-1]) or 0),
                "avg_30": round(float(volume_arr[-30:].mean()), 0),
                "obv": safe_round(safe_value(obv), 0),
            },
        }
        return str(results)
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"Error: {str(e)}"
