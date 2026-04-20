# 🏪 本地生活 AI 平台

> 让 AI 连接每一个好店。用户找店、排队、预约；商家自动接待、数据管理。

[![AI-First Platform](https://img.shields.io/badge/AI-First-Platform-purple)](https://github.com/ccc414719618-dotcom/local-life-ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](https://opensource.org/licenses/MIT)

---

## 🎯 两个版本

### 👤 用户端 - `@local-life-ai/user-connector`

帮助用户发现附近好店、排队、预约。

**安装命令**：
```bash
skill install @local-life-ai/user-connector
```

**功能**：
| 功能 | 说明 |
|------|------|
| 🔍 搜索服务 | 按关键词搜索附近商家 |
| 📋 查看排队 | 实时查看排队等待情况 |
| 🎫 线上取号 | 不到店也能排队 |
| 📅 预约座位 | 提前预约，到点用餐 |

---

### 🏪 商户端 - `@local-life-ai/merchant-connector`

帮助商家 7×24 小时自动接待客户。

**安装命令**：
```bash
skill install @local-life-ai/merchant-connector
```

**功能**：
| 功能 | 说明 |
|------|------|
| 📊 数据看板 | 实时查看今日营业数据 |
| 📋 排队管理 | 查看排队列表 |
| 📅 预约管理 | 查看预约到店情况 |
| 🔧 位置校准 | 校准店铺位置，提高推荐精度 |

---

## 🍜 餐饮店家自建 Skill

如果你想创建**完全自定义**的商家 AI Skill，可以用 `restaurant-skill-builder` 工具：

**功能**：
| 功能 | 说明 |
|------|------|
| 🏪 门店信息 | 地址、营业时间、联系方式 |
| 🍽️ 外卖配送 | 配送范围、平台 |
| 📶 Wi-Fi | 密码、连接方式 |
| 🎫 美团排队 | 在线取号、查进度、取消（可选） |

**使用方式**：
```bash
# 克隆工具
git clone https://github.com/ccc414719618-dotcom/restaurant-skill-builder.git \
  ~/.claude/skills/restaurant-skill-builder/

# 告诉 AI 帮你创建
# “帮我创建一个餐饮 Skill”
```

**详细文档**：[tools/restaurant-skill-builder/README.md](tools/restaurant-skill-builder/README.md)

---

## 🚀 快速启动

### 1. 克隆仓库
```bash
git clone https://github.com/ccc414719618-dotcom/local-life-ai.git
cd local-life-ai
```

### 2. 安装依赖
```bash
cd mvp-demo/registry
npm install
cd ..
```

### 3. 启动服务
```bash
chmod +x start.sh
./start.sh
```

### 4. 打开 Demo 网站
访问 http://localhost:3000

---

## 🌐 Demo 网站功能

启动后访问 http://localhost:3000 可以看到：

### 首页
- 两个 Skill 安装入口（用户端/商户端）
- 已入驻商家列表
- AI 发现接口说明

### 商家二维码页
访问 http://localhost:3000/qr
- 展示每个商家的二维码
- 用户扫码可进入定位校准

### 扫码定位页
访问 http://localhost:3000/locate?shop_id=jin_001
- 自动获取用户 GPS 位置
- 上报给平台用于精准推荐

---

## 🏪 已入驻商家

| 商家 | service_id | 类型 | 服务能力 | 健康标签 |
|------|------------|------|----------|----------|
| 金谷园饺子馆 | `jin_001` | 饺子 | 排队、预约、外卖、WiFi、菜单 | 🌿 低油脂 |
| 宏缘火锅 | `hong_001` | 火锅 | 排队、预约、外卖、WiFi、菜单 | 鸳鸯锅、包间 |
| 季多西面馆 | `ji_001` | 面馆 | 外卖、WiFi、菜单 | 现拉面 |
| 兴华家常菜 | `xin_001` | 家常菜 | 排队、预约、外卖、WiFi、菜单 | 经济实惠 |

---

## 🔌 API 接口

### 搜索商家
```bash
curl "http://localhost:3000/mcp/search?q=火锅"
```

### 查看排队
```bash
curl -X POST http://localhost:3000/mcp/jin_001/call \
  -H "Content-Type: application/json" \
  -d '{"tool":"get_queue_status","parameters":{}}'
```

### 取号
```bash
curl -X POST http://localhost:3000/mcp/jin_001/call \
  -H "Content-Type: application/json" \
  -d '{"tool":"take_queue_number","parameters":{"table_type_id":1,"people_count":2}}'
```

### 预约
```bash
curl -X POST http://localhost:3000/mcp/jin_001/call \
  -H "Content-Type: application/json" \
  -d '{"tool":"book_table","parameters":{"date":"2026-04-21","time":"19:00","people_count":2}}'
```

### 商户数据看板
```bash
curl http://localhost:3000/api/merchant/jin_001/dashboard
```

---

## 📁 目录结构

```
mvp-demo/
├── README.md                    # 本文件
│
├── skills/                      # AI Skill 目录
│   ├── user/                    # 👤 用户端 Skill
│   │   ├── user-connector/
│   │   │   ├── SKILL.md        # Skill 定义（安装时读取）
│   │   │   ├── install.sh      # 安装脚本
│   │   │   ├── llai           # CLI 工具
│   │   │   └── skill.json      # 元数据
│   │   └── README.md            # 用户端说明
│   │
│   ├── merchant/                # 🏪 商户端 Skill
│   │   ├── merchant-connector/
│   │   │   ├── SKILL.md        # Skill 定义
│   │   │   ├── install.sh      # 安装脚本
│   │   │   ├── llm            # 商户命令工具
│   │   │   └── skill.json      # 元数据
│   │   └── README.md            # 商户端说明
│   │
│   └── demo/                    # 🏬 示例商家
│       ├── jin-gu-yuan-dumpling/  # 金谷园饺子馆
│       ├── hong-yuan-hotpot/      # 宏缘火锅
│       ├── ji-dong-xi-noodles/    # 季多西面馆
│       └── xing-hua-restaurant/   # 兴华家常菜
│
├── tools/                        # 🛠️ 商家工具
│   └── restaurant-skill-builder/ # 🍜 餐饮店家 AI Skill 创建工具
│       ├── SKILL.md            # Skill 定义
│       ├── skill.json          # 元数据
│       ├── README.md           # 使用说明
│       ├── scripts/
│       │   └── init_skill.py   # 交互式初始化脚本
│       └── mcp_server_template/ # MCP 服务端模板
│
├── registry/                     # 🌐 服务注册平台
│   ├── server.js               # Express 服务器
│   ├── merchant-db.js          # 商家数据库
│   ├── skills.json             # 商家注册数据
│   ├── package.json
│   └── public/                  # Web 页面
│       ├── index.html          # 平台首页
│       ├── locate.html         # 扫码定位页
│       └── qr.html             # 商家二维码页
│
├── cli/                         # 💻 命令行工具
│   └── llai                    # 用户 CLI
│
└── start.sh                    # 启动脚本
```

---

## 🔧 部署到公网

要让其他 AI Agent 也能使用，需要将服务注册平台部署到公网：

### 方案 A：内网穿透
```bash
ngrok http 3000
```

### 方案 B：云服务器
- 部署到阿里云/腾讯云
- 修改 Skill 中的 API 地址

### 方案 C：GitHub Pages + API
- 前端部署到 GitHub Pages
- API 单独部署

---

## 📦 Skill 安装详情

### 用户端 Skill
| 项目 | 内容 |
|------|------|
| Skill ID | `@local-life-ai/user-connector` |
| 安装命令 | `skill install @local-life-ai/user-connector` |
| Raw 文件 | [SKILL.md](https://raw.githubusercontent.com/ccc414719618-dotcom/local-life-ai/main/mvp-demo/skills/user/user-connector/SKILL.md) |
| GitHub | [skills/user/](https://github.com/ccc414719618-dotcom/local-life-ai/tree/main/mvp-demo/skills/user) |

### 商户端 Skill
| 项目 | 内容 |
|------|------|
| Skill ID | `@local-life-ai/merchant-connector` |
| 安装命令 | `skill install @local-life-ai/merchant-connector` |
| Raw 文件 | [SKILL.md](https://raw.githubusercontent.com/ccc414719618-dotcom/local-life-ai/main/mvp-demo/skills/merchant/merchant-connector/SKILL.md) |
| GitHub | [skills/merchant/](https://github.com/ccc414719618-dotcom/local-life-ai/tree/main/mvp-demo/skills/merchant) |

---

## 🤝 加入我们

如果你也是 AI 开发者，欢迎：

- ⭐ **Star** 本项目
- 🐛 **提交 Bug**
- 📝 **完善文档**
- 🚀 **分享你的 Skill**

---

## 📄 License

MIT License - 随便用！

---

**GitHub**: https://github.com/ccc414719618-dotcom/local-life-ai
