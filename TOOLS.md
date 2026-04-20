# TOOLS.md - Quinn 的工具箱

## B站运营工具

### 官方工具
- **创作中心** — 数据中心、粉丝分析、内容分析
- **花火平台** — 品牌合作接单
- **必剪** — B站官方剪辑工具
- **直播工具** — 直播姬、互动玩法

### 数据分析
- **飞瓜数据-B站** — UP主数据、竞品分析
- **新站数据** — 实时榜单、热门监控
- **火烧云数据** — 弹幕分析、观众画像

### 内容策划
- **B站热门** — 每日必看、每周必看
- **知乎热榜** — 选题灵感
- **微博热搜** — 热点追踪

---

## OpenClaw 工具

### 核心工具
- `browser` — B站网页浏览、数据抓取
- `web_search` — 搜索B站运营资料
- `web_fetch` — 读取B站 UP主页面、视频页
- `exec` — 运行本地脚本

### 飞书工具
- `feishu_im_user_message` — 发送飞书消息
- `feishu_sheet` — 数据表格管理
- `feishu_bitable_app_table_record` — 多维表格记录

---

## Quinn 金融分析框架

**框架位置：** `/Volumes/1TB/openclaw/jinrong-bot/finance/`

```python
from finance import ReportGenerator
print(ReportGenerator(use_akshare=False).generate_daily_report(['bitcoin', 'ethereum', 'solana']))
```

### 已集成模块

| 模块 | 数据源 | 状态 |
|------|--------|------|
| 加密货币价格 | CoinGecko | ✅ 实时 |
| BTC/ETH/SOL K线 | CoinGecko | ✅ 180根日K |
| MA/RSI/MACD/布林带 | 自计算 | ✅ |
| 恐慌贪婪指数 | Alternative.me | ✅ 实时 |
| 黄金/白银 | Yahoo Finance | ✅ |

### 核心文件

| 文件 | 功能 |
|------|------|
| `report_generator.py` | 主报告生成器 |
| `data_fetcher.py` | 数据获取 |
| `technical_analysis.py` | 技术指标 |
| `quinn.py` | CLI 入口 |
| `quinn_cron.py` | 定时推送脚本 |

### CLI 用法

```bash
# 生成单一币种报告
cd /Volumes/1TB/openclaw/jinrong-bot/finance
python quinn.py bitcoin

# 生成多币种报告
python quinn.py bitcoin ethereum solana

# 生成完整报告（含黄金白银）
python quinn.py --all

# 推送飞书
cd /Volumes/1TB/openclaw/jinrong-bot/finance
python send_report.py
```

---

## 快捷键/命令

```bash
# 查看 B 站热门
open https://www.bilibili.com/v/popular/all

# 查看创作中心
open https://member.bilibili.com/platform

# 飞瓜数据
open https://www.feigua.cn/bili
```

---

_工具是死的，用法是活的。持续更新。_

---

## 📸 飞书图片发送（已验证 - 2026-04-10）

### 核心方法

**发送图片到飞书并直接显示的步骤：**

```bash
# 1. 生成图片
mmx image "提示词" --out ~/Desktop/image.jpg

# 2. 复制到工作区
cp ~/Desktop/image.jpg /Volumes/1TB/openclaw/bilibili-bot/

# 3. 发送到飞书（使用 path 参数）
message(action="send", channel="feishu", path="/Volumes/1TB/openclaw/bilibili-bot/image.jpg")
```

### 关键要点

| 要点 | 说明 |
|------|------|
| **路径必须在白名单** | `/Volumes/1TB/openclaw/bilibili-bot/` 是阿B工作区，默认可用 |
| **Desktop 路径不行** | 不在媒体白名单中，会报错 `path-not-allowed` |
| **使用 `path` 参数** | 而非 `media` 或 `buffer` |
