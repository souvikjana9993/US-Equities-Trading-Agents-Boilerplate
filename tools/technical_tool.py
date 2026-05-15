import yfinance as yf
import pandas as pd
import numpy as np
import talib
import logging
from typing import Dict, Any, List
from strands import tool

logger = logging.getLogger("TechnicalTool")

@tool
def get_comprehensive_technical_analysis(ticker: str) -> str:
    """
    Comprehensive technical analysis using TA-Lib.
    Calculates RSI, MACD, Moving Averages, Bollinger Bands, and more for US stocks.
    """
    logger.info(f"Fetching comprehensive technicals for {ticker}...")
    
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="2y")  # Need 2 years for some indicators
        
        if hist.empty or len(hist) < 50:
            return f"Error: Insufficient data for {ticker}"
        
        close = hist['Close']
        high = hist['High']
        low = hist['Low']
        volume = hist['Volume']
        
        # Handle MultiIndex columns from yfinance (common in recent versions)
        if isinstance(close, pd.DataFrame):
            if close.shape[1] == 1:
                close = close.iloc[:, 0]
                high = high.iloc[:, 0] if isinstance(high, pd.DataFrame) else high
                low = low.iloc[:, 0] if isinstance(low, pd.DataFrame) else low
                volume = volume.iloc[:, 0] if isinstance(volume, pd.DataFrame) else volume
            else:
                close = close.iloc[:, -1]
                high = high.iloc[:, -1] if isinstance(high, pd.DataFrame) else high
                low = low.iloc[:, -1] if isinstance(low, pd.DataFrame) else low
                volume = volume.iloc[:, -1] if isinstance(volume, pd.DataFrame) else volume
        
        # Convert to numpy arrays with float64 type (TA-Lib requirement)
        close_arr = close.values.astype('float64')
        high_arr = high.values.astype('float64')
        low_arr = low.values.astype('float64')
        volume_arr = volume.values.astype('float64')
        
        current_price = float(close_arr[-1])
        
        # ==================== TREND INDICATORS ====================
        sma_50 = talib.SMA(close_arr, timeperiod=50)
        sma_100 = talib.SMA(close_arr, timeperiod=100)
        sma_200 = talib.SMA(close_arr, timeperiod=200)
        sma_365 = talib.SMA(close_arr, timeperiod=365)
        
        ema_20 = talib.EMA(close_arr, timeperiod=20)
        ema_50 = talib.EMA(close_arr, timeperiod=50)
        
        macd, macd_signal, macd_hist = talib.MACD(close_arr, fastperiod=26, slowperiod=52, signalperiod=9)
        psar = talib.SAR(high_arr, low_arr)
        adx = talib.ADX(high_arr, low_arr, close_arr, timeperiod=21)
        
        # ==================== MOMENTUM OSCILLATORS ====================
        rsi_21 = talib.RSI(close_arr, timeperiod=21)
        rsi_14 = talib.RSI(close_arr, timeperiod=14)
        slowk, slowd = talib.STOCH(high_arr, low_arr, close_arr, 
                                   fastk_period=21, slowk_period=5, slowk_matype=0, 
                                   slowd_period=5, slowd_matype=0)
        cci = talib.CCI(high_arr, low_arr, close_arr, timeperiod=21)
        willr = talib.WILLR(high_arr, low_arr, close_arr, timeperiod=21)
        roc = talib.ROC(close_arr, timeperiod=21)
        
        # ==================== VOLATILITY INDICATORS ====================
        upper_bb, middle_bb, lower_bb = talib.BBANDS(close_arr, timeperiod=30, nbdevup=2, nbdevdn=2, matype=0)
        atr = talib.ATR(high_arr, low_arr, close_arr, timeperiod=14)
        
        # ==================== VOLUME INDICATORS ====================
        obv = talib.OBV(close_arr, volume_arr)
        
        # ==================== PIVOT POINTS ====================
        last_high = high_arr[-1]
        last_low = low_arr[-1]
        last_close = close_arr[-1]
        pp = (last_high + last_low + last_close) / 3
        r1 = 2 * pp - last_low
        s1 = 2 * pp - last_high
        
        # Helper for results
        def safe_value(arr, idx=-1):
            if arr is None or (hasattr(arr, '__len__') and len(arr) == 0): return None
            try:
                val = arr[idx] if hasattr(arr, '__getitem__') else arr
                val = float(val)
                return val if np.isfinite(val) else None
            except: return None

        results = {
            "ticker": ticker,
            "current_price": round(float(current_price), 2),
            "sma": {"50": round(safe_value(sma_50) or 0, 2), "200": round(safe_value(sma_200) or 0, 2)},
            "rsi": round(safe_value(rsi_14) or 0, 2),
            "macd": {"line": round(safe_value(macd) or 0, 4), "hist": round(safe_value(macd_hist) or 0, 4)},
            "bollinger": {"upper": round(safe_value(upper_bb) or 0, 2), "lower": round(safe_value(lower_bb) or 0, 2)},
            "pivot_points": {"pp": round(float(pp), 2), "r1": round(float(r1), 2), "s1": round(float(s1), 2)},
            "overall_signal": "BULLISH" if current_price > (safe_value(sma_50) or 0) else "BEARISH"
        }
        
        return str(results)
        
    except Exception as e:
        logger.error(f"Error in comprehensive technicals: {e}")
        return f"Error: {str(e)}"
