"""
Quinn Finance Framework - Technical Analysis Module
技术分析：MA、RSI、MACD、布林带、支撑阻力
"""

import math
from typing import List, Tuple, Optional, Dict


class TechnicalAnalyzer:
    """技术分析器"""
    
    def __init__(self):
        self.indicators = {}
    
    def calculate_ma(self, prices: List[float], period: int) -> Optional[float]:
        """计算移动平均线"""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period
    
    def calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """计算指数移动平均线"""
        if len(prices) < period:
            return []
        
        k = 2 / (period + 1)
        ema_values = [prices[0]]
        
        for price in prices[1:]:
            ema_values.append(price * k + ema_values[-1] * (1 - k))
        
        return ema_values
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """计算RSI指标"""
        if len(prices) < period + 1:
            return None
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def calculate_macd(self, prices: List[float], 
                     fast: int = 12, 
                     slow: int = 26, 
                     signal: int = 9) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        计算MACD
        返回: (macd_line, signal_line, histogram)
        """
        if len(prices) < slow + signal:
            return None, None, None
        
        ema_fast = self.calculate_ema(prices, fast)
        ema_slow = self.calculate_ema(prices, slow)
        
        macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
        
        # Signal line
        k = 2 / (signal + 1)
        signal_line = [macd_line[0]]
        for val in macd_line[1:]:
            signal_line.append(val * k + signal_line[-1] * (1 - k))
        
        histogram = [m - s for m, s in zip(macd_line, signal_line)]
        
        return macd_line[-1], signal_line[-1], histogram[-1]
    
    def calculate_bollinger_bands(self, prices: List[float], 
                                  period: int = 20, 
                                  std_dev: int = 2) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        计算布林带
        返回: (upper, middle, lower)
        """
        if len(prices) < period:
            return None, None, None
        
        middle = sum(prices[-period:]) / period
        
        # 计算标准差
        variance = sum((p - middle) ** 2 for p in prices[-period:]) / period
        std = math.sqrt(variance)
        
        upper = middle + std_dev * std
        lower = middle - std_dev * std
        
        return upper, middle, lower
    
    def calculate_support_resistance(self, highs: List[float], 
                                    lows: List[float], 
                                    closes: List[float],
                                    lookback: int = 7) -> Dict[str, float]:
        """
        计算支撑和阻力位
        """
        if len(highs) < lookback or len(lows) < lookback:
            return {}
        
        # 近期高低点
        recent_high = max(highs[-lookback:])
        recent_low = min(lows[-lookback:])
        
        # Pivot point
        if len(closes) >= 2:
            pivot = (highs[-2] + lows[-2] + closes[-2]) / 3
        else:
            pivot = closes[-1]
        
        # R1, R2, S1, S2
        r1 = 2 * pivot - lows[-2] if len(lows) >= 2 else pivot
        s1 = 2 * pivot - highs[-2] if len(highs) >= 2 else pivot
        
        return {
            'pivot': pivot,
            'r1': r1,
            'r2': recent_high,
            's1': s1,
            's2': recent_low
        }
    
    def analyze(self, ohlc_data: List[List[float]]) -> Dict:
        """
        综合技术分析
        ohlc_data: [[open, high, low, close], ...]
        """
        if not ohlc_data or len(ohlc_data) < 30:
            return {}
        
        opens = [k[0] for k in ohlc_data]
        highs = [k[1] for k in ohlc_data]
        lows = [k[2] for k in ohlc_data]
        closes = [k[3] for k in ohlc_data]
        
        current_price = closes[-1]
        
        # 计算指标
        ma5 = self.calculate_ma(closes, 5)
        ma10 = self.calculate_ma(closes, 10)
        ma20 = self.calculate_ma(closes, 20)
        ma60 = self.calculate_ma(closes, 60) if len(closes) >= 60 else None
        
        rsi = self.calculate_rsi(closes)
        macd, signal_line, histogram = self.calculate_macd(closes)
        upper, middle, lower = self.calculate_bollinger_bands(closes)
        
        sr_levels = self.calculate_support_resistance(highs, lows, closes)
        
        # 趋势判断
        if current_price > ma20 and (ma20 > ma60 if ma60 else True):
            trend = "上升趋势"
        elif current_price < ma20 and (ma20 < ma60 if ma60 else True):
            trend = "下降趋势"
        else:
            trend = "震荡整理"
        
        # RSI 信号
        if rsi:
            if rsi > 70:
                rsi_signal = "超买区域，警惕回调"
            elif rsi < 30:
                rsi_signal = "超卖区域，关注反弹"
            elif rsi > 60:
                rsi_signal = "偏强区域，谨慎追多"
            elif rsi < 40:
                rsi_signal = "偏弱区域，观望为主"
            else:
                rsi_signal = "中性区域"
        else:
            rsi_signal = "数据不足"
        
        # MACD 信号
        if histogram:
            if histogram > 0:
                macd_signal = "多方动能增强"
            else:
                macd_signal = "空方动能增强"
        else:
            macd_signal = "数据不足"
        
        return {
            'current_price': current_price,
            'trend': trend,
            'ma': {
                'ma5': ma5,
                'ma10': ma10,
                'ma20': ma20,
                'ma60': ma60
            },
            'rsi': {
                'value': rsi,
                'signal': rsi_signal
            },
            'macd': {
                'macd': macd,
                'signal': signal_line,
                'histogram': histogram,
                'signal_text': macd_signal
            },
            'bollinger': {
                'upper': upper,
                'middle': middle,
                'lower': lower
            },
            'support_resistance': sr_levels
        }


if __name__ == "__main__":
    # 简单测试
    import urllib.request
    import json
    
    # 获取BTC K线
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/ohlc?vs_currency=usd&days=30"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as response:
        klines = json.loads(response.read())
    
    analyzer = TechnicalAnalyzer()
    result = analyzer.analyze(klines)
    
    print(f"当前价格: ${result['current_price']:,.2f}")
    print(f"趋势: {result['trend']}")
    print(f"RSI(14): {result['rsi']['value']:.1f} - {result['rsi']['signal']}")
    print(f"MACD: {result['macd']['signal_text']}")