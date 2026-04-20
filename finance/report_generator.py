"""
Quinn Finance Framework - Report Generator v2
专业金融分析报告生成器
集成：加密货币 + 贵金属 + 全球指数
"""

import urllib.request
import json
import math
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class TechnicalAnalyzer:
    """技术分析器"""
    
    @staticmethod
    def calculate_ma(prices: List[float], period: int) -> Optional[float]:
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> List[float]:
        if len(prices) < period:
            return []
        k = 2 / (period + 1)
        ema_values = [prices[0]]
        for price in prices[1:]:
            ema_values.append(price * k + ema_values[-1] * (1 - k))
        return ema_values
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
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
    
    @staticmethod
    def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        if len(prices) < slow + signal:
            return None, None, None
        ema_fast = TechnicalAnalyzer.calculate_ema(prices, fast)
        ema_slow = TechnicalAnalyzer.calculate_ema(prices, slow)
        macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
        k = 2 / (signal + 1)
        signal_line = [macd_line[0]]
        for val in macd_line[1:]:
            signal_line.append(val * k + signal_line[-1] * (1 - k))
        histogram = [m - s for m, s in zip(macd_line, signal_line)]
        return macd_line[-1], signal_line[-1], histogram[-1]
    
    @staticmethod
    def calculate_bollinger(prices: List[float], period: int = 20) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        if len(prices) < period:
            return None, None, None
        middle = sum(prices[-period:]) / period
        variance = sum((p - middle) ** 2 for p in prices[-period:]) / period
        std = math.sqrt(variance)
        return middle + 2 * std, middle, middle - 2 * std


from finance.data_fetcher import DataFetcher


class ReportGenerator:
    """报告生成器"""
    
    # 简单内存缓存（同一进程内有效）
    _cache: Dict[str, tuple] = {}
    _cache_ttl: int = 120  # 缓存有效期（秒）
    
    def __init__(self, use_akshare: bool = False):
        self.fetcher = DataFetcher()
        self.analyzer = TechnicalAnalyzer()
        self.use_akshare = use_akshare
    
    def _get_ashare_summary(self) -> Dict:
        """获取A股主要指数 (使用akshare，可选)"""
        try:
            import sys
            sys.path.insert(0, '/Users/Zhuanz/Library/Python/3.14/lib/python/site-packages')
            import akshare as ak
            
            df = ak.stock_zh_index_spot_em()
            major_names = ['上证指数', '深证成指', '创业板', '沪深300', '科创50', '上证50']
            filtered = df[df['名称'].str.contains('|'.join(major_names), na=False)]
            result = {}
            for _, row in filtered.iterrows():
                result[row['名称']] = {
                    'price': row.get('最新价', 0),
                    'change': row.get('涨跌幅', 0)
                }
            return result
        except:
            return {}
    
    def _format_emoji(self, change: float) -> str:
        return "📈" if change > 0 else "📉"
    
    def _render_market_indices(self) -> str:
        """渲染全球指数模块"""
        indices = self.fetcher.get_market_indices()
        if not indices:
            return "\n🌍 【全球主要指数】\n   数据暂时不可用"
        
        lines = ["\n🌍 【全球主要指数】"]
        
        # 分区域展示（key名称直接匹配）
        regions = {
            '美国': ['S&P 500', 'NASDAQ', 'Dow Jones'],
            '欧洲': ['FTSE 100', 'DAX'],
            '亚太': ['Nikkei 225', 'Hang Seng', 'SSE 上证'],
        }
        
        for region, names in regions.items():
            lines.append(f"\n   {region}:")
            for name in names:
                if name in indices:
                    info = indices[name]
                    emoji = self._format_emoji(info['change'])
                    price_str = f"{info['price']:,.2f}"
                    lines.append(f"   {emoji} {name}: {price_str} ({info['change']:+.2f}%)")
        
        return "\n".join(lines)
    
    def generate_daily_report(self, symbols: List[str] = None) -> str:
        """生成每日分析报告（优化：减少API请求次数）"""
        if symbols is None:
            symbols = ['bitcoin', 'ethereum']
        
        # 获取数据（每个symbol一次请求，避免连续调用被限流）
        crypto_data = {}
        for sym in symbols:
            data = self.fetcher.get_crypto_prices([sym])
            if data:
                crypto_data.update(data)
        # 180天K线用于技术分析（单独一次请求）
        ohlc_data = self.fetcher.get_crypto_ohlc('bitcoin', 180)
        fear_greed = self.fetcher.get_fear_greed_index()
        metals = self.fetcher.get_precious_metals()
        
        # 处理K线
        closes = [k[4] for k in ohlc_data] if ohlc_data else []
        highs = [k[2] for k in ohlc_data] if ohlc_data else []
        lows = [k[3] for k in ohlc_data] if ohlc_data else []
        
        # 计算指标
        ma5 = self.analyzer.calculate_ma(closes, 5)
        ma10 = self.analyzer.calculate_ma(closes, 10)
        ma20 = self.analyzer.calculate_ma(closes, 20)
        ma60 = self.analyzer.calculate_ma(closes, 60)
        rsi = self.analyzer.calculate_rsi(closes)
        macd, signal_line, histogram = self.analyzer.calculate_macd(closes)
        bb_upper, bb_middle, bb_lower = self.analyzer.calculate_bollinger(closes)
        
        # 生成报告
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        lines = []
        lines.append("=" * 60)
        lines.append("    🔍 QUINN 专业金融分析报告")
        lines.append(f"    {now} UTC+8")
        lines.append("=" * 60)
        
        # ============ 加密货币 ============
        lines.append("\n📊 【加密货币】")
        for symbol, info in crypto_data.items():
            name = symbol.capitalize()
            change = info['change_24h']
            emoji = self._format_emoji(change)
            lines.append(f"   {emoji} {name}")
            lines.append(f"   ├ 价格: ${info['usd']:,.2f} / ¥{info['cny']:,.0f}")
            lines.append(f"   └ 24h: {change:+.2f}%")
        
        # ============ 全球指数 ============
        lines.append(self._render_market_indices())
        
        # ============ 恐慌贪婪指数 ============
        if fear_greed:
            if fear_greed >= 75:
                fg_signal = "极度贪婪 🔴"
            elif fear_greed >= 50:
                fg_signal = "贪婪 🟡"
            elif fear_greed >= 25:
                fg_signal = "恐惧 🔵"
            else:
                fg_signal = "极度恐惧 ⚫"
            lines.append(f"\n🌡️ 【市场情绪 - 恐慌贪婪指数】")
            lines.append(f"   指数: {fear_greed} - {fg_signal}")
        
        # ============ 贵金属 ============
        if metals:
            lines.append(f"\n🥇 【贵金属】(USD/盎司)")
            for name, info in metals.items():
                price = info.get('price', 0)
                change = info.get('change', 0)
                emoji = self._format_emoji(change)
                if price:
                    lines.append(f"   {emoji} {name}: ${price:,.2f} ({change:+.2f}%)")
        
        # ============ 技术分析 ============
        if closes:
            current = closes[-1]
            prev = closes[-2] if len(closes) > 1 else current
            
            lines.append("\n" + "-" * 60)
            lines.append("【一、BTC 技术分析】")
            lines.append("-" * 60)
            
            lines.append(f"\n📊 近期走势 ({len(closes)}根日K)")
            change_pct = ((current - prev) / prev * 100) if prev else 0
            lines.append(f"   最新收盘: ${current:,.2f} ({change_pct:+.2f}%)")
            
            # MA
            lines.append(f"\n📈 移动平均线 (MA)")
            if ma5:
                cross = "▲ 金叉" if current > ma5 and closes[-2] <= closes[-3] else "▼ 死叉" if current < ma5 and closes[-2] >= closes[-3] else ""
                lines.append(f"   MA5:  ${ma5:,.2f}  {cross}")
            if ma10:
                lines.append(f"   MA10: ${ma10:,.2f}")
            if ma20:
                lines.append(f"   MA20: ${ma20:,.2f}")
            if ma60:
                lines.append(f"   MA60: ${ma60:,.2f}")
            
            # 趋势
            if current > ma20 and (ma20 > ma60 if ma60 else True):
                trend = "上升趋势 ✅"
            elif current < ma20 and (ma20 < ma60 if ma60 else True):
                trend = "下降趋势 🔻"
            else:
                trend = "震荡整理 📊"
            lines.append(f"   趋势判断: {trend}")
            
            # RSI
            lines.append(f"\n📉 RSI 指标 (14日)")
            if rsi:
                if rsi > 70:
                    rsi_s = "超买区域 🔴 警惕回调"
                elif rsi < 30:
                    rsi_s = "超卖区域 🟢 关注反弹"
                elif rsi > 60:
                    rsi_s = "偏强区域 🟡 谨慎追多"
                elif rsi < 40:
                    rsi_s = "偏弱区域 🟡 观望为主"
                else:
                    rsi_s = "中性区域 ⚪"
                lines.append(f"   RSI(14): {rsi:.1f} - {rsi_s}")
            
            # MACD
            lines.append(f"\n📊 MACD 指标")
            if macd and signal_line and histogram is not None:
                lines.append(f"   MACD: ${macd:.2f}")
                lines.append(f"   Signal: ${signal_line:.2f}")
                lines.append(f"   Histogram: ${histogram:.2f}")
                macd_trend = "多方动能增强 🟢" if histogram > 0 else "空方动能增强 🔴"
                lines.append(f"   判断: {macd_trend}")
            
            # 布林带
            if bb_upper and bb_middle and bb_lower:
                lines.append(f"\n📊 布林带 (20日)")
                lines.append(f"   Upper: ${bb_upper:,.2f}")
                lines.append(f"   Middle: ${bb_middle:,.2f}")
                lines.append(f"   Lower: ${bb_lower:,.2f}")
                if current > bb_upper:
                    bb_signal = "价格突破上轨，注意回调风险"
                elif current < bb_lower:
                    bb_signal = "价格突破下轨，关注反弹机会"
                elif current > bb_middle:
                    bb_signal = "在中上轨运行，偏强"
                else:
                    bb_signal = "在中下轨运行，偏弱"
                lines.append(f"   信号: {bb_signal}")
            
            # 支撑阻力
            if highs and lows:
                recent_high = max(highs[-7:]) if len(highs) >= 7 else max(highs)
                recent_low = min(lows[-7:]) if len(lows) >= 7 else min(lows)
                pivot = (highs[-1] + lows[-1] + closes[-1]) / 3 if len(closes) >= 1 else current
                
                lines.append("\n" + "-" * 60)
                lines.append("【二、支撑与阻力】")
                lines.append("-" * 60)
                lines.append(f"\n🟢 支撑位:")
                lines.append(f"   第一支撑: ${lows[-1]:,.2f} (日内低点)")
                lines.append(f"   第二支撑: ${recent_low:,.2f} (近期低点)")
                lines.append(f"   第三支撑: ${pivot:,.2f} (Pivot)")
                lines.append(f"\n🔴 阻力位:")
                lines.append(f"   第一阻力: ${highs[-1]:,.2f} (日内高点)")
                lines.append(f"   第二阻力: ${recent_high:,.2f} (近期高点)")
                lines.append(f"   心理关口: $80,000")
            
            # 交易策略
            lines.append("\n" + "-" * 60)
            lines.append("【三、交易策略建议】")
            lines.append("-" * 60)
            
            signals = []
            if current > ma20:
                signals.append(("MA多头", True))
            else:
                signals.append(("MA空头", False))
            if rsi and rsi < 30:
                signals.append(("RSI超卖", True))
            elif rsi and rsi > 70:
                signals.append(("RSI超买", False))
            if histogram is not None and histogram > 0:
                signals.append(("MACD多方", True))
            else:
                signals.append(("MACD空方", False))
            
            bull = sum(1 for _, v in signals if v)
            bear = sum(1 for _, v in signals if not v)
            
            if bull > bear and bull >= 2:
                overall = "偏多 📈"
            elif bear > bull and bear >= 2:
                overall = "偏空 📉"
            else:
                overall = "中性 📊"
            
            lines.append(f"\n🎯 综合信号: {overall}")
            lines.append(f"   看多因子: {bull}/3")
            lines.append(f"   看空因子: {bear}/3")
            
            lines.append(f"\n💼 操作建议:")
            if overall == "偏多 📈":
                lines.append(f"   ✅ 进场区域: ${current:,.2f} 附近")
                lines.append(f"   ✅ 止损位: ${recent_low:,.2f}")
                lines.append(f"   ✅ 目标位1: ${recent_high:,.2f}")
                lines.append(f"   ✅ 仓位建议: 轻仓试多，不超过20%")
            elif overall == "偏空 📉":
                lines.append(f"   🔻 进场区域: ${current:,.2f} 附近")
                lines.append(f"   🔻 止损位: ${recent_high:,.2f}")
                lines.append(f"   🔻 目标位: ${recent_low:,.2f}")
                lines.append(f"   🔻 仓位建议: 轻仓试空，不超过20%")
            else:
                lines.append(f"   ⚪ 建议观望，等待方向明确")
                lines.append(f"   ⚪ 突破 {recent_high:,.2f} 跟进做多")
                lines.append(f"   ⚪ 跌破 {recent_low:,.2f} 跟进做空")
            
            lines.append(f"\n📋 风险提示:")
            lines.append(f"   • 严格止损，不要扛单")
            lines.append(f"   • 控制仓位，杠杆不超过5x")
            lines.append(f"   • 美联储利率决议前后波动加大")
        
        # 基本面 & 新闻
        lines.append("\n" + "-" * 60)
        lines.append("【四、市场新闻】")
        lines.append("-" * 60)
        news = self.fetcher.get_news(['BTC-USD', '^GSPC', 'GC=F'], limit=5)
        if news:
            for i, n in enumerate(news, 1):
                pub = n['pubDate'][:10] if n['pubDate'] else ''
                lines.append(f"\n   {i}. {n['title']}")
                if n['summary']:
                    lines.append(f"      {n['summary'][:120]}...")
                lines.append(f"      来源: {n['provider']} · {pub}")
        else:
            lines.append(f"\n   暂无新闻数据")
        
        lines.append("\n" + "=" * 60)
        lines.append("  ⚠️ 免责声明: 仅供参考,不构成投资建议")
        lines.append("  📧 由 Quinn 投资研究员生成")
        lines.append("  🔍 深度分析,价值投资")
        lines.append("=" * 60)
        
        return "\n".join(lines)


if __name__ == "__main__":
    generator = ReportGenerator()
    report = generator.generate_daily_report(['bitcoin', 'ethereum', 'solana'])
    print(report)
