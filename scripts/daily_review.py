#!/usr/bin/env python3
"""
Quinn 每日复盘
每天 00:00 执行 - 汇总今日报告 + 异常检测 + 记忆更新
输出：写入复盘文件 + 打印摘要
"""
import sys
import json
import os
from datetime import datetime, date

WORKSPACE = "/Volumes/1TB/openclaw/jinrong-bot"
sys.path.insert(0, WORKSPACE)

def main():
    today = date.today().strftime('%Y-%m-%d')
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    today_file = today.replace('-', '')
    log_path = f"{WORKSPACE}/logs/daily_review.log"
    os.makedirs(f"{WORKSPACE}/memory", exist_ok=True)
    os.makedirs(f"{WORKSPACE}/reports", exist_ok=True)

    # ── 读取今日 push 日志 ──
    push_log_path = f"{WORKSPACE}/finance/reports/push_log.json"
    btc_price = None
    rsi = None
    overall = None
    doc_url = None

    if os.path.exists(push_log_path):
        with open(push_log_path) as f:
            log = json.load(f)
        if today in log:
            entry = log[today]
            btc_price = entry.get('btc')
            rsi = entry.get('rsi')
            overall = entry.get('overall')
            doc_url = entry.get('doc_url')

    # ── 异常检测 ──
    alerts = []
    if rsi:
        if rsi > 75:
            alerts.append("⚠️ RSI 超买（{:.1f}），注意回调风险".format(rsi))
        elif rsi < 30:
            alerts.append("⚠️ RSI 超卖（{:.1f}），关注超跌反弹机会".format(rsi))
    if not alerts:
        alerts.append("✅ 今日无显著异常信号")

    # ── 读取今日新闻 ──
    news_lines = []
    news_path = f"{WORKSPACE}/finance/reports/latest_report.txt"
    if os.path.exists(news_path):
        with open(news_path) as nf:
            content = nf.read()
        if "新闻" in content or "news" in content.lower():
            for line in content.split("\n"):
                line = line.strip()
                if line and len(line) > 15:
                    news_lines.append(line)
                    if len(news_lines) >= 5:
                        break

    # ── 写入复盘文件 ──
    review_path = f"{WORKSPACE}/memory/{today}-review.md"
    with open(review_path, "w") as f:
        f.write(f"# {today} 每日复盘\n\n")
        f.write(f"_由 Quinn 自动生成 · {now}_\n\n")

        f.write("## 📊 今日行情回顾\n\n")
        if btc_price:
            f.write(f"- BTC 参考价: **${btc_price:,.2f}**\n")
        if rsi:
            f.write(f"- RSI(14): **{rsi:.1f}**\n")
        if overall:
            f.write(f"- 整体信号: **{overall}**\n")
        if doc_url:
            f.write(f"- 完整报告: {doc_url}\n")
        if not any([btc_price, rsi, overall]):
            f.write("_（今日报告尚未生成）_\n")

        f.write("\n## 📰 今日新闻摘要\n\n")
        if news_lines:
            for line in news_lines:
                f.write(f"- {line}\n")
        else:
            f.write("_（无可用新闻数据）_\n")

        f.write("\n## 🔍 异常检测\n\n")
        for alert in alerts:
            f.write(f"- {alert}\n")

        f.write("\n## 💡 明日关注\n\n")
        f.write("- 关注美联储官员讲话或重要经济数据发布\n")
        f.write("- 监控 RSI 是否从极端区域回落\n")
        f.write("- 检查恐慌贪婪指数变化\n")
        f.write("- 关注 BTC 能否突破关键阻力位\n")

    # ── 写入日志 ──
    with open(log_path, "a") as f:
        f.write(f"[{now}] Daily review completed\n")
        if btc_price:
            f.write(f"  BTC: {btc_price}, RSI: {rsi}, Signal: {overall}\n")

    # ── 构建摘要 ──
    msg = f"🌙 **Quinn 每日复盘** — {today}\n\n"
    if btc_price:
        msg += f"📌 BTC: **${btc_price:,.2f}**\n"
    if rsi:
        msg += f"📌 RSI: **{rsi:.1f}**\n"
    if overall:
        msg += f"📌 信号: **{overall}**\n"
    msg += "\n" + "\n".join(f"  {a}" for a in alerts)
    msg += f"\n\n📄 完整复盘: {review_path}\n"
    msg += "_仅供参考，不构成投资建议_"

    print(msg)
    print(f"\n✅ 复盘完成: {review_path}")
    return review_path

if __name__ == "__main__":
    main()
