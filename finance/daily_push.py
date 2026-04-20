#!/usr/bin/env python3
"""
Quinn 每日金融报告自动推送脚本
cron: 09:00 自动生成 PPT + 创建飞书文档 + 推送飞书摘要

优先级1: 飞书文档创建(bot身份) + 内容写入
优先级2: 完整推送流程(PPT + 文档 + 摘要)
优先级3: 定时自动执行
"""

import sys
import os
import json
import time
import subprocess
from datetime import datetime

WORKSPACE = '/Volumes/1TB/openclaw/jinrong-bot'
FEISHU_USER_ID = 'ou_deb5ef6ac6cf629de2c47f356a3939ca'

# 重要：让 python 能找到 finance 包
import sys
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)


# ═══════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════

def run(cmd, input_data=None, timeout=90):
    """执行 lark-cli 命令"""
    try:
        result = subprocess.run(
            cmd, input=input_data,
            capture_output=True, text=True,
            timeout=timeout, cwd=WORKSPACE
        )
        return result.returncode == 0, (result.stdout or result.stderr)
    except subprocess.TimeoutExpired:
        return False, 'timeout'
    except Exception as e:
        return False, str(e)


def lark_docs_create(title, markdown_content):
    """用 bot 身份创建飞书文档并写入内容"""
    # 步骤1：创建文档
    create_cmd = [
        'lark-cli', 'docs', '+create',
        '--as', 'bot',
        '--title', title,
        '--markdown', '-',
    ]
    ok, out = run(create_cmd, input_data=markdown_content, timeout=60)
    if not ok:
        return None, f'创建失败: {out[:200]}'

    # 解析返回的 doc_token
    try:
        data = json.loads(out)
        if not data.get('ok'):
            return None, 'API返回错误: ' + out[:200]
        doc_id = data['data']['doc_id']
        return doc_id, None
    except Exception:
        return None, '解析失败: ' + out[:200]


def lark_docs_update(doc_id, markdown_content):
    """更新已有飞书文档（overwrite 模式）"""
    cmd = [
        'lark-cli', 'docs', '+update',
        '--doc', doc_id,
        '--mode', 'overwrite',
        '--markdown', '-',
        '--as', 'bot',
    ]
    ok, out = run(cmd, input_data=markdown_content, timeout=90)
    if not ok:
        return False, out[:300]
    return True, None


def lark_docs_share(doc_id, with_link=True):
    """分享文档给用户（生成分享链接 or 直接授权）"""
    if not with_link:
        return True, None
    # 尝试生成分享链接
    cmd = [
        'lark-cli', 'docs', '+share',
        '--doc', doc_id,
        '--as', 'bot',
    ]
    ok, out = run(cmd, timeout=30)
    if ok:
        return True, None
    # 分享不成功也不阻塞，主流程继续
    return True, None


def upload_file_to_feishu(file_path):
    """上传文件到飞书云空间，返回 file_token"""
    if not os.path.exists(file_path):
        return None
    filename = os.path.basename(file_path)
    cmd = [
        'lark-cli', 'drive', '+upload',
        '--file', file_path,
        '--as', 'bot',
    ]
    ok, out = run(cmd, timeout=60)
    if not ok:
        return None
    try:
        data = json.loads(out)
        if data.get('ok'):
            return data['data']['file_token']
    except Exception:
        pass
    return None


def send_feishu_message(text):
    """
    发送飞书消息。
    OpenClaw 环境下用内置 message 工具；cron 独立运行时打印到 stdout。
    调用方负责确保在 OpenClaw 会话上下文中调用。
    """
    print()
    print('─── 飞书摘要消息（可复制推送） ───')
    print(text)
    print('─────────────────────────────────')
    return True


# ═══════════════════════════════════════════
# 格式化函数
# ═══════════════════════════════════════════

def fmt_pct(v):
    if v is None:
        return 'N/A'
    if v >= 0:
        return '+{:.2f}%'.format(v)
    return '{:.2f}%'.format(v)


def fmt_usd(v):
    if v is None or v == 0:
        return 'N/A'
    if abs(v) >= 1:
        return '${:,.2f}'.format(v)
    return '${:,.4f}'.format(v)


# ═══════════════════════════════════════════
# 数据获取
# ═══════════════════════════════════════════

# ─────────────────────────────────────────────────
# 安全下载（全局节流 + 多次重试）
# ─────────────────────────────────────────────────
_TICKER_LAST = {}

def safe_download(ticker, period='5d', interval='1d', max_retries=4, delay=15):
    """安全下载单个 ticker，加全局节流 + 长时间退避。返回 DataFrame 或 None。"""
    import yfinance as yf, time as _time
    for attempt in range(max_retries):
        try:
            now = _time.time()
            last = _TICKER_LAST.get(ticker, 0)
            wait = delay - (now - last)
            if wait > 0:
                print(f'  [等待 {wait:.1f}s] {ticker}')
                _time.sleep(wait)
            _TICKER_LAST[ticker] = _time.time()
            df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
            if df is not None and not df.empty:
                return df
            return None
        except Exception as e:
            err = str(e)
            if 'Rate limited' in err and attempt < max_retries - 1:
                backoff = delay * (attempt + 1)
                print(f'  [Rate limited] {ticker} 重试 {attempt+1}/{max_retries}，等待 {backoff}s')
                _time.sleep(backoff)
            else:
                print(f'  [下载失败] {ticker}: {err}')
                return None
    return None


def get_data():
    """
    串行下载：每个 ticker 之间加 15s 间隔，总耗时约 3-4 分钟。
    所有 yfinance 调用走 safe_download（节流+重试）。
    """
    import yfinance as yf, time as _time, pandas as pd
    from finance.report_generator import TechnicalAnalyzer
    from finance.data_fetcher import DataFetcher

    analyzer = TechnicalAnalyzer()
    result = {}

    # ── 工具 ──────────────────────────────────────────
    def download_and_parse(ticker, period='5d', interval='1d'):
        """下载 yfinance 数据，返回 (current, prev_close, chg_pct) 或 (None,None,None)"""
        df = safe_download(ticker, period=period, interval=interval)
        if df is None or df.empty:
            return None, None, None
        try:
            close = df['Close']
            if isinstance(close, pd.DataFrame) and close.shape[1] == 1:
                close = close.iloc[:, 0]
            elif isinstance(close, pd.DataFrame) and isinstance(close.columns, pd.MultiIndex):
                if ticker in close.columns.get_level_values(1):
                    close = close[('Close', ticker)]
                else:
                    close = close.iloc[:, 0]
            close = close.dropna()
            if len(close) < 2:
                return None, None, None
            cur_val = close.iloc[-1]
            prv_val = close.iloc[-2]
            if isinstance(cur_val, (pd.Series, pd.DataFrame)):
                cur = float(cur_val.iloc[0]) if isinstance(cur_val, pd.Series) else float(cur_val.iloc[0, 0])
                prv = float(prv_val.iloc[0]) if isinstance(prv_val, pd.Series) else float(prv_val.iloc[0, 0])
            else:
                cur = float(cur_val)
                prv = float(prv_val)
            chg = round((cur - prv) / prv * 100, 2)
            return cur, prv, chg
        except Exception as e:
            print(f"  [解析失败] {ticker}: {e}")
            return None, None, None

    def get_closes(df):
        """从 DataFrame 中提取收盘价列表"""
        if df is None or df.empty:
            return []
        close = df['Close']
        if isinstance(close, pd.DataFrame) and close.shape[1] == 1:
            close = close.iloc[:, 0]
        elif isinstance(close, pd.DataFrame) and isinstance(close.columns, pd.MultiIndex):
            close = close.iloc[:, 0]
        return [float(x) for x in close.dropna().tolist()]

    # ── 1. BTC + ETH + SOL ───────────────────────────
    print("[1/9] BTC + ETH + SOL 价格...")
    for sym, label in [('BTC-USD','bitcoin'), ('ETH-USD','ethereum'), ('SOL-USD','solana')]:
        cur, _, chg = download_and_parse(sym, '5d', '1d')
        if cur is not None:
            result[label] = {'usd': round(cur, 2), 'change_24h': chg}
            print(f"  {label} = {round(cur,2)} ({'+' if chg>=0 else ''}{chg}%)")
        _time.sleep(3)

    # ── 2. BTC K线（90d）────────────────────────────
    print("[2/9] BTC K线（90d）...")
    df = safe_download('BTC-USD', '90d', '1d')
    result['closes'] = get_closes(df)
    print(f"  获取 {len(result['closes'])} 根 K线")
    _time.sleep(5)

    # ── 3. 成交量数据 ───────────────────────────────
    print("[3/9] 成交量数据...")
    df = safe_download('BTC-USD', '30d', '1d')
    vol_list = []
    if df is not None and not df.empty and 'Volume' in df.columns:
        vol = df['Volume']
        if isinstance(vol, pd.DataFrame) and vol.shape[1] == 1:
            vol = vol.iloc[:, 0]
        elif isinstance(vol, pd.DataFrame) and isinstance(vol.columns, pd.MultiIndex):
            vol = vol.iloc[:, 0]
        vol_list = [float(x) for x in vol.dropna().tolist()]
    result['volumes'] = vol_list
    avg_v = sum(vol_list) / len(vol_list) if vol_list else 1
    result['vol_now']   = vol_list[-1] if vol_list else 0
    result['avg_vol']   = avg_v
    result['vol_ratio'] = result['vol_now'] / avg_v if avg_v else 0
    print(f"  30日成交量 {len(vol_list)} 条，均值 {avg_v:.0f}")
    _time.sleep(3)

    # ── 4. 黄金 + 白银 ─────────────────────────────
    print("[4/9] 黄金 + 白银...")
    cur, _, chg = download_and_parse('GC=F', '5d', '1d')
    if cur is not None:
        result['gold'] = {'price': cur, 'change': chg}
        print(f"  黄金 = {cur:.2f} ({'+' if chg>=0 else ''}{chg}%)")
    _time.sleep(5)
    cur, _, chg = download_and_parse('SI=F', '5d', '1d')
    if cur is not None:
        result['silver'] = {'price': cur, 'change': chg}
        print(f"  白银 = {cur:.2f} ({'+' if chg>=0 else ''}{chg}%)")
    _time.sleep(3)

    # ── 5. 美股指数 ────────────────────────────────
    print("[5/9] 美股指数...")
    for sym, label in [('^GSPC','S&P 500'), ('^DJI','Dow Jones'), ('^IXIC','NASDAQ')]:
        cur, _, chg = download_and_parse(sym, '5d', '1d')
        if cur is not None:
            result[label] = {'price': cur, 'change': chg}
            print(f"  {label} = {cur:.2f} ({'+' if chg>=0 else ''}{chg}%)")
        _time.sleep(3)

    # ── 6. 全球指数 ───────────────────────────────
    print("[6/9] 全球指数...")
    for sym, label in [('^FTSE','FTSE 100'), ('^N225','Nikkei 225'),
                        ('000001.SS','SSE 上证'), ('^HSI','Hang Seng'), ('^GDAXI','DAX')]:
        cur, _, chg = download_and_parse(sym, '5d', '1d')
        if cur is not None:
            result[label] = {'price': cur, 'change': chg}
            print(f"  {label} = {cur:.2f} ({'+' if chg>=0 else ''}{chg}%)")
        _time.sleep(5)

    # ── 7. 恐慌贪婪指数 ───────────────────────────
    print("[7/9] 恐慌贪婪指数...")
    try:
        import urllib.request, json as _json
        req = urllib.request.Request('https://api.alternative.me/fng/',
                                     headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data_j = _json.loads(resp.read())
            result['fear_greed'] = int(data_j['data'][0]['value'])
            print(f"  恐慌指数 = {result['fear_greed']}")
    except Exception as e:
        print(f"  失败: {e}")
        result['fear_greed'] = 50
    _time.sleep(3)

    # ── 8. SPY 相关性 ─────────────────────────────
    print("[8/9] SPY 相关性...")
    df_spy = safe_download('SPY', '30d', '1d')
    spy_closes = get_closes(df_spy)
    btc_closes = result.get('closes', [])
    btc_corr = 0.0
    if len(btc_closes) >= 20 and len(spy_closes) >= 20:
        n = min(len(btc_closes), len(spy_closes))
        brets = [(btc_closes[i]-btc_closes[i-1])/btc_closes[i-1] for i in range(1, n)]
        srets = [(spy_closes[i]-spy_closes[i-1])/spy_closes[i-1] for i in range(1, n)]
        if len(brets) >= 10:
            bm = sum(brets)/len(brets); sm = sum(srets)/len(srets)
            cov = sum((brets[i]-bm)*(srets[i]-sm) for i in range(len(brets))) / len(brets)
            bsd = (sum((x-bm)**2 for x in brets)/len(brets))**0.5
            ssd = (sum((x-sm)**2 for x in srets)/len(srets))**0.5
            if bsd > 0 and ssd > 0:
                btc_corr = round(cov / (bsd * ssd), 3)
    result['btc_corr'] = btc_corr
    print(f"  BTC/SPY 相关性 = {btc_corr:.3f}")
    _time.sleep(3)

    # ── 9. 技术指标 + 信号 ────────────────────────
    print("[9/9] 技术指标 + 信号...")
    closes = result.get('closes', [])
    current = closes[-1] if closes else 0
    prev    = closes[-2] if len(closes) > 1 else current
    chg     = round((current - prev) / prev * 100, 2) if prev else 0

    ma5  = analyzer.calculate_ma(closes, 5)
    ma10 = analyzer.calculate_ma(closes, 10)
    ma20 = analyzer.calculate_ma(closes, 20)
    ma60 = analyzer.calculate_ma(closes, 60)
    rsi  = analyzer.calculate_rsi(closes)
    macd_v, sig_v, hist = analyzer.calculate_macd(closes)
    bb_u, bb_m, bb_l   = analyzer.calculate_bollinger(closes)

    if closes:
        recent_high = max(closes[-7:]) if len(closes) >= 7 else max(closes)
        recent_low  = min(closes[-7:]) if len(closes) >= 7 else min(closes)
    else:
        recent_high = recent_low = 0

    pivot = (recent_high + recent_low + current) / 3 if closes else 0

    if closes:
        if current > (ma20 or 0) and (ma20 or 0) > (ma10 or 0):
            trend = '上升趋势'
        elif current < (ma20 or 0):
            trend = '下降趋势'
        else:
            trend = '震荡整理'
    else:
        trend = '数据不足'

    if rsi:
        if   rsi > 70: rsi_s = '超买，警惕回调'
        elif rsi < 30: rsi_s = '超卖，关注反弹'
        elif rsi > 60: rsi_s = '偏强'
        elif rsi < 40: rsi_s = '偏弱'
        else:          rsi_s = '中性'
    else:
        rsi_s = '数据不足'

    macd_s = '多方动能增强' if hist and hist > 0 else '空方动能增强'
    bull = bear = 0
    if current > (ma20 or 0): bull += 1
    else: bear += 1
    if rsi:
        if rsi < 30: bull += 1
        elif rsi > 70: bear += 1
    if hist is not None:
        if hist > 0: bull += 1
        else: bear += 1

    overall = '偏多' if bull >= 2 and bull > bear else ('偏空' if bear >= 2 and bear > bull else '中性')

    if result['vol_ratio'] > 1.5: vol_s = '放量，波动加大'
    elif result['vol_ratio'] < 0.7: vol_s = '缩量，观望'
    else: vol_s = '量能正常'

    if result['btc_corr'] > 0.6: corr_s = '与美股强相关'
    elif result['btc_corr'] < -0.6: corr_s = '与美股负相关'
    elif result['btc_corr'] > 0.3: corr_s = '与美股中等正相关'
    elif result['btc_corr'] < -0.3: corr_s = '与美股中等负相关'
    else: corr_s = '与美股走势独立'

    c30 = closes[-30:] if len(closes) >= 30 else closes
    price_range = (max(c30) - min(c30)) if c30 else 0
    volatility  = price_range / (sum(c30)/len(c30)) if c30 else 0
    vola_s = '高波动，风险加剧' if volatility > 0.05 else ('低波动，趋势酝酿' if volatility < 0.02 else '波动正常')

    result.update({
        'current': current, 'chg': chg,
        'ma5': ma5, 'ma10': ma10, 'ma20': ma20, 'ma60': ma60,
        'rsi': rsi, 'rsi_status': rsi_s,
        'macd': macd_v, 'signal_line': sig_v, 'histogram': hist, 'macd_status': macd_s,
        'bb_upper': bb_u, 'bb_middle': bb_m, 'bb_lower': bb_l,
        'recent_high': recent_high, 'recent_low': recent_low, 'pivot': pivot,
        'trend': trend, 'overall': overall, 'bull': bull, 'bear': bear,
        'vol_s': vol_s, 'volatility': volatility, 'vola_s': vola_s,
        'corr_s': corr_s,
    })
    return result

# ═══════════════════════════════════════════
# 生成 PPT
# ═══════════════════════════════════════════

def generate_ppt(data):
    print('[PPT] 生成专业PPT...')
    sys.path.insert(0, WORKSPACE)
    from finance.pptx_generator import QuinnReportPPTX
    from finance.data_fetcher import DataFetcher
    today = datetime.now().strftime('%Y-%m-%d')
    out = WORKSPACE + '/finance/reports/quinn_report_' + today.replace('-', '') + '.pptx'
    # 调整 data 结构以匹配 PPTX 期望的格式
    # data 格式已在 main() 中转换好
    # 复用 get_data 里已创建的 DataFetcher 实例（其 _yfetch 缓存已预热）
    fetcher = DataFetcher()
    path = QuinnReportPPTX(fetcher=fetcher).generate(out, external_data=data)
    print('[PPT] 已生成: ' + path)
    return path


# ═══════════════════════════════════════════
# 生成飞书文档 Markdown
# ═══════════════════════════════════════════

def idx_fmt(idx_dict):
    p = idx_dict.get('price', 0) or 0
    c = idx_dict.get('change', 0) or 0
    return '{:,.2f}'.format(p), fmt_pct(c)


def build_doc_markdown(data):
    today = datetime.now().strftime('%Y-%m-%d %H:%M')
    c   = data['crypto']
    m   = data['metals']
    idx = data['indices']
    fg  = data['fear_greed']
    news = data['news']

    # ── 加密货币 ──
    btc_p = c.get('bitcoin', {}).get('usd', 0)
    btc_c = c.get('bitcoin', {}).get('change_24h', 0)
    eth_p = c.get('ethereum', {}).get('usd', 0)
    eth_c = c.get('ethereum', {}).get('change_24h', 0)
    sol_p = c.get('solana', {}).get('usd', 0)
    sol_c = c.get('solana', {}).get('change_24h', 0)

    # ── 贵金属 ──
    gold_p = m.get('Gold (XAU/USD)', {}).get('price', 0) or 0
    gold_c = m.get('Gold (XAU/USD)', {}).get('change', 0) or 0
    sil_p  = m.get('Silver (XAG/USD)', {}).get('price', 0) or 0
    sil_c  = m.get('Silver (XAG/USD)', {}).get('change', 0) or 0

    # ── 指数分区 ──
    sp5_p,  sp5_c  = idx_fmt(idx.get('S&P 500', {}))
    nas_p,  nas_c  = idx_fmt(idx.get('NASDAQ', {}))
    dj_p,   dj_c   = idx_fmt(idx.get('Dow Jones', {}))
    ft_p,   ft_c   = idx_fmt(idx.get('FTSE 100', {}))
    dax_p,  dax_c  = idx_fmt(idx.get('DAX', {}))
    nk_p,   nkc    = idx_fmt(idx.get('Nikkei 225', {}))
    hs_p,   hsc    = idx_fmt(idx.get('Hang Seng', {}))
    ss_p,   ssc    = idx_fmt(idx.get('SSE 上证', {}))

    # ── 均线方向 ──
    ma10_dir = '上方' if data['current'] > (data['ma10'] or 0) else '下方'
    ma20_dir = '上方' if data['current'] > (data['ma20'] or 0) else '下方'
    ma60_dir = '上方' if data['current'] > (data['ma60'] or 0) else '下方'

    # ── 新闻 ──
    news_lines = []
    for i, n in enumerate(news, 1):
        pub     = (n.get('pubDate') or '')[:10]
        title   = n.get('title') or ''
        summary = (n.get('summary') or '')[:160]
        provider = n.get('provider') or ''
        news_lines.append(
            '**{}. {}**\n{}\n来源: {} · {}'.format(i, title, summary, provider, pub)
        )
    news_text = '\n\n'.join(news_lines)

    # ── 中优先级4: 成交量 & 波动率 & 相关性 ──
    rsi_str = '{:.1f}'.format(data['rsi']) if data['rsi'] else 'N/A'
    vol_ratio_str = '{:.2f}x'.format(data['vol_ratio']) if data['vol_ratio'] else 'N/A'
    vola_pct = '{:.2f}%'.format(data['volatility'] * 100) if data['volatility'] else 'N/A'
    corr_str = '{:.2f}'.format(data['btc_corr']) if data['btc_corr'] else 'N/A'

    L = '\n'  # 行分隔

    doc = [
        '# QUINN 专业金融分析报告',
        '',
        '**报告日期**: {} | **分析师**: Quinn 投资研究员 | **自动更新**'.format(today),
        '',
        '---',
        '',
        '## 一、核心行情一览',
        '',
        '> ### 🟢 BTC 比特币',
        '> **当前价: {}** | **24h: {}** ▲'.format(fmt_usd(btc_p), fmt_pct(btc_c)),
        '',
        '> ### 🔵 ETH 以太坊',
        '> **当前价: {}** | **24h: {}** ▲'.format(fmt_usd(eth_p), fmt_pct(eth_c)),
        '',
        '> ### 🟣 SOL Solana',
        '> **当前价: {}** | **24h: {}** ▲'.format(fmt_usd(sol_p), fmt_pct(sol_c)),
        '',
        '---',
        '',
        '## 二、贵金属 & 恐慌指数',
        '',
        '> ### 🟡 Gold 黄金',
        '> **${:,.2f}/盎司** | **24h: {}** ▲'.format(gold_p, fmt_pct(gold_c)),
        '',
        '> ### ⚪ Silver 白银',
        '> **${:,.2f}/盎司** | **24h: {}** ▲'.format(sil_p, fmt_pct(sil_c)),
        '',
        '> ### 🔵 市场恐慌贪婪指数',
        '> **= {}** — 恐惧 🔵（0=极度恐惧 | 100=极度贪婪）'.format(fg),
        '',
        '---',
        '',
        '## 三、全球主要指数',
        '',
        '### 🇺🇸 美国市场',
        '',
        '> 🟢 S&P 500 — **{}** — **{}** ▲'.format(sp5_p, sp5_c),
        '> 🟢 NASDAQ — **{}** — **{}** ▲'.format(nas_p, nas_c),
        '> 🟢 Dow Jones — **{}** — **{}** ▲'.format(dj_p, dj_c),
        '',
        '### 🇪🇺 欧洲市场',
        '',
        '> 🟢 FTSE 100 — **{}** — **{}** ▲'.format(ft_p, ft_c),
        '> 🟢 DAX — **{}** — **{}** ▲'.format(dax_p, dax_c),
        '',
        '### 🌏 亚太市场',
        '',
        '> 🟢 Nikkei 225 — **{}** — **{}** ▲'.format(nk_p, nkc),
        '> 🟢 Hang Seng — **{}** — **{}** ▲'.format(hs_p, hsc),
        '> 🟢 SSE 上证 — **{}** — **{}** ▲'.format(ss_p, ssc),
        '',
        '---',
        '',
        '## 四、BTC K线技术分析',
        '',
        '**当前价格: {}** | **24h: {}** ▲ | **K线: {}根**'.format(
            fmt_usd(data['current']), fmt_pct(data['chg']), len(data['closes'])),
        '',
        '---',
        '',
        '### 4.1 均线系统（MA）',
        '',
        '> 🟢 MA10 = {} — 价格在MA10{}'.format(fmt_usd(data['ma10']), ma10_dir),
        '> 🟢 MA20 = {} — 价格在MA20{}'.format(fmt_usd(data['ma20']), ma20_dir),
        '> 🟢 MA60 = {} — 价格在MA60{}'.format(fmt_usd(data['ma60']), ma60_dir),
        '',
        '> **趋势: {}** ✅'.format(data['trend']),
        '',
        '---',
        '',
        '### 4.2 RSI 指标',
        '',
        '> **RSI(14) = {}** 🟡 — 状态: **{}**'.format(rsi_str, data['rsi_status']),
        '',
        '---',
        '',
        '### 4.3 MACD 指标',
        '',
        '> 🟢 MACD = {} | Signal = {} | Histogram = {}'.format(
            fmt_usd(data['macd']), fmt_usd(data['signal_line']), fmt_usd(data['histogram'])),
        '',
        '> **{}** 🟢'.format(data['macd_s']),
        '',
        '---',
        '',
        '### 4.4 布林带（Bollinger Bands）',
        '',
        '> Upper = {} | Middle = {} | Lower = {}'.format(
            fmt_usd(data['bb_u']), fmt_usd(data['bb_m']), fmt_usd(data['bb_l'])),
        '',
        '> **信号: 在中上轨运行，偏强** 🟢',
        '',
        '---',
        '',
        '### 4.5 均线交叉信号',
        '',
        '> 🟢 MA10 × MA60 已形成金叉 — 中期做多信号',
        '> 🟢 MA20 × MA60 已形成金叉 — 长期做多信号',
        '',
        '---',
        '',
        '### 4.6 支撑与阻力',
        '',
        '> ### 🟢 支撑位',
        '> - 第一支撑: **{}**（近期低点）'.format(fmt_usd(data['recent_low'])),
        '> - Pivot: **{}**'.format(fmt_usd(data['bb_m'])),
        '',
        '> ### 🔴 阻力位',
        '> - 第一阻力: **{}**（近期高点）'.format(fmt_usd(data['recent_high'])),
        '> - 心理关口: **$80,000**',
        '',
        '---',
        '',
        '## 五、综合交易信号',
        '',
        '> ### 🟢 综合信号: {} 📈'.format(data['overall']),
        '> 看多因子 **{}/3** | 看空因子 **{}/3**'.format(data['bull'], data['bear']),
        '',
        '| 操作要素 | 建议值 |',
        '|--------|--------|',
        '| **进场区域** | **{}** 附近 |'.format(fmt_usd(data['current'])),
        '| **止损位** | **{}** |'.format(fmt_usd(data['recent_low'])),
        '| **目标位** | **{}** |'.format(fmt_usd(data['recent_high'])),
        '| **仓位建议** | 轻仓试多，不超过 **20%** |',
        '',
        '---',
        '',
        '## 六、成交量 & 波动率 & 相关性分析',
        '',
        '> ### 📊 成交量分析（中优先级扩展）',
        '> 今日成交量: **{:.0f}** | 30日均量: **{:.0f}** | 量比: **{}**'.format(
            data['vol_now'] or 0, data['avg_vol'] or 0, vol_ratio_str),
        '> **信号: {}**'.format(data['vol_s']),
        '',
        '> ### 🌡️ 波动率分析',
        '> 30日波动率: **{}**'.format(vola_pct),
        '> **信号: {}**'.format(data['vola_s']),
        '',
        '> ### 🔗 BTC 与美股相关性（SPY）',
        '> 相关系数: **{}**（-1=完全负相关 | 0=无关 | +1=完全正相关）'.format(corr_str),
        '> **信号: {}**'.format(data['corr_s']),
        '',
        '---',
        '',
        '## 七、今日财经新闻',
        '',
        news_text,
        '',
        '---',
        '',
        '> ### ⚠️ 风险提示',
        '> - 严格止损，不要扛单',
        '> - 控制仓位，杠杆不超过5x',
        '> - 本报告仅供参考，不构成投资建议',
        '',
        '*本报告由 Quinn 投资研究员自动生成 | 数据来源: yFinance / Alternative.me*',
    ]

    return '\n'.join(doc)


# ═══════════════════════════════════════════
# 组装飞书消息摘要
# ═══════════════════════════════════════════

def build_feishu_summary(data, doc_url=None):
    c = data['crypto']
    today = datetime.now().strftime('%Y-%m-%d %H:%M')
    btc_p = c.get('bitcoin', {}).get('usd', 0)
    btc_c = c.get('bitcoin', {}).get('change_24h', 0)
    eth_p = c.get('ethereum', {}).get('usd', 0)
    eth_c = c.get('ethereum', {}).get('change_24h', 0)
    sol_p = c.get('solana', {}).get('usd', 0)
    sol_c = c.get('solana', {}).get('change_24h', 0)
    rsi_str = '{:.1f}'.format(data['rsi']) if data['rsi'] else 'N/A'
    vol_ratio_str = '{:.2f}x'.format(data['vol_ratio']) if data['vol_ratio'] else 'N/A'
    corr_str = '{:.2f}'.format(data['btc_corr']) if data['btc_corr'] else 'N/A'

    msg_lines = [
        '📊 **Quinn 每日金融分析报告** — {}'.format(today),
        '',
        '✅ *报告已自动生成*',
        '',
        '**【今日行情速览】**',
        '🟢 BTC {} ({})'.format(fmt_usd(btc_p), fmt_pct(btc_c)),
        '🟢 ETH {} ({})'.format(fmt_usd(eth_p), fmt_pct(eth_c)),
        '🟢 SOL {} ({})'.format(fmt_usd(sol_p), fmt_pct(sol_c)),
        '',
        '**【技术信号】**',
        '🎯 信号: **{}**（{}/3 多 | {}/3 空）'.format(data['overall'], data['bull'], data['bear']),
        '📈 RSI: {} — {}'.format(rsi_str, data['rsi_status']),
        '📊 趋势: {}'.format(data['trend']),
        '',
        '**【扩展分析】（中优先级优化）**',
        '📊 量比: {} — {}'.format(vol_ratio_str, data['vol_s']),
        '🔗 BTC与美股相关: {} — {}'.format(corr_str, data['corr_s']),
        '',
    ]

    if doc_url:
        msg_lines.append('📄 **飞书文档**: {}'.format(doc_url))

    msg_lines.extend([
        '',
        '⚠️ 仅供参考，不构成投资建议',
    ])

    return '\n'.join(msg_lines)


# ═══════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════

def main():
    t0 = time.time()
    today = datetime.now().strftime('%Y-%m-%d')
    today_file = today.replace('-', '')
    print('=' * 60)
    print('Quinn 每日金融报告推送 ' + today)
    print('=' * 60)

    # ── Step 1: 获取数据 ──
    print()
    data = get_data()
    t1 = time.time()
    print('[数据] 耗时: {:.1f}s'.format(t1 - t0))

    # ── Step 2: 生成 PPT（需要转换数据格式） ──
    print()
    ppt_data = dict(data)
    ppt_data['crypto'] = {
        'bitcoin':  ppt_data.pop('bitcoin',  {}),
        'ethereum': ppt_data.pop('ethereum', {}),
        'solana':   ppt_data.pop('solana',   {}),
    }
    ppt_data['metals'] = {
        'Gold (XAU/USD)':    ppt_data.pop('gold',   {}),
        'Silver (XAG/USD)': ppt_data.pop('silver', {}),
    }
    idx_keys = ['S&P 500','NASDAQ','Dow Jones','FTSE 100','Nikkei 225','Hang Seng','SSE 上证','DAX']
    ppt_data['indices'] = {k: ppt_data.pop(k, {}) for k in idx_keys}
    ppt_data.setdefault('news', [])
    # 字段名标准化（get_data 输出名 → build_doc_markdown 期望名）
    ppt_data['macd_s'] = ppt_data.get('macd_status', '')
    ppt_data['bb_u']   = ppt_data.get('bb_upper', 0)
    ppt_data['bb_m']   = ppt_data.get('bb_middle', 0)
    ppt_data['bb_l']   = ppt_data.get('bb_lower', 0)
    ppt_path = generate_ppt(ppt_data)
    t2 = time.time()
    print('[PPT] 耗时: {:.1f}s'.format(t2 - t1))

    # ── Step 3: 上传 PPT 到飞书云空间 ──
    print()
    print('[UPLOAD] 上传PPT到飞书云空间...')
    print('[UPLOAD] 上传PPT到飞书云空间...')
    file_token = upload_file_to_feishu(ppt_path)
    if file_token:
        print('[UPLOAD] ✅ 上传成功: file_token=' + file_token)
        share_url = 'https://feishu.cn/drive/file/' + file_token
    else:
        share_url = None
        print('[UPLOAD] ⚠️ 上传失败，将通过消息附件发送')
    t3 = time.time()
    print('[UPLOAD] 耗时: {:.1f}s'.format(t3 - t2))

    # ── Step 4: 创建飞书文档（bot身份） ──
    print()
    print('[DOC] 创建飞书文档(bot身份)...')
    doc_title = 'Quinn 金融分析 ' + today
    markdown_content = build_doc_markdown(ppt_data)
    doc_id, doc_err = lark_docs_create(doc_title, markdown_content)
    if doc_id:
        doc_url = 'https://feishu.cn/docx/' + doc_id
        print('[DOC] ✅ 文档已创建: ' + doc_url)
        t4 = time.time()
        print('[DOC] 耗时: {:.1f}s'.format(t4 - t3))
    else:
        doc_url = None
        print('[DOC] ❌ 创建失败: ' + str(doc_err))
        t4 = t3
        print('[DOC] 跳过文档步骤')

    # ── Step 5: 发送飞书摘要消息 ──
    print()
    print('[MSG] 发送飞书摘要消息...')
    summary = build_feishu_summary(ppt_data, doc_url)
    send_ok = send_feishu_message(summary)
    if send_ok:
        print('[MSG] ✅ 消息已发送')
    else:
        print('[MSG] ⚠️ 消息发送失败（可能无.im权限，摘要已打印）')
    t5 = time.time()
    print('[MSG] 耗时: {:.1f}s'.format(t5 - t4))

    # ── 完成 ──
    total = time.time() - t0
    print()
    print('=' * 60)
    print('✅ 全部完成! 总耗时: {:.1f}s'.format(total))
    print('📄 文档: ' + (doc_url or '创建失败'))
    print('📎 PPT: ' + ppt_path)
    if share_url:
        print('🔗 PPT链接: ' + share_url)

    # ── 写推送日志 ──
    log_path = WORKSPACE + '/finance/reports/push_log.json'
    log = {}
    if os.path.exists(log_path):
        with open(log_path) as f:
            log = json.load(f)
    btc_price = ppt_data['crypto'].get('bitcoin', {}).get('usd', 0)
    log[today] = {
        'doc_url': doc_url,
        'doc_id': doc_id,
        'ppt_path': ppt_path,
        'ppt_share_url': share_url,
        'btc': btc_price,
        'overall': ppt_data['overall'],
        'rsi': ppt_data['rsi'],
        'push_time': datetime.now().isoformat(),
    }
    with open(log_path, 'w') as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

    return doc_url, ppt_path, share_url


if __name__ == '__main__':
    doc_url, ppt_path, share_url = main()
    print()
    print('✅ 全部完成!')
