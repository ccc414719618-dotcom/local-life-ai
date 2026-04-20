#!/usr/bin/env python3
"""
Quinn 市场动态扫描 v2
每天 15:00 执行 - 多时间周期技术分析 + 市场情绪

覆盖：1H / 4H / 1D / 1W 四个时间周期
内容：价格 + RSI + MACD + 均线 + 支撑阻力 + 恐慌贪婪
"""
import sys
import time
import json
import os
from datetime import datetime

WORKSPACE = "/Volumes/1TB/openclaw/jinrong-bot"
sys.path.insert(0, WORKSPACE)

import pandas as pd
import numpy as np
import yfinance as yf

# ── 工具函数 ──────────────────────────────────────────

def fmt(val, is_pct=False, decimals=None):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    sign = "+" if val >= 0 else ""
    if is_pct:
        d = decimals if decimals else 2
        return f"{sign}{val:.{d}f}%"
    if decimals is not None:
        return f"{sign}{val:.{decimals}f}"
    return f"{sign}{val:.2f}"

def rsi_calc(closes, period=14):
    """计算 RSI，接受 Series 或单列 DataFrame"""
    if isinstance(closes, pd.DataFrame):
        if closes.shape[1] == 1:
            closes = closes.iloc[:, 0]
        else:
            return None
    if len(closes) < period + 1:
        return None
    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 1)

def macd_calc(closes, fast=12, slow=26, signal=9):
    """计算 MACD: (DIF, DEA, BAR)"""
    if len(closes) < slow + signal:
        return None, None, None
    ema_fast = closes.ewm(span=fast, adjust=False).mean()
    ema_slow = closes.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    bar = 2 * (dif - dea)
    return round(float(dif.iloc[-1]), 4), round(float(dea.iloc[-1]), 4), round(float(bar.iloc[-1]), 4)

def ma_calc(closes, windows=[5, 20, 60]):
    """计算多条均线"""
    result = {}
    for w in windows:
        if len(closes) >= w:
            ma = closes.rolling(window=w).mean().iloc[-1]
            if not np.isnan(ma):
                result[f"MA{w}"] = round(float(ma), 2)
    return result

def atr_calc(high, low, close, period=14):
    """计算 ATR"""
    if len(high) < period + 1:
        return None
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    return round(float(tr.rolling(window=period).mean().iloc[-1]), 2)

def sup_res(closes, windows=[20, 60]):
    """计算近端支撑/阻力"""
    result = {'support': None, 'resistance': None}
    for w in windows:
        if len(closes) >= w:
            min_p = float(closes.tail(w).min())
            max_p = float(closes.tail(w).max())
            if result['support'] is None or min_p > result['support']:
                result['support'] = min_p
            if result['resistance'] is None or max_p < result['resistance']:
                result['resistance'] = max_p
    return result

def trend_signal(rsi_val, dif, dea, price, ma_dict, sr):
    """综合多指标判断趋势信号"""
    signals = []
    if rsi_val and rsi_val > 70:
        signals.append("RSI超买")
    elif rsi_val and rsi_val < 30:
        signals.append("RSI超卖")
    if dif is not None and dea is not None:
        if dif > dea:
            signals.append("MACD多头")
        else:
            signals.append("MACD空头")
    if ma_dict:
        price_arr = float(price)
        if 'MA5' in ma_dict and price_arr > ma_dict['MA5']:
            signals.append("价格>MA5")
        elif 'MA5' in ma_dict:
            signals.append("价格<MA5")
    bullish = len([s for s in signals if '超卖' in s or '多头' in s or '>' in s])
    bearish = len([s for s in signals if '超买' in s or '空头' in s or '<' in s])
    if bullish > bearish:
        return "偏多", bullish, bearish
    elif bearish > bullish:
        return "偏空", bullish, bearish
    return "中性", bullish, bearish

def fetch_ohlc(ticker, interval, period):
    """下载 OHLCV，处理 MultiIndex 列"""
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
    if df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# ── 多时间周期分析 ─────────────────────────────────────

def multi_timeframe_analysis(ticker="BTC-USD"):
    """4个时间周期的技术分析"""
    configs = [
        ("1H",  "7d",  "60m"),
        ("4H",  "30d", "4h"),
        ("1D",  "90d", "1d"),
        ("1W",  "365d","1wk"),
    ]
    results = {}
    for label, period, interval in configs:
        df = fetch_ohlc(ticker, interval, period)
        if df is None or df.empty or 'Close' not in df.columns:
            results[label] = {"status": "数据获取失败"}
            continue
        closes = df['Close'].dropna()
        if len(closes) < 5:
            results[label] = {"status": "数据不足"}
            continue
        high = df['High'].dropna()
        low  = df['Low'].dropna()
        price = float(closes.iloc[-1])
        rsi   = rsi_calc(closes)
        dif, dea, bar = macd_calc(closes)
        ma    = ma_calc(closes)
        sr    = sup_res(closes)
        atr   = atr_calc(high, low, closes)
        sig, bull, bear = trend_signal(rsi, dif, dea, price, ma, sr)
        results[label] = {
            "price":    price,
            "rsi":      rsi,
            "dif":      dif,
            "dea":      dea,
            "macd_bar": bar,
            "ma":       ma,
            "support":  sr['support'],
            "resistance": sr['resistance'],
            "atr":      atr,
            "signal":   sig,
            "bullish_count": bull,
            "bearish_count": bear,
        }
        # 休息一下防限流
        time.sleep(1.5)
    return results

# ── 恐慌贪婪 ──────────────────────────────────────────

def get_fear_greed():
    """获取恐慌贪婪指数 + 历史对比"""
    try:
        url = "https://api.alternative.me/fng/?limit=5"
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            if 'data' in data and len(data['data']) > 0:
                items = data['data']
                latest = int(items[0]['value'])
                prev   = int(items[1]['value']) if len(items) > 1 else latest
                delta  = latest - prev
                # 分类
                if latest >= 75:
                    cls_zh = "极度贪婪"
                    cls_en = "Extreme Greed"
                    emoji  = "🟢"
                elif latest >= 55:
                    cls_zh = "贪婪"
                    cls_en = "Greed"
                    emoji  = "💚"
                elif latest >= 45:
                    cls_zh = "中性"
                    cls_en = "Neutral"
                    emoji  = "🟡"
                elif latest >= 25:
                    cls_zh = "恐慌"
                    cls_en = "Fear"
                    emoji  = "🧡"
                else:
                    cls_zh = "极度恐慌"
                    cls_en = "Extreme Fear"
                    emoji  = "🔴"
                return {
                    "value":  latest,
                    "prev":   prev,
                    "delta":  delta,
                    "class_zh": cls_zh,
                    "class_en": cls_en,
                    "emoji":  emoji,
                    "trend":  "恶化" if delta < -5 else ("改善" if delta > 5 else "持稳"),
                }
    except Exception as e:
        print(f"[!] 恐慌贪婪获取失败: {e}")
    return None

def get_crypto_fear_index():
    """加密市场特有恐惧指数（综合波动率 + 合约资金费率 + 多空比）"""
    # Alternative.me 没有专门的加密恐惧指数，用 BTC 波动率模拟
    try:
        btc = yf.Ticker("BTC-USD")
        # 30天波动率（年化）
        hist = btc.history(period="30d", interval="1d")
        if len(hist) >= 7:
            returns = hist['Close'].pct_change().dropna()
            vol_30d = float(returns.std() * np.sqrt(365) * 100)
            # 恐惧阈值（高波动=恐惧）
            if vol_30d > 80:
                fear_level = "极度恐慌"
                emoji = "🔴"
            elif vol_30d > 50:
                fear_level = "恐慌"
                emoji = "🧡"
            elif vol_30d > 30:
                fear_level = "中性"
                emoji = "🟡"
            else:
                fear_level = "贪婪"
                emoji = "💚"
            return {
                "btc_vol_30d": round(vol_30d, 1),
                "fear_level": fear_level,
                "emoji": emoji,
            }
    except Exception as e:
        print(f"[!] 加密恐惧指数获取失败: {e}")
    return None

# ── 主函数 ────────────────────────────────────────────

def metal_signal(ticker, name, period='90d'):
    """
    贵金属多周期分析 + 交易建议
    ticker: 'GC=F' (gold) or 'SI=F' (silver)
    返回: dict 包含 1D 数据、1W 数据、每日建议、每周建议
    """
    result = {}

    # 1D 数据（90天日线）
    df_d = fetch_ohlc(ticker, '1d', period)
    if df_d is not None and not df_d.empty and 'Close' in df_d.columns:
        closes_d = df_d['Close'].dropna()
        high_d   = df_d['High'].dropna()
        low_d    = df_d['Low'].dropna()
        if len(closes_d) >= 30:
            price_d = float(closes_d.iloc[-1])
            rsi_d   = rsi_calc(closes_d)
            dif_d, dea_d, bar_d = macd_calc(closes_d)
            ma_d    = ma_calc(closes_d)
            sr_d    = sup_res(closes_d)
            atr_d   = atr_calc(high_d, low_d, closes_d)
            sig_d, bull_d, bear_d = trend_signal(rsi_d, dif_d, dea_d, price_d, ma_d, sr_d)
            result['1D'] = {
                'price': price_d, 'rsi': rsi_d,
                'dif': dif_d, 'dea': dea_d, 'macd_bar': bar_d,
                'ma': ma_d, 'support': sr_d['support'],
                'resistance': sr_d['resistance'], 'atr': atr_d,
                'signal': sig_d, 'bull_count': bull_d, 'bear_count': bear_d,
            }

    # 1W 数据（52周周线）
    df_w = fetch_ohlc(ticker, '1wk', '365d')
    if df_w is not None and not df_w.empty and 'Close' in df_w.columns:
        closes_w = df_w['Close'].dropna()
        high_w   = df_w['High'].dropna()
        low_w    = df_w['Low'].dropna()
        if len(closes_w) >= 10:
            price_w = float(closes_w.iloc[-1])
            rsi_w   = rsi_calc(closes_w)
            dif_w, dea_w, bar_w = macd_calc(closes_w)
            ma_w    = ma_calc(closes_w)
            sr_w    = sup_res(closes_w)
            sig_w, bull_w, bear_w = trend_signal(rsi_w, dif_w, dea_w, price_w, ma_w, sr_w)
            result['1W'] = {
                'price': price_w, 'rsi': rsi_w,
                'dif': dif_w, 'dea': dea_w, 'macd_bar': bar_w,
                'ma': ma_w, 'support': sr_w['support'],
                'resistance': sr_w['resistance'],
                'signal': sig_w, 'bull_count': bull_w, 'bear_count': bear_w,
            }

    # 生成建议
    result['advice'] = _metal_advice(result, name)
    return result


def _metal_advice(data, name):
    """基于多周期指标生成贵金属交易建议"""
    d1 = data.get('1D', {})
    w1 = data.get('1W', {})

    def _score(d):
        """0-100 多空评分"""
        if not d:
            return 50, '数据不足'
        score = 50
        reasons = []

        rsi = d.get('rsi')
        if rsi:
            if rsi > 70:
                score -= 20; reasons.append(f'RSI超买({rsi})')
            elif rsi < 30:
                score += 20; reasons.append(f'RSI超卖({rsi})')
            elif rsi > 60:
                score += 10; reasons.append(f'RSI偏强({rsi})')
            elif rsi < 40:
                score -= 10; reasons.append(f'RSI偏弱({rsi})')

        dif = d.get('dif'); dea = d.get('dea')
        if dif and dea:
            if dif > dea:
                score += 15; reasons.append('MACD多头')
            else:
                score -= 15; reasons.append('MACD空头')

        ma = d.get('ma', {})
        price = d.get('price', 0)
        if ma:
            ma5  = ma.get('MA5', price)
            ma20 = ma.get('MA20', price)
            if price > ma5:
                score += 10; reasons.append('价格>MA5')
            else:
                score -= 10; reasons.append('价格<MA5')
            if ma5 > ma20:
                score += 10; reasons.append('均线多头排列')
            elif ma5 < ma20:
                score -= 10; reasons.append('均线空头排列')

        sig = d.get('signal', '')
        if '偏多' in sig:
            score += 10
        elif '偏空' in sig:
            score -= 10

        confidence = '低'
        if len(reasons) >= 4:
            confidence = '高'
        elif len(reasons) >= 2:
            confidence = '中'

        return max(0, min(100, score)), reasons, confidence

    score_d, reasons_d, conf_d = _score(d1)
    score_w, reasons_w, conf_w = _score(w1)

    # 行动建议
    def _action(score, conf, horizon):
        if conf == '数据不足':
            return '观望', '中'
        if score >= 70:
            return '买入', conf
        elif score >= 58:
            return '持有/加仓', conf
        elif score >= 45:
            return '持有', conf
        elif score >= 30:
            return '减仓', conf
        else:
            return '卖出/做空', conf

    act_d, conf_d = _action(score_d, conf_d, '日内')
    act_w, conf_w = _action(score_w, conf_w, '波段')

    # 关键价位
    sup = d1.get('support') or w1.get('support')
    res = d1.get('resistance') or w1.get('resistance')

    return {
        'daily': {'action': act_d, 'confidence': conf_d,
                   'score': score_d, 'reasons': reasons_d},
        'weekly': {'action': act_w, 'confidence': conf_w,
                   'score': score_w, 'reasons': reasons_w},
        'key_levels': {
            'support': sup,
            'resistance': res,
        }
    }


def main():
    t0 = time.time()
    today     = datetime.now().strftime('%Y-%m-%d')
    today_file = today.replace('-', '')
    now       = datetime.now().strftime('%Y-%m-%d %H:%M')

    os.makedirs(f"{WORKSPACE}/reports", exist_ok=True)

    lines = []
    all_data = {}

    # ── 1. 恐慌贪婪指数 ──
    fg = get_fear_greed()
    time.sleep(2)
    cf = get_crypto_fear_index()

    lines.append("**【市场情绪】**")
    if fg:
        trend_emoji = "📈" if fg['trend'] == "改善" else ("📉" if fg['trend'] == "恶化" else "➡️")
        lines.append(f"  恐慌贪婪: **{fg['value']}** ({fg['emoji']} {fg['class_zh']}) {trend_emoji} {fg['trend']}")
        lines.append(f"    上日: {fg['prev']} → 今日: {fg['value']}（{fg['delta']:+d}）")
    else:
        lines.append("  恐慌贪婪: N/A")
    if cf:
        lines.append(f"  加密波动率恐惧: **{cf['btc_vol_30d']}%**（{cf['emoji']} {cf['fear_level']}）30日年化")
    lines.append("")

    # ── 2. 多时间周期分析 ──
    lines.append("**【BTC 多周期技术分析】**")
    mtf = multi_timeframe_analysis("BTC-USD")

    interval_labels = {
        "1H": "1小时",
        "4H": "4小时",
        "1D": "日线",
        "1W": "周线",
    }

    for tf, data in mtf.items():
        if "status" in data:
            lines.append(f"  {tf}（{interval_labels.get(tf,tf)}）: {data['status']}")
            continue
        price    = data['price']
        rsi_val  = data['rsi']
        dif_val  = data['dif']
        dea_val  = data['dea']
        bar_val  = data['macd_bar']
        ma_dict  = data['ma']
        sup      = data['support']
        res      = data['resistance']
        atr_val  = data['atr']
        sig      = data['signal']
        bull_ct  = data['bullish_count']
        bear_ct  = data['bearish_count']

        # RSI emoji
        if rsi_val and rsi_val > 70:
            rsi_emoji = "🔴"
        elif rsi_val and rsi_val < 30:
            rsi_emoji = "🟢"
        elif rsi_val and rsi_val > 55:
            rsi_emoji = "💚"
        elif rsi_val and rsi_val < 45:
            rsi_emoji = "🧡"
        else:
            rsi_emoji = "🟡"

        # MACD 信号
        if dif_val and dea_val:
            if dif_val > dea_val:
                macd_sig = "🟢金叉"
            else:
                macd_sig = "🔴死叉"
            bar_arrow = "▲" if bar_val and bar_val > 0 else ("▼" if bar_val and bar_val < 0 else "─")
        else:
            macd_sig = "N/A"
            bar_arrow = ""

        lines.append(f"  ── {tf}（{interval_labels.get(tf,tf)}）──")
        lines.append(f"    价格: **${price:,.2f}**")
        lines.append(f"    RSI: {rsi_emoji} {rsi_val if rsi_val else 'N/A'}")
        lines.append(f"    MACD: {macd_sig}（DIF={dif_val}, DEA={dea_val}）{bar_arrow}{abs(bar_val) if bar_val else 'N/A'}")

        if ma_dict:
            ma_str = " / ".join([f"MA{k[-2:]}={v:,.0f}" for k, v in sorted(ma_dict.items())])
            lines.append(f"    均线: {ma_str}")

        # 支撑阻力
        sr_parts = []
        if sup:
            sr_parts.append(f"支撑 ${sup:,.0f}")
        if res:
            sr_parts.append(f"阻力 ${res:,.0f}")
        if sr_parts:
            lines.append(f"    支撑/阻力: {', '.join(sr_parts)}")
        if atr_val:
            lines.append(f"    ATR(14): {atr_val:.2f}")
        lines.append(f"    综合信号: **{sig}**（多 {bull_ct} / 空 {bear_ct}）")

    time.sleep(2)

    # ── 3. ETH / SOL 快照 ──
    lines.append("")
    lines.append("**【主流加密货币】**")
    for ticker, name in [("ETH-USD", "Ethereum"), ("SOL-USD", "Solana")]:
        try:
            df = yf.download(ticker, period="30d", interval="1d", auto_adjust=True, progress=False)
            if not df.empty:
                closes = df['Close'].dropna()
                if isinstance(closes, pd.DataFrame):
                    closes = closes[ticker].dropna()
                price = float(closes.iloc[-1])
                prev  = float(closes.iloc[-2]) if len(closes) >= 2 else price
                chg   = round((price - prev) / prev * 100, 2)
                rsi_v = rsi_calc(closes)
                rsi_e = "💚" if rsi_v and rsi_v > 55 else ("🧡" if rsi_v and rsi_v < 45 else "🟡")
                lines.append(f"  {name}: **${price:,.2f}** ({fmt(chg, True)}) RSI {rsi_e}{rsi_v}")
            time.sleep(1.5)
        except Exception as e:
            lines.append(f"  {name}: 获取失败")

    time.sleep(2)

    # ── 4. 全球指数 + 贵金属 ──
    INDEX_MAP = {
        "S&P 500": "^GSPC", "Dow Jones": "^DJI", "NASDAQ": "^IXIC",
        "FTSE 100": "^FTSE", "Nikkei 225": "^N225",
        "SSE 上证": "000001.SS", "Hang Seng": "^HSI", "DAX": "^GDAXI",
    }
    lines.append("")
    lines.append("**【全球指数】**")
    try:
        data = yf.download(" ".join(INDEX_MAP.values()), period="5d", interval="1d", auto_adjust=True, progress=False)
        if not data.empty:
            for name, ticker in INDEX_MAP.items():
                try:
                    closes = data['Close'][ticker].dropna() if ticker in data['Close'].columns else pd.Series()
                    if len(closes) >= 2:
                        cur, prv = float(closes.iloc[-1]), float(closes.iloc[-2])
                        lines.append(f"  {name}: **{cur:,.2f}** ({fmt((cur-prv)/prv*100, True)})")
                except:
                    pass
    except Exception as e:
        lines.append(f"  获取失败: {e}")

    time.sleep(2)

    lines.append("")
    lines.append("**【贵金属多周期分析】**")
    for metal_name, ticker in [("黄金", "GC=F"), ("白银", "SI=F")]:
        ms = metal_signal(ticker, metal_name)
        d1 = ms.get('1D', {})
        w1 = ms.get('1W', {})
        adv = ms.get('advice', {})
        da  = adv.get('daily',  {})
        wa  = adv.get('weekly', {})
        kl  = adv.get('key_levels', {})

        price_d = d1.get('price')
        rsi_d   = d1.get('rsi')
        rsi_e   = "💚" if rsi_d and rsi_d > 55 else ("🧡" if rsi_d and rsi_d < 45 else "🟡")

        lines.append(f"  ── {metal_name} ──")
        if price_d:
            lines.append(f"    日线价格: **${price_d:,.2f}** RSI {rsi_e}{rsi_d if rsi_d else 'N/A'}")

        dif_d = d1.get('dif'); dea_d = d1.get('dea')
        if dif_d and dea_d:
            macd_e = "🟢" if dif_d > dea_d else "🔴"
            lines.append(f"    日线MACD: {macd_e}{'金叉' if dif_d > dea_d else '死叉'}")

        if d1.get('ma'):
            ma_s = "/".join([f"MA{k[-2:]}={v:,.0f}" for k,v in sorted(d1['ma'].items())])
            lines.append(f"    日线均线: {ma_s}")

        if kl.get('support') or kl.get('resistance'):
            sup_p = f"${kl['support']:,.0f}" if kl.get('support') else "N/A"
            res_p = f"${kl['resistance']:,.0f}" if kl.get('resistance') else "N/A"
            lines.append(f"    关键支撑/阻力: {sup_p} / {res_p}")

        # 每日建议
        da_act  = da.get('action', 'N/A')
        da_conf = da.get('confidence', '')
        da_scr  = da.get('score', 50)
        da_score_bar = "█" * int(da_scr/10) + "░" * (10 - int(da_scr/10))
        lines.append(f"    📅 每日建议: **{da_act}**（{da_conf}）{da_score_bar} {da_scr}/100")

        # 每周建议
        wa_act  = wa.get('action', 'N/A')
        wa_conf = wa.get('confidence', '')
        wa_scr  = wa.get('score', 50)
        wa_score_bar = "█" * int(wa_scr/10) + "░" * (10 - int(wa_scr/10))
        lines.append(f"    📆 每周建议: **{wa_act}**（{wa_conf}）{wa_score_bar} {wa_scr}/100")

        time.sleep(1.5)

    elapsed = time.time() - t0

    # ── 构建消息 ──
    msg = f"📊 **Quinn 市场扫描** — {now}\n\n" + "\n".join(lines)
    msg += f"\n\n_耗时: {elapsed:.1f}s · 仅供参考，不构成投资建议_"

    # 写入文件
    report_path = f"{WORKSPACE}/reports/market_scan_{today_file}.txt"
    latest_path = f"{WORKSPACE}/reports/latest_market_scan.txt"

    for path in [report_path, latest_path]:
        with open(path, "w") as f:
            f.write(f"# Quinn 市场扫描 {now}\n\n")
            f.write(msg)

    with open(f"{WORKSPACE}/logs/market_scan.log", "a") as f:
        f.write(f"[{now}] 完成，耗时 {elapsed:.1f}s\n")

    print(msg)
    print(f"\n✅ 扫描完成 ({elapsed:.1f}s)")
    return report_path

if __name__ == "__main__":
    main()
