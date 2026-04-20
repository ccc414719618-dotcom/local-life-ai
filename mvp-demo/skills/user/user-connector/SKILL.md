# 本地生活 AI - 用户端 Skill

> 让 AI 帮助用户发现附近好店、排队、预约

---

## 🎯 这是什么？

这是一个 **AI Skill**，安装后你的 AI 就能：
- 🔍 搜索附近的商家（餐厅、火锅、面馆等）
- 📋 查看实时排队情况
- 🎫 线上取号
- 📅 预约座位

---

## 📦 安装方式

### 方式一：一键安装（推荐）
```
skill install @local-life-ai/user-connector
```

### 方式二：手动安装
1. 下载 SKILL.md 文件
2. 放入你的 AI Agent 的 skills 目录
3. AI 重启后自动加载

---

## 🚀 快速开始

安装成功后，告诉 AI：

**"我想找附近的饺子馆"**

AI 会自动调用本地生活平台 API，搜索附近的饺子馆并返回结果。

---

## 💬 对话示例

### 示例 1：找店
**你说**：帮我找附近的饺子馆

**AI 回答**：
```
找到了 2 家饺子馆：

✅ 金谷园饺子馆
   📍 海淀区学院路甲38号
   🌟 低油脂，适合减肥
   🕐 营业中

✅ 兴华家常菜
   📍 海淀区语言大学附近
   🌟 家常菜、经济实惠
   🕐 营业中
```

### 示例 2：取号
**你说**：帮我在金谷园排个号，2位

**AI 回答**：
```
✅ 取号成功！
🪑 排队号：A32
⏱️ 预计等待：7分钟
📍 地点：海淀区学院路甲38号
```

### 示例 3：预约
**你说**：我想预约兴华家常菜，明天晚上7点，3位

**AI 回答**：
```
✅ 预约成功！
🪑 预约号：B20260421001
📅 时间：2026-04-21 19:00
👥 人数：3位
🏠 地点：海淀区语言大学附近
```

---

## ⚙️ API 配置

### 本地开发
默认连接本地服务注册平台：
```
http://localhost:3000
```

### 修改 API 地址
如果服务部署在其他地址，编辑 SKILL.md 中的 `BASE` 变量：
```javascript
const BASE = "http://你的服务器地址:端口";
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
| 搜索商家 | `GET /mcp/search?q=关键词` |
| 查看排队 | `POST /mcp/{service_id}/call` |
| 取号 | `POST /mcp/{service_id}/call` |
| 预约 | `POST /mcp/{service_id}/call` |

### 调用示例
```bash
# 搜索商家
curl "http://localhost:3000/mcp/search?q=火锅"

# 查看排队
curl -X POST http://localhost:3000/mcp/jin_001/call \
  -H "Content-Type: application/json" \
  -d '{"tool":"get_queue_status","parameters":{}}'
```

---

## 📁 文件结构

```
user-connector/
├── SKILL.md      # 本文件 - Skill 定义
├── install.sh    # 安装脚本
├── llai         # CLI 工具（可选）
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
