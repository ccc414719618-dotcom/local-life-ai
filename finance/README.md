# Quinn 金融分析框架

> 🔍 专业金融分析工具，支持加密货币、贵金属、全球指数

## 已安装工具

- **OpenBB** - 金融数据平台
- **akshare** - A股/期货数据
- **yfinance** - 美股数据

## 文件结构

```
finance/
├── __init__.py           # 包入口
├── data_fetcher.py       # 数据获取模块
├── technical_analysis.py   # 技术分析模块
├── report_generator.py    # 报告生成模块
├── quinn.py              # 命令行入口
└── README.md             # 本文件
```

## 快速使用

```python
from finance import ReportGenerator

gen = ReportGenerator()
report = gen.generate_daily_report(['bitcoin', 'ethereum', 'solana'])
print(report)
```

## 命令行使用

```bash
# 默认分析 BTC + ETH
python3 -c "from finance import ReportGenerator; print(ReportGenerator().generate_daily_report())"

# 自定义币种
python3 -c "from finance import ReportGenerator; print(ReportGenerator().generate_daily_report(['bitcoin', 'solana']))"
```

## 功能列表

| 功能 | 状态 | 说明 |
|------|------|------|
| 实时价格 | ✅ | BTC/ETH/SOL 等 CoinGecko 支持的币种 |
| K线数据 | ✅ | 日K (最多180根) |
| MA分析 | ✅ | MA5/10/20/60 |
| RSI分析 | ✅ | 14日RSI |
| MACD分析 | ✅ | MACD + Signal + Histogram |
| 布林带 | ✅ | 20日布林带 |
| 支撑阻力 | ✅ | 三层支撑、三层阻力 |
| 恐慌贪婪指数 | ✅ | Alternative.me API |
| 贵金属 | 🔜 | 待集成 |
| A股/港股 | 🔜 | 待配置 akshare |
| 全球指数 | 🔜 | 待配置 yfinance/OpenBB |

## 数据来源

- **CoinGecko** - 加密货币实时价格和K线
- **Alternative.me** - 恐慌贪婪指数
- **OpenBB** - 扩展市场数据(待配置)
- **akshare** - A股/期货数据(待配置)

## 下一步

1. 配置 OpenBB 获取更多市场数据
2. 配置 akshare 获取A股数据
3. 集成贵金属实时数据
4. 添加定时任务自动推送飞书

---

*由 Quinn 投资研究员生成 | 2026-04-19*
