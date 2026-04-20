"""
Quinn Finance Framework - Chart Generator
生成专业金融图表
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional
import io
import os

# 中文字体
FONT_CN = ['PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['font.sans-serif'] = FONT_CN
plt.rcParams['axes.unicode_minus'] = False

OUTPUT_DIR = '/Volumes/1TB/openclaw/jinrong-bot/finance/charts'
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _get_ohlc_from_yfinance(ticker_sym: str, days: int = 90) -> Optional[Dict]:
    """
    获取OHLC数据。
    优先使用 DataFetcher 类级缓存（同进程内复用，节省 yfinance 请求）。
    """
    cache_key = f'ohlc_{ticker_sym}_{days}d'
    # 尝试从 DataFetcher 类缓存读取（跨模块共享）
    try:
        from data_fetcher import DataFetcher
        if hasattr(DataFetcher, '_yfinance_cache') and cache_key in DataFetcher._yfinance_cache:
            return DataFetcher._yfinance_cache[cache_key]
    except Exception:
        pass
    # 没有缓存，直接下载
    import yfinance as yf
    try:
        ticker = yf.Ticker(ticker_sym)
        hist = ticker.history(period=f'{days}d', interval='1h', auto_adjust=True)
        if hist.empty:
            hist = ticker.history(period=f'{days}d', interval='1d', auto_adjust=True)
        if hist.empty:
            return None
        daily = hist.groupby(hist.index.date).agg(
            Open=('Open', 'first'),
            High=('High', 'max'),
            Low=('Low', 'min'),
            Close=('Close', 'last')
        ).reset_index()
        daily['date'] = daily['index'].apply(lambda x: x if isinstance(x, str) else str(x))
        # 写入 DataFetcher 缓存
        try:
            from data_fetcher import DataFetcher
            if hasattr(DataFetcher, '_yfinance_cache'):
                DataFetcher._yfinance_cache[cache_key] = daily
        except Exception:
            pass
        return daily
    except Exception as e:
        print(f'K线获取失败: {e}')
        return None


class ChartGenerator:
    
    @staticmethod
    def _style_axis(ax):
        """统一样式"""
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#CCCCCC')
        ax.spines['bottom'].set_color('#CCCCCC')
        ax.tick_params(colors='#666666')
        ax.yaxis.grid(True, color='#EEEEEE', linestyle='-', linewidth=0.5)
        ax.set_axisbelow(True)
    
    @classmethod
    def plot_btc_price_chart(cls, output_path: str = None) -> Optional[str]:
        """BTC价格走势图（K线 + MA）"""
        data = _get_ohlc_from_yfinance('BTC-USD', 90)
        if data is None or len(data) < 5:
            return None
        
        closes = data['Close'].values
        dates_str = data['date'].values
        dates = [datetime.strptime(str(d), '%Y-%m-%d') for d in dates_str]
        
        # 计算MA
        def ma(arr, n):
            result = np.full(len(arr), np.nan)
            for i in range(n-1, len(arr)):
                result[i] = np.mean(arr[i-n+1:i+1])
            return result
        
        ma5 = ma(closes, 5)
        ma10 = ma(closes, 10)
        ma20 = ma(closes, 20)
        ma60 = ma(closes, 20)  # 60天日线数据不够用20
        
        fig, ax = plt.subplots(figsize=(12, 6), dpi=100)
        fig.patch.set_facecolor('#0D1117')
        ax.set_facecolor('#0D1117')
        
        # 价格线
        ax.plot(dates, closes, color='#F7931A', linewidth=1.5, label='BTC Price', zorder=3)
        ax.fill_between(dates, closes, color='#F7931A', alpha=0.1)
        
        # MA线
        ax.plot(dates, ma5, color='#00D4AA', linewidth=1, linestyle='--', label='MA5', alpha=0.8)
        ax.plot(dates, ma10, color='#FF6B6B', linewidth=1, linestyle='--', label='MA10', alpha=0.8)
        ax.plot(dates, ma20, color='#4ECDC4', linewidth=1.2, linestyle='-', label='MA20', alpha=0.9)
        
        # 最新价格标注
        last_close = closes[-1]
        ax.annotate(f'${last_close:,.0f}', 
                   xy=(dates[-1], last_close),
                   xytext=(8, 0), textcoords='offset points',
                   color='#F7931A', fontsize=12, fontweight='bold')
        
        ax.set_title('BTC/USD 价格走势 (90天)', color='white', fontsize=16, fontweight='bold', pad=15)
        ax.set_ylabel('价格 (USD)', color='#AAAAAA', fontsize=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        plt.xticks(rotation=30)
        ax.legend(loc='upper left', framealpha=0.2, facecolor='#1C1C1C', labelcolor='white')
        cls._style_axis(ax)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x:,.0f}'))
        
        # 涨跌幅
        pct_change = ((closes[-1] - closes[-2]) / closes[-2] * 100) if len(closes) > 1 else 0
        color = '#00D4AA' if pct_change >= 0 else '#FF4757'
        ax.text(0.98, 0.95, f'24h: {pct_change:+.2f}%', transform=ax.transAxes,
               color=color, fontsize=11, ha='right', va='top',
               bbox=dict(boxstyle='round,pad=0.3', facecolor='#1C1C1C', alpha=0.8))
        
        plt.tight_layout()
        path = output_path or os.path.join(OUTPUT_DIR, 'btc_price.png')
        plt.savefig(path, facecolor='#0D1117', edgecolor='none', dpi=100)
        plt.close()
        return path
    
    @classmethod
    def plot_market_overview(cls, crypto_data: Dict, metals_data: Dict, indices_data: Dict, output_path: str = None) -> Optional[str]:
        """市场总览柱状图"""
        items = []
        colors = []
        
        # 加密货币
        for sym, info in crypto_data.items():
            items.append((sym.capitalize(), info.get('change_24h', 0), '#F7931A' if 'BTC' in sym.upper() else '#627EEA'))
        
        # 贵金属
        for name, info in metals_data.items():
            items.append((name.split()[0], info.get('change', 0), '#FFD700'))
        
        # 指数
        for name, info in indices_data.items():
            if info.get('change', 0) != 0:
                items.append((name, info['change'], '#00D4AA'))
        
        if not items:
            return None
        
        labels = [item[0] for item in items]
        values = [item[1] for item in items]
        colors_bar = [item[2] for item in items]
        
        fig, ax = plt.subplots(figsize=(12, 6), dpi=100)
        fig.patch.set_facecolor('#FFFFFF')
        ax.set_facecolor('#F8F9FA')
        
        bars = ax.bar(labels, values, color=colors_bar, edgecolor='white', linewidth=0.5, width=0.6)
        
        # 数值标签
        for bar, val in zip(bars, values):
            ypos = bar.get_height()
            color = '#00D4AA' if ypos >= 0 else '#FF4757'
            ax.text(bar.get_x() + bar.get_width()/2, ypos + 0.05 if ypos >= 0 else ypos - 0.15,
                   f'{val:+.2f}%', ha='center', va='bottom' if ypos >= 0 else 'top',
                   color=color, fontsize=9, fontweight='bold')
        
        ax.axhline(y=0, color='#CCCCCC', linewidth=1)
        ax.set_title('📊 市场涨跌概览 (24h)', fontsize=16, fontweight='bold', pad=15)
        ax.set_ylabel('涨跌幅 (%)', fontsize=10)
        cls._style_axis(ax)
        plt.xticks(rotation=30, ha='right')
        plt.tight_layout()
        
        path = output_path or os.path.join(OUTPUT_DIR, 'market_overview.png')
        plt.savefig(path, facecolor='white', edgecolor='none', dpi=100)
        plt.close()
        return path
    
    @classmethod
    def plot_rsi_gauge(cls, rsi_value: float, output_path: str = None) -> Optional[str]:
        """RSI 仪表盘"""
        fig, ax = plt.subplots(figsize=(6, 4), dpi=100, subplot_kw={'projection': 'polar'})
        fig.patch.set_facecolor('#0D1117')
        ax.set_facecolor('#0D1117')
        
        # RSI分段
        angles = np.linspace(0.25, 2.25, 100)
        values = np.ones(100)
        
        # 超卖区域
        ax.fill_between(angles, 0, 0.3, color='#00D4AA', alpha=0.3)
        # 中性区域
        ax.fill_between(angles, 0.3, 0.7, color='#FFD700', alpha=0.2)
        # 超买区域
        ax.fill_between(angles, 0.7, 1, color='#FF4757', alpha=0.3)
        
        # 指针（RSI 0-100映射到 0.25-2.25角度）
        needle_angle = 0.25 + (rsi_value / 100) * 2.0
        needle_val = 0.85
        ax.annotate('', xy=(np.radians(np.degrees(needle_angle)), needle_val),
                   xytext=(0, 0), arrowprops=dict(arrowstyle='->', color='white', lw=2))
        
        # 中心数值
        ax.text(0, -0.1, f'RSI: {rsi_value:.1f}', ha='center', va='center',
               color='white', fontsize=18, fontweight='bold', transform=ax.transAxes)
        
        # 状态标签
        if rsi_value > 70:
            status, status_color = '超买 🔴', '#FF4757'
        elif rsi_value < 30:
            status, status_color = '超卖 🟢', '#00D4AA'
        elif rsi_value > 60:
            status, status_color = '偏强 🟡', '#FFD700'
        elif rsi_value < 40:
            status, status_color = '偏弱 🟡', '#FFD700'
        else:
            status, status_color = '中性 ⚪', '#AAAAAA'
        
        ax.text(0, -0.2, status, ha='center', va='center',
               color=status_color, fontsize=12, transform=ax.transAxes)
        
        ax.set_yticklabels([])
        ax.set_xticklabels([])
        ax.spines['polar'].set_visible(False)
        ax.grid(False)
        
        path = output_path or os.path.join(OUTPUT_DIR, 'rsi_gauge.png')
        plt.savefig(path, facecolor='#0D1117', edgecolor='none', dpi=100)
        plt.close()
        return path
    
    @classmethod
    def plot_portfolio_bar(cls, crypto_data: Dict, metals_data: Dict, output_path: str = None) -> Optional[str]:
        """投资品种涨跌对比（柱状图）"""
        labels, prices, changes = [], [], []
        color_map = {'bitcoin': '#F7931A', 'ethereum': '#627EEA', 'solana': '#9945FF',
                     'Gold': '#FFD700', 'Silver': '#C0C0C0'}
        
        for sym, info in crypto_data.items():
            labels.append(sym.capitalize())
            prices.append(info['usd'])
            changes.append(info['change_24h'])
        
        for name, info in metals_data.items():
            short_name = name.split()[0]
            labels.append(short_name)
            prices.append(info['price'])
            changes.append(info['change'])
        
        colors = [color_map.get(l.lower(), '#4ECDC4') for l in labels]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=100)
        fig.patch.set_facecolor('#F8F9FA')
        
        # 左侧：价格
        bars1 = ax1.bar(labels, prices, color=colors, edgecolor='white', linewidth=0.5)
        for bar, price in zip(bars1, prices):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(prices)*0.01,
                    f'${price:,.0f}', ha='center', va='bottom', fontsize=9, color='#333333')
        ax1.set_title('当前价格 (USD)', fontsize=12, fontweight='bold', pad=10)
        ax1.set_ylabel('USD', fontsize=9)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x:,.0f}'))
        ax1.tick_params(axis='x', rotation=30)
        
        # 右侧：涨跌幅
        bar_colors = ['#00D4AA' if v >= 0 else '#FF4757' for v in changes]
        bars2 = ax2.bar(labels, changes, color=bar_colors, edgecolor='white', linewidth=0.5)
        for bar, val in zip(bars2, changes):
            ypos = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2, ypos + 0.05 if ypos >= 0 else ypos - 0.15,
                    f'{val:+.2f}%', ha='center', va='bottom' if ypos >= 0 else 'top',
                    fontsize=9, color='#333333', fontweight='bold')
        ax2.axhline(y=0, color='#CCCCCC', linewidth=1)
        ax2.set_title('24h 涨跌幅', fontsize=12, fontweight='bold', pad=10)
        ax2.set_ylabel('涨跌幅 (%)', fontsize=9)
        ax2.tick_params(axis='x', rotation=30)
        
        for ax in (ax1, ax2):
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.yaxis.grid(True, color='#EEEEEE', linestyle='-', linewidth=0.5)
            ax.set_axisbelow(True)
        
        plt.tight_layout()
        path = output_path or os.path.join(OUTPUT_DIR, 'portfolio_bar.png')
        plt.savefig(path, facecolor='white', edgecolor='none', dpi=100)
        plt.close()
        return path


if __name__ == '__main__':
    # 测试图表生成
    from data_fetcher import DataFetcher
    import sys
    
    fetcher = DataFetcher()
    crypto = fetcher.get_crypto_prices(['bitcoin', 'ethereum', 'solana'])
    metals = fetcher.get_precious_metals()
    indices = fetcher.get_market_indices()
    ohlc = fetcher.get_crypto_ohlc('bitcoin', 90)
    
    # 计算RSI
    closes = [k[4] for k in ohlc]
    from report_generator import TechnicalAnalyzer
    analyzer = TechnicalAnalyzer()
    rsi = analyzer.calculate_rsi(closes)
    
    print('生成图表...')
    
    p1 = ChartGenerator.plot_btc_price_chart()
    print(f'BTC价格图: {p1}')
    
    p2 = ChartGenerator.plot_market_overview(crypto, metals, indices)
    print(f'市场总览: {p2}')
    
    p3 = ChartGenerator.plot_portfolio_bar(crypto, metals)
    print(f'组合对比: {p3}')
    
    if rsi:
        p4 = ChartGenerator.plot_rsi_gauge(rsi)
        print(f'RSI仪表: {p4}')
    
    print('完成!')
