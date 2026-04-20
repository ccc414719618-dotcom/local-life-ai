# 本地生活 AI 平台 - MVP Demo

> 让 AI Agent 通过自然语言调用本地商家服务

---

## 🎯 两个版本

### 1. 用户端 - @local-life-ai/user-connector
帮助用户发现附近好店、排队、预约。

**安装**：
```bash
skill install @local-life-ai/user-connector
```

**功能**：
- 🔍 搜索附近商家（按关键词/分类/位置）
- 📋 查看实时排队情况
- 🎫 线上取号
- 📅 预约座位

---

### 2. 商户端 - @local-life-ai/merchant-connector
帮助商家 7x24 小时自动接待客户。

**安装**：
```bash
skill install @local-life-ai/merchant-connector
```

**功能**：
- 📊 数据看板（排队/预约/翻台率）
- 📋 排队列表管理
- 📅 预约列表管理
- 🔧 位置校准

---

## 🚀 快速启动

```bash
cd mvp-demo

# 安装依赖
cd registry && npm install && cd ..

# 启动服务注册平台
chmod +x start.sh
./start.sh
```

**访问地址**：
| 服务 | 地址 |
|------|------|
| 平台首页 | http://localhost:3000 |
| 商家二维码 | http://localhost:3000/qr |
| API | http://localhost:3000/api/skills |
| MCP Manifest | http://localhost:3000/mcp-manifest.json |

---

## 📁 目录结构

```
mvp-demo/
├── README.md                    # 本文件
├── skills/                      # AI Skill 目录
│   ├── user/                    # 用户端 Skill
│   │   ├── user-connector/      # 用户连接器
│   │   │   ├── SKILL.md        # Skill 定义
│   │   │   ├── install.sh      # 安装脚本
│   │   │   └── skill.json       # 元数据
│   │   └── README.md            # 用户端说明
│   │
│   ├── merchant/                # 商户端 Skill
│   │   ├── merchant-connector/  # 商户连接器
│   │   │   ├── SKILL.md        # Skill 定义
│   │   │   ├── install.sh      # 安装脚本
│   │   │   ├── llm             # 商户命令工具
│   │   │   └── skill.json       # 元数据
│   │   └── README.md            # 商户端说明
│   │
│   └── demo/                    # 示例商家 Skill
│       ├── jin-gu-yuan-dumpling/  # 金谷园饺子馆
│       ├── hong-yuan-hotpot/      # 宏缘火锅
│       ├── ji-dong-xi-noodles/    # 季多西面馆
│       └── xing-hua-restaurant/   # 兴华家常菜
│
├── registry/                     # 服务注册平台
│   ├── server.js               # Express 服务器
│   ├── merchant-db.js          # 商家数据库
│   ├── skills.json             # 商家注册数据
│   ├── package.json
│   └── public/                  # Web 页面
│       ├── index.html          # 平台首页
│       ├── locate.html         # 扫码定位页
│       └── qr.html             # 商家二维码页
│
├── cli/                         # 命令行工具
│   └── llai                    # 用户 CLI
│
└── start.sh                    # 启动脚本
```

---

## 🔌 API 示例

```bash
# 获取所有商家
curl http://localhost:3000/api/skills

# 搜索商家（中文）
curl "http://localhost:3000/mcp/search?q=火锅"

# 查看排队状态
curl -X POST http://localhost:3000/mcp/jin_001/call \
  -H "Content-Type: application/json" \
  -d '{"tool":"get_queue_status","parameters":{}}'

# 商家取号
curl -X POST http://localhost:3000/mcp/jin_001/call \
  -H "Content-Type: application/json" \
  -d '{"tool":"take_queue_number","parameters":{"table_type_id":1,"people_count":2}}'

# 商家预约
curl -X POST http://localhost:3000/mcp/jin_001/call \
  -H "Content-Type: application/json" \
  -d '{"tool":"book_table","parameters":{"date":"2026-04-21","time":"19:00","people_count":2}}'

# 商家数据看板
curl http://localhost:3000/api/merchant/jin_001/dashboard
```

---

## 📋 商家列表

| 商家 | service_id | 类型 | 服务 |
|------|------------|------|------|
| 金谷园饺子馆 | jin_001 | 饺子 | 排队、预约、外卖、Wi-Fi、菜单 |
| 宏缘火锅 | hong_001 | 火锅 | 排队、预约、外卖、Wi-Fi、菜单 |
| 季多西面馆 | ji_001 | 面馆 | 外卖、Wi-Fi、菜单 |
| 兴华家常菜 | xin_001 | 家常菜 | 排队、预约、外卖、Wi-Fi、菜单 |

---

## 🔧 配置

服务注册平台地址（默认）：
```
http://localhost:3000
```

如需修改，编辑 `skills/user/user-connector/SKILL.md` 和 `skills/merchant/merchant-connector/SKILL.md` 中的 `BASE` 变量。

---

## 📦 部署到公网

要让其他 AI Agent 也能使用，需要将服务注册平台部署到公网：

1. **方案 A：内网穿透**
   ```bash
   # 使用 ngrok
   ngrok http 3000
   ```

2. **方案 B：云服务器**
   - 部署到阿里云/腾讯云
   - 修改 Skill 中的 API 地址

3. **方案 C：GitHub Pages + API**
   - 前端部署到 GitHub Pages
   - API 单独部署

---

## 📄 License

MIT
