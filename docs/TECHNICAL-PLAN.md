# 本地生活 AI Skill 平台 - 技术方案

> 版本：v0.1 | 日期：2026-04-19 | 作者：基于与用户讨论整理

---

## 1. 核心架构原则

### 1.1 数据主权原则
- **平台只做黄页**：只存元数据（店名、地址、MCP端点）
- **商家控制数据**：MCP Server 部署在商家电脑/服务器
- **用户控制偏好**：AI Agent 本地存储用户数据

### 1.2 部署原则
- **去中心化**：平台不存核心数据
- **最小化基础设施**：商家可零成本部署
- **MCP 协议**：标准化的 Agent-Skill 通信协议

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户侧 (User)                        │
│                                                             │
│   ┌─────────────────────┐     ┌─────────────────────────┐   │
│   │   AI Agent (本地)   │     │   用户设备 (手机/电脑)  │   │
│   │                     │     │                          │   │
│   │  - 本地偏好存储      │     │  - 自然语言交互入口      │   │
│   │  - 读取 Skill Registry │     │  - 查看服务结果        │   │
│   │  - 调用 MCP Server   │     │  - 授权管理            │   │
│   └─────────────────────┘     └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ MCP 协议调用
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      平台侧 (Platform)                    │
│                                                             │
│   ┌─────────────────────┐     ┌─────────────────────────┐ │
│   │   Skill Registry    │     │    Merchant Portal     │ │
│   │   (技能注册表)       │     │    (商家后台)          │ │
│   │                     │     │                        │ │
│   │  - skill_name      │     │  - AI 引导创建流程     │ │
│   │  - categories       │     │  - 数据迁移工具        │ │
│   │  - location         │     │  - 一键部署脚本        │ │
│   │  - mcp_endpoint     │     │  - 商家管理后台        │ │
│   │  - version          │     │                        │ │
│   └─────────────────────┘     └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ MCP 协议调用
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     商家侧 (Merchant)                      │
│                                                             │
│   ┌─────────────────────┐     ┌─────────────────────────┐ │
│   │   Merchant Server    │     │   本地设备              │ │
│   │   (商家服务器)        │     │   (电脑/手机/树莓派)   │ │
│   │                     │     │                        │ │
│   │  - MCP Server       │     │  - 部署 Skill         │ │
│   │  - tools.py         │     │  - 商家日常运营        │ │
│   │  - SQLite DB        │     │                        │ │
│   │  - 图片/视频存储      │     │                        │ │
│   └─────────────────────┘     └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 技术组件

### 3.1 Skill Registry (注册表)

```json
{
  "skills": [
    {
      "skill_id": "jingu_001",
      "skill_name": "金谷园饺子馆",
      "merchant_id": "merchant_001",
      "categories": ["餐饮", "饺子", "排队"],
      "location": {
        "lat": 39.95,
        "lng": 116.31,
        "address": "杏坛路文教产业园K座南2层"
      },
      "mcp_endpoint": "http://merchant.local:8000",
      "mcp_endpoint_public": "https://mcp-proxy.platform.com/merchant_001",
      "version": "0.4.2",
      "auth_required": false,
      "capabilities": ["queue", "delivery", "wifi", "info"],
      "created_at": "2026-04-01",
      "updated_at": "2026-04-19"
    }
  ]
}
```

**存储方式**：
- 轻量级数据库（SQLite / PostgreSQL）
- 纯元数据，不含任何业务数据
- 类似 DNS 的查找表

### 3.2 MCP Server (商家侧)

```
merchant-server/
├── SKILL.md              # 商家 Skill 指令
├── skill.json            # MCP 工具定义
├── server.py             # FastAPI MCP 入口
├── tools.py              # 工具实现（商家修改这里）
├── database.py           # 数据库操作
├── requirements.txt      # 依赖
└── Dockerfile            # 一键部署
```

**MCP 工具模板**：

| 工具名 | 功能 | 返回数据 |
|--------|------|---------|
| `get_shop_info` | 店铺基本信息 | 名称、地址、营业时间 |
| `get_queue_status` | 排队状态 | 当前等待人数、可选桌型 |
| `take_queue_number` | 取号 | 排队号、预计等待时间 |
| `get_delivery_info` | 外卖信息 | 配送范围、平台 |
| `get_wifi_info` | Wi-Fi | 名称、密码 |
| `get_latest_news` | 最新活动 | 公告、优惠 |

### 3.3 Merchant Portal (商家后台)

**功能模块**：

| 模块 | 功能 |
|------|------|
| **AI 引导创建** | 商家描述业务 → AI 生成完整 Skill |
| **数据迁移** | 美团 OAuth → 读取数据 → 导入 |
| **一键部署** | 生成部署脚本 → 推送到商家设备 |
| **店铺管理** | 修改营业时间、套餐、活动 |
| **数据看板** | 访问统计、服务调用次数 |

### 3.4 AI 引导创建流程

```
商家输入：
「我是一家饺子馆，在北邮旁边，营业到晚上10点」

AI 处理：
1. 提取实体：店铺类型、位置、营业时间
2. 生成 SKILL.md（店铺介绍、触发场景）
3. 生成 skill.json（MCP 工具定义）
4. 生成 tools.py（工具实现框架）
5. 生成 server.py（FastAPI 服务）
6. 生成部署脚本

商家确认：
- 检查生成的信息
- 点击「确认发布」
- 选择部署方式（电脑/云服务器）
- 一键部署
```

---

## 4. 部署方案

### 4.1 商家本地部署（推荐）

**最低要求**：
- 一台常开的电脑（Windows / Mac / Linux）
- 4GB 内存
- 稳定的网络

**部署步骤**：
```bash
# 1. 下载商家端程序
# 2. 运行安装向导
# 3. 配置店铺信息
# 4. 启动服务
# 5. 自动生成 Skill 并注册到平台
```

**网络穿透方案**：

| 方案 | 适用场景 | 复杂度 |
|------|---------|--------|
| **Tailscale (推荐)** | 有电脑基础的商家 | ⭐ 极简 |
| **ngrok** | 临时测试 | ⭐ 简单 |
| **frp** | 有服务器的商家 | ⭐⭐ 中等 |
| **平台中转** | 所有商家 | ⭐⭐⭐ 需要开发 |

**Tailscale 方案**：
```bash
# 商家电脑安装 Tailscale
# 获取虚拟 IP（如 100.64.x.x）
# 商家 AI Agent 通过这个 IP 访问 MCP Server
```

### 4.2 云服务器部署（可选）

适合有技术能力的商家：
- 腾讯云函数 SCF
- 阿里云函数计算
- AWS Lambda

### 4.3 容器化部署

```dockerfile
FROM python:3.11-slim
COPY . /app
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
```

商家只需：
```bash
docker run -p 8000:8000 merchant-skill
```

---

## 5. 数据流设计

### 5.1 用户查询流程

```
用户： "金谷园现在排队情况怎么样？"

AI Agent：
1. 读取 Skill Registry
2. 发现「金谷园饺子馆」Skill
3. 通过 MCP 协议调用商家 MCP Server
4. 获取实时排队数据
5. 返回给用户

全程：
- 平台只做发现，不存数据
- 数据在商家 MCP Server
- 用户 AI Agent 本地处理
```

### 5.2 排队取号流程

```
用户： "帮我在金谷园排个2人桌"

AI Agent：
1. 读取 Skill Registry
2. 发现金谷园有 queue 能力
3. 调用 MCP tools/call → take_queue_number
4. 商家 MCP Server 处理请求
5. 返回排队号和预计等待时间
6. 用户 AI Agent 展示给用户

（涉及美团 API，需要用户授权 Token）
```

---

## 6. 安全设计

### 6.1 认证授权

| 场景 | 方案 |
|------|------|
| AI Agent 发现 Skill | 公开，无需认证 |
| 调用只读工具（查询） | 公开 |
| 调用写操作（取号） | 用户 Token 验证 |
| 商家管理后台 | OAuth 2.0 |
| 平台管理后台 | 管理员账号 |

### 6.2 数据隔离

- 每个商家的 MCP Server 独立运行
- 数据库按 merchant_id 隔离
- API 请求需要带 merchant_id 校验

---

## 7. MCP 协议集成

### 7.1 协议栈

```
┌─────────────────────────────────────────┐
│           AI Agent (用户侧)              │
│                                         │
│   - 本地存储用户偏好                      │
│   - 读取 Skill Registry                 │
│   - 发起 MCP 调用                       │
└─────────────────────────────────────────┘
                    │
                    │ HTTP / Streamable
                    ▼
┌─────────────────────────────────────────┐
│         MCP Server (商家侧)              │
│                                         │
│   - FastAPI 实现                         │
│   - 返回商家数据                        │
│   - 商家的 Token 验证                   │
└─────────────────────────────────────────┘
```

### 7.2 MCP 工具定义示例

```json
{
  "name": "take_queue_number",
  "description": "在金谷园饺子馆取号排队",
  "inputSchema": {
    "type": "object",
    "properties": {
      "table_type_id": {
        "type": "integer",
        "description": "桌型编号（1=小桌，2=四人桌）"
      },
      "people_count": {
        "type": "integer",
        "description": "就餐人数"
      }
    },
    "required": ["table_type_id", "people_count"]
  }
}
```

---

## 8. 基础设施规划

### MVP 阶段（2-4周）

| 组件 | 选型 | 成本 |
|------|------|------|
| Skill Registry | SQLite | $0 |
| Merchant Portal | Next.js + Vercel | $0-20 |
| MCP 代理 | 简单 Node.js | $0-10 |
| 监控 | 日志 + 告警 | $0 |

### v1.0 阶段（1-2月）

| 组件 | 选型 | 成本 |
|------|------|------|
| Skill Registry | PostgreSQL | $20/月 |
| Merchant Portal | Next.js + Vercel | $20/月 |
| MCP 代理集群 | 2x 4C8G 云服务器 | $50/月 |
| CDN | 阿里云 | $10/月 |
| 监控 | Datadog | $30/月 |

---

## 9. 技术栈总结

| 层级 | 技术选型 |
|------|---------|
| **前端** | Next.js / React |
| **后端** | FastAPI (Python) |
| **数据库** | PostgreSQL + SQLite |
| **部署** | Docker + 云服务器 / 商家本地 |
| **协议** | MCP (Model Context Protocol) |
| **网络穿透** | Tailscale / ngrok |
| **认证** | OAuth 2.0 + JWT |
| **搜索** | Elasticsearch (可选) |

---

## 10. 开发里程碑

| 阶段 | 周数 | 交付物 |
|------|------|---------|
| **MVP** | 1-2周 | 本地生活 Skill 生成器（餐饮版） |
| **MCP 集成** | 第2周 | MCP Server 模板 + 注册表 |
| **商家后台** | 第3周 | AI 引导创建 + 部署脚本 |
| **用户发现** | 第4周 | Skill 市场 + AI Agent 集成 |
| **内测** | 第4周 | 3-5家商家真实测试 |

---

## 11. 参考实现

- **Skill 生成器**：restaurant-skill-builder（已验证）
- **MCP Server**：金谷园饺子馆 Skill（已部署）
- **排队系统**：meituan-queue（已集成）
- **AI 引导**：LLM 自然语言生成（GPT-4 / Claude）
