# Cron 任务配置

## 🕐 已配置任务

| 时间 | 任务 | 脚本 |
|------|------|------|
| 09:00 | 金融分析日报推送 | `finance/quinn_cron.py` |
| 15:00 | 市场动态扫描 | `scripts/market_scan.sh` |
| 00:00 | 每日复盘 + 记忆更新 | `scripts/daily_review.sh` |

## 📋 Crontab 内容

```cron
0 9 * * * cd /Volumes/1TB/openclaw/jinrong-bot/finance && /opt/homebrew/bin/python3 quinn_cron.py >> /Volumes/1TB/openclaw/jinrong-bot/finance/reports/cron.log 2>&1
0 15 * * * /Volumes/1TB/openclaw/jinrong-bot/scripts/market_scan.sh >> /Volumes/1TB/openclaw/jinrong-bot/logs/market_scan.log 2>&1
0 0 * * * /Volumes/1TB/openclaw/jinrong-bot/scripts/daily_review.sh >> /Volumes/1TB/openclaw/jinrong-bot/logs/daily_review.log 2>&1
```

## 🧪 手动测试

```bash
# 测试市场扫描
/Volumes/1TB/openclaw/jinrong-bot/scripts/market_scan.sh

# 测试每日复盘
/Volumes/1TB/openclaw/jinrong-bot/scripts/daily_review.sh

# 查看日志
tail -f /Volumes/1TB/openclaw/jinrong-bot/logs/market_scan.log
tail -f /Volumes/1TB/openclaw/jinrong-bot/logs/daily_review.log
```

## 🔧 管理命令

```bash
# 查看当前 crontab
crontab -l

# 编辑 crontab
crontab -e

# 删除所有任务
crontab -r
```

---

_更新于 2026-04-20_
