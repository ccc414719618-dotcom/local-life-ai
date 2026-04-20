#!/bin/bash
# Capability Evolver 自动运行脚本

cd /Volumes/1TB/openclaw/bilibili-bot/skills/capability-evolver

# 运行进化（非审核模式）
node index.js run

# 记录运行时间
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Evolution cycle completed" >> /Volumes/1TB/openclaw/bilibili-bot/logs/evolve.log
