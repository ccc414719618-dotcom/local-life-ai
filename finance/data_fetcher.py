"""
Quinn Finance Framework - Data Fetcher Module v3
统一使用 yfinance 获取所有数据（解决 CoinGecko 被墙问题）
"""

import urllib.request
import pandas as pd
import json
from datetime import datetime
from typing import Optional, Dict, Any, List


class DataFetcher:
    """数据获取器 - 全链路 yfinance"""
    
    CRYPTO_MAP = {
        'bitcoin': 'BTC-USD',
        'ethereum': 'ETH-USD',
        'solana': 'SOL-USD',
    }
    
    # 类级别缓存：所有实例共享，同一进程内跨调用复用
    _yfinance_cache: Dict[str, Any] = {}
    # 全局节流：每个ticker上次请求时间（秒），防止同ticker高频请求触发限流
    _ticker_last_request: Dict[str, float] = {}

    def __init__(self):
        self.session_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    
    def _get(self, url: str, timeout: int = 10) -> Optional[Dict]:
        """通用 GET 请求"""
        try:
            req = urllib.request.Request(url, headers=self.session_headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read())
        except Exception:
            return None
    
    def _throttle(self, ticker: str, min_interval: float = 2.0):
        """全局节流：确保同一 ticker 两次请求间隔不少于 min_interval 秒"""
        import time
        now = time.time()
        last = self._ticker_last_request.get(ticker, 0)
        elapsed = now - last
        if elapsed < min_interval:
            wait = min_interval - elapsed
            print(f'  [throttle] {ticker} 等待 {wait:.1f}s')
            time.sleep(wait)
        self._ticker_last_request[ticker] = time.time()

    def _yfetch(self, ticker: str, period: str = '1mo', interval: str = '1d') -> Any:
        """yfinance 封装，带缓存+节流+重试+退避"""
        key = f"{ticker}_{period}_{interval}"
        if key in self._yfinance_cache and self._yfinance_cache[key] is not None:
            return self._yfinance_cache[key]
        import yfinance as yf, time
        for attempt in range(4):
            try:
                self._throttle(ticker, min_interval=2.5)
                t = yf.Ticker(ticker)
                result = t.history(period=period, interval=interval)
                self._yfinance_cache[key] = result
                return result
            except Exception as e:
                if 'Rate limited' in str(e) and attempt < 3:
                    wait = (attempt + 1) * 10
                    print(f'  [yfinance rate limit] {ticker} 重试 ({attempt+1}/4)，等待 {wait}s')
                    time.sleep(wait)
                else:
                    print(f'  [yfinance error] {ticker}: {e}')
                    self._yfinance_cache[key] = None
                    return None
        return None

    def _yfinance_download(self, tickers: str or List, period: str, interval: str = '1d', auto_adjust: bool = True):
        """yfinance download 封装，带节流+重试+退避，返回 DataFrame 或 None"""
        import yfinance as yf, time
        ticker_list = tickers if isinstance(tickers, list) else tickers.split()
        for ticker in ticker_list:
            self._throttle(ticker, min_interval=2.5)
        for attempt in range(4):
            try:
                return yf.download(
                    tickers, period=period, interval=interval,
                    auto_adjust=auto_adjust, progress=False
                )
            except Exception as e:
                if 'Rate limited' in str(e) and attempt < 3:
                    wait = (attempt + 1) * 10
                    print(f'  [yfinance rate limit] 重试 ({attempt+1}/4)，等待 {wait}s')
                    time.sleep(wait)
                else:
                    print(f'  [yfinance download error] {e}')
                    return None
        return None
    
    def get_crypto_prices(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        获取加密货币价格 (yfinance，失败时从K线数据兜底)
        """
        import yfinance as yf
        result = {}
        cny_rate = self._get_cny_rate()
        
        for symbol in symbols:
            ticker_sym = self.CRYPTO_MAP.get(symbol, f"{symbol.upper()}-USD")
            try:
                ticker = yf.Ticker(ticker_sym)
                # 用 5d+1h 组合确保能取到多个交易日数据
                hist = self._yfinance_download(ticker_sym, '5d', '1h', auto_adjust=True)
                if hist.empty:
                    hist = self._yfinance_download(ticker_sym, '5d', '1d', auto_adjust=True)
                if hist.empty:
                    continue
                closes = hist['Close'].dropna()
                if closes.empty:
                    continue
                current = float(closes.iloc[-1])
                # 按日期分组取日收盘价（避免同一天多个小时数据）
                daily_closes = hist.groupby(hist.index.date)['Close'].last().dropna()
                if len(daily_closes) >= 2:
                    prev = float(daily_closes.iloc[-2])
                    change = round((current - prev) / prev * 100, 2)
                else:
                    change = 0.0
                volume = float(hist['Volume'].dropna().iloc[-1]) if 'Volume' in hist.columns else 0
                result[symbol] = {
                    'usd': round(current, 2),
                    'cny': round(current * cny_rate, 0),
                    'change_24h': change,
                    'volume_24h': round(volume, 2)
                }
            except Exception as e:
                print(f"获取 {symbol} 价格失败: {e}")
        return result
    
    def _get_cny_rate(self) -> float:
        """获取 USD/CNY 汇率"""
        try:
            import yfinance as yf
            ticker = yf.Ticker('USDCNY=X')
            hist = self._yfetch('USDCNY=X', '2d')
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
        except:
            pass
        return 7.2  # 默认汇率
    
    def get_crypto_ohlc(self, symbol: str = 'bitcoin', days: int = 90) -> List:
        """
        获取K线数据 (yfinance，1h聚合为日线确保数据充足)
        返回: [[timestamp_ms, open, high, low, close], ...]
        """
        ticker_sym = self.CRYPTO_MAP.get(symbol, f"{symbol.upper()}-USD")
        try:
            import yfinance as yf
            # 用重试机制
            hist = self._yfinance_download(ticker_sym, f'{days}d', '1h', auto_adjust=True)
            if hist is None or hist.empty:
                hist = self._yfinance_download(ticker_sym, f'{days}d', '1d', auto_adjust=True)
            if hist is None or hist.empty:
                return []
            daily = hist.groupby(hist.index.date).agg(
                Open=('Open', 'first'),
                High=('High', 'max'),
                Low=('Low', 'min'),
                Close=('Close', 'last')
            )
            rows = []
            for date, row in daily.iterrows():
                ts_ms = int(pd.Timestamp(date).timestamp() * 1000)
                rows.append([ts_ms, row['Open'], row['High'], row['Low'], row['Close']])
            return rows
        except Exception as e:
            print(f'获取 {symbol} K线失败: {e}')
            return []
    
    def get_precious_metals(self) -> Dict[str, Dict]:
        """获取贵金属实时数据 (yfinance)"""
        result = {}
        try:
            import yfinance as yf
            data = self._yfinance_download('GC=F SI=F', '5d', '1d', auto_adjust=True)
            if not data.empty:
                close_prices = data['Close']
                for symbol, name in [('GC=F', 'Gold (XAU/USD)'), ('SI=F', 'Silver (XAG/USD)')]:
                    if symbol in close_prices.columns:
                        col = close_prices[symbol].dropna()
                        if len(col) >= 2:
                            current = float(col.iloc[-1])
                            prev = float(col.iloc[-2])
                            change = round((current - prev) / prev * 100, 2)
                            result[name] = {'price': current, 'change': change}
        except Exception as e:
            print(f"贵金属获取失败: {e}")
        return result
    
    def get_market_indices(self) -> Dict[str, Dict]:
        """获取全球主要指数真实行情 (yfinance)"""
        indices = {
            '^GSPC': 'S&P 500',
            '^DJI': 'Dow Jones',
            '^FTSE': 'FTSE 100',
            '^N225': 'Nikkei 225',
            '000001.SS': 'SSE 上证',
            '^IXIC': 'NASDAQ',
            '^HSI': 'Hang Seng',
            '^GDAXI': 'DAX',
        }
        result = {}
        try:
            import yfinance as yf
            # 批量获取主力指数
            batch = ['^GSPC', '^DJI', '^FTSE', '^N225', '000001.SS']
            data = self._yfinance_download(' '.join(batch), '5d', '1d', auto_adjust=True)
            if not data.empty:
                if isinstance(data.columns, pd.MultiIndex):
                    close_prices = data['Close']
                else:
                    close_prices = data
                for symbol in batch:
                    if symbol in close_prices.columns:
                        col = close_prices[symbol].dropna()
                        if len(col) >= 2:
                            current = float(col.iloc[-1])
                            prev = float(col.iloc[-2])
                            change = round((current - prev) / prev * 100, 2)
                            result[indices[symbol]] = {'price': current, 'change': change}
            # 兜底单独获取
            fallback = {'^IXIC': 'NASDAQ', '^HSI': 'Hang Seng', '^GDAXI': 'DAX'}
            for symbol, name in fallback.items():
                if name in result:
                    continue
                try:
                    ticker = yf.Ticker(symbol)
                    hist = self._yfetch(symbol, '5d')
                    if not hist.empty and len(hist) >= 2:
                        current = float(hist['Close'].iloc[-1])
                        prev = float(hist['Close'].iloc[-2])
                        change = round((current - prev) / prev * 100, 2)
                        result[name] = {'price': current, 'change': change}
                except:
                    pass
        except Exception as e:
            print(f"全球指数获取失败: {e}")
        return result
    
    def get_fear_greed_index(self) -> Optional[int]:
        """获取恐慌贪婪指数 (Alternative.me)"""
        url = "https://api.alternative.me/fng/?limit=1"
        data = self._get(url, timeout=8)
        if data and 'data' in data and len(data['data']) > 0:
            return int(data['data'][0]['value'])
        return None
    
    def get_dominant_trend(self) -> str:
        """判断市场主导趋势"""
        crypto = self.get_crypto_prices(['bitcoin'])
        if not crypto or 'bitcoin' not in crypto:
            return "数据获取失败"
        btc_change = crypto['bitcoin']['change_24h']
        if btc_change > 3:
            return "强势上涨"
        elif btc_change > 0:
            return "小幅上涨"
        elif btc_change > -3:
            return "小幅回调"
        else:
            return "明显下跌"
    
    def get_news(self, tickers: list = None, limit: int = 5) -> list:
        """
        获取财经新闻 (yfinance 原生接口)
        tickers: ['BTC-USD', '^GSPC', 'GC=F'] 等
        返回: [{title, summary, provider, pubDate, url}, ...]
        """
        if tickers is None:
            tickers = ['BTC-USD', '^GSPC', 'GC=F']
        all_news = []
        seen_titles = set()
        try:
            import yfinance as yf
            for ticker_sym in tickers:
                try:
                    ticker = yf.Ticker(ticker_sym)
                    news = ticker.get_news()
                    if not news:
                        continue
                    for item in news:
                        content = item.get('content', {})
                        title = content.get('title', '')
                        if not title or title in seen_titles:
                            continue
                        seen_titles.add(title)
                        all_news.append({
                            'title': title,
                            'summary': content.get('summary', '')[:200],
                            'provider': content.get('provider', {}).get('displayName', ''),
                            'pubDate': content.get('pubDate', ''),
                            'url': content.get('clickThroughUrl', {}).get('url', ''),
                        })
                        if len(all_news) >= limit:
                            break
                except Exception:
                    continue
                if len(all_news) >= limit:
                    break
        except Exception as e:
            print(f"获取新闻失败: {e}")
        return all_news[:limit]


if __name__ == "__main__":
    import time
    import pandas as pd
    f = DataFetcher()
    
    print("=== 测试数据获取 ===")
    
    t0 = time.time()
    crypto = f.get_crypto_prices(['bitcoin', 'ethereum', 'solana'])
    print(f"加密货币: {len(crypto)} items ({time.time()-t0:.1f}s)")
    for sym, info in crypto.items():
        print(f"  {sym}: ${info['usd']:,.2f} ({info['change_24h']:+.2f}%)")
    
    t1 = time.time()
    ohlc = f.get_crypto_ohlc('bitcoin', 90)
    print(f"BTC K线: {len(ohlc)} 根 ({time.time()-t1:.1f}s)")
    
    t2 = time.time()
    fg = f.get_fear_greed_index()
    print(f"恐慌贪婪: {fg} ({time.time()-t2:.1f}s)")
    
    t3 = time.time()
    metals = f.get_precious_metals()
    print(f"贵金属: {len(metals)} items ({time.time()-t3:.1f}s)")
    
    t4 = time.time()
    indices = f.get_market_indices()
    print(f"全球指数: {len(indices)} items ({time.time()-t4:.1f}s)")
    
    t5 = time.time()
    news = f.get_news(['BTC-USD', '^GSPC', 'GC=F'], limit=5)
    print(f"新闻: {len(news)} 条 ({time.time()-t5:.1f}s)")
    for n in news:
        print(f"  - {n['title'][:60]}")
    
    print(f"\n总耗时: {time.time()-t0:.1f}s")
