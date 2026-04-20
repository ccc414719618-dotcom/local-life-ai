# 本地生活 AI - 商户端 Skill

> 让 AI 帮助商家 7×24 小时自动接待客户

---

## 🎯 这是什么？

这是一个 **AI Skill**，安装后你的 AI 就能：
- 📊 查看今日营业数据看板
- 📋 查看实时排队列表
- 📅 查看预约到店情况
- 🪑 查看桌台占用状态
- 🔧 位置校准（提高推荐精度）

---

## 📦 安装方式

### 方式一：一键安装（推荐）
```
skill install @local-life-ai/merchant-connector
```

### 方式二：手动安装
1. 下载 SKILL.md 文件
2. 放入你的 AI Agent 的 skills 目录
3. AI 重启后自动加载

---

## 🚀 快速开始

安装成功后，告诉 AI：

**"我想开通商家服务"**

AI 会引导你完成以下设置：
1. 输入店铺名称
2. 确认店铺地址（自动通过 IP 定位）
3. 校准精确位置

---

## 💬 对话示例

### 示例 1：查看今日营业
**你说**：看看今天的营业情况

**AI 回答**：
```
📊 今日数据看板 - 金谷园饺子馆

🕐 数据时间：14:30
━━━━━━━━━━━━━━━
⏳ 排队等待：0 桌
🎫 今日取号：3 人
📅 今日预约：2 人
🪑 预约待到：1 人
━━━━━━━━━━━━━━━
桌台状态：共 12 桌，空闲 8 桌
```

### 示例 2：查看排队列表
**你说**：现在排队多少人？

**AI 回答**：
```
📋 排队列表

目前无排队

今日取号记录：
  #1  A31  14:02  2人
  #2  A32  14:15  3人
  #3  A33  14:28  4人
```

### 示例 3：查看预约列表
**你说**：今天有几个人预约？

**AI 回答**：
```
📅 预约列表 - 今日

待到店：
  🪑 B31  19:00  2人
  🪑 B32  20:00  3人

已到店：
  ✅ B20  12:00  4人（已完成）
```

### 示例 4：校准位置
**你说**：位置不准，帮我校准一下

**AI 回答**：
```
🔧 位置校准

请打开以下链接进行位置校准：
http://localhost:3000/locate?shop_id=jin_001

校准后，AI 推荐会更精准！
```

---

## ⚙️ API 配置

### API 地址
服务已部署在 Vercel 上：
```
https://local-life-registry.vercel.app
```

### 修改 API 地址
如果服务部署在其他地址，编辑 SKILL.md 中的 `BASE` 变量：
```javascript
const BASE = "https://local-life-registry.vercel.app";
```

---

## 🏪 支持的商家

| 商家 | service_id | 类型 | 特色 |
|------|------------|------|------|
| 金谷园饺子馆 | `jin_001` | 饺子 | 低油脂、减肥友好 |
| 宏缘火锅 | `hong_001` | 火锅 | 鸳鸯锅、包间 |
| 季多西面馆 | `ji_001` | 面馆 | 现拉面、手擀面 |
| 兴华家常菜 | `xin_001` | 家常菜 | 经济实惠 |

---

## 🔧 技术细节

### API 端点
| 功能 | 端点 |
|------|------|
| 数据看板 | `GET /api/merchant/{service_id}/dashboard` |
| 排队列表 | `GET /api/merchant/{service_id}/dashboard` |
| 预约列表 | `GET /api/merchant/{service_id}/dashboard` |
| 桌台状态 | `GET /api/merchant/{service_id}/tables` |

### 调用示例
```bash
# 查看数据看板
curl http://localhost:3000/api/merchant/jin_001/dashboard

# 查看桌台状态
curl http://localhost:3000/api/merchant/jin_001/tables
```

---

## 📁 文件结构

```
merchant-connector/
├── SKILL.md      # 本文件 - Skill 定义
├── install.sh    # 安装脚本
├── llm          # 商户命令行工具（可选）
└── skill.json    # Skill 元数据
```

---

## 🤝 加入我们

如果你也是 AI 开发者，欢迎：
- ⭐ Star 本项目
- 🐛 提交 Bug
- 📝 完善文档

**GitHub**: https://github.com/ccc414719618-dotcom/local-life-ai

---

## 📄 License

MIT
