#!/bin/bash
# Quinn 每日复盘脚本
# 每天 00:00 执行

WORKSPACE="/Volumes/1TB/openclaw/jinrong-bot"
LOG_FILE="$WORKSPACE/logs/daily_review.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 每日复盘开始" >> "$LOG_FILE"

/opt/homebrew/bin/python3 "$WORKSPACE/scripts/daily_review.py" >> "$LOG_FILE" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 每日复盘完成" >> "$LOG_FILE"
