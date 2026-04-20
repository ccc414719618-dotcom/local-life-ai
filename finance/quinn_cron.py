#!/usr/bin/env python3
"""
Quinn 金融分析定时推送脚本
每天 09:00 自动生成报告并推送飞书
"""

import sys
import os

# 设置 Python 路径
sys.path.insert(0, '/Volumes/1TB/openclaw/jinrong-bot')

from finance.report_generator import ReportGenerator


def main():
    print("=" * 60)
    print("QUINN 金融分析定时推送")
    print("=" * 60)
    
    # 生成报告 (不使用 akshare，速度太慢)
    generator = ReportGenerator(use_akshare=False)
    report = generator.generate_daily_report(['bitcoin', 'ethereum', 'solana'])
    
    print(report)
    print("=" * 60)
    
    # 保存报告到文件
    report_file = '/Volumes/1TB/openclaw/jinrong-bot/finance/reports/latest_report.txt'
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\n✅ 报告已保存到: {report_file}")
    return report


if __name__ == '__main__':
    main()
