#!/bin/bash
# Quinn 市场扫描脚本
# 每天 15:00 执行

WORKSPACE="/Volumes/1TB/openclaw/jinrong-bot"
LOG_FILE="$WORKSPACE/logs/market_scan.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 市场扫描开始" >> "$LOG_FILE"

/opt/homebrew/bin/python3 "$WORKSPACE/scripts/market_scan.py" >> "$LOG_FILE" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 市场扫描完成" >> "$LOG_FILE"
