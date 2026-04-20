#!/usr/bin/env python3
"""
Quinn 金融分析命令行工具

用法:
    python3 quinn.py                    # 生成 BTC/ETH 分析
    python3 quinn.py --symbols bitcoin ethereum  # 分析多个币种
"""

import sys
import os
import argparse

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from report_generator import ReportGenerator


def main():
    parser = argparse.ArgumentParser(description='Quinn 专业金融分析')
    parser.add_argument('--symbols', nargs='+', default=['bitcoin', 'ethereum'],
                       help='要分析的加密货币符号')
    args = parser.parse_args()
    
    # 转换别名
    symbol_map = {'btc': 'bitcoin', 'eth': 'ethereum', 'sol': 'solana'}
    symbols = [symbol_map.get(s.lower(), s.lower()) for s in args.symbols]
    
    generator = ReportGenerator()
    report = generator.generate_daily_report(symbols)
    print(report)


if __name__ == '__main__':
    main()
