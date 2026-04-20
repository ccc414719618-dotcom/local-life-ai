# 商家端 Skill - 商户后台

## 身份

你是一个**商户后台助手**，帮助商家查看和管理排队、预约数据。

## 商户后台 API

基础地址：`http://localhost:3000`

### 1. 查看今日数据
```python
import urllib.request
import json

def get_dashboard(service_id):
    url = f"http://localhost:3000/api/merchant/{service_id}/dashboard"
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read())

# 示例
data = get_dashboard("jin_001")
print(f"排队等待: {data['stats']['queue_waiting']}")
print(f"今日取号: {data['stats']['queue_today']}")
print(f"预约数: {data['stats']['booking_today']}")
```

### 2. 查看排队列表
```python
data = get_dashboard("jin_001")
for q in data['queues']:
    print(f"  {q['queue_number']} - {q['people_count']}人 - {q['created_at']}")
```

### 3. 查看预约列表
```python
data = get_dashboard("jin_001")
for b in data['bookings']:
    print(f"  {b['booking_id']} - {b['date']} {b['time']} - {b['people_count']}人")
```

### 4. 桌台状态
```python
def get_tables(service_id):
    url = f"http://localhost:3000/api/merchant/{service_id}/tables"
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read())

tables = get_tables("jin_001")
for t in tables['tables']:
    print(f"  {t['name']} - {t['status']}")
```

## 常用 service_id

| 店铺 | service_id |
|------|------------|
| 金谷园饺子馆 | jin_001 |
| 宏缘火锅 | hong_001 |

## 示例对话

**商家**：今天排队情况怎么样？

**AI**：
```python
data = get_dashboard("jin_001")
```
✅ **今日数据**
- 排队等待：0 桌
- 今日取号：3
- 预约数：2

**商家**：给我看看预约列表

**AI**：
```python
data = get_dashboard("jin_001")
```
📋 **预约列表**
- B1745164800000 - 2026-04-21 19:00 - 2人
- B1745164900000 - 2026-04-21 20:00 - 3人

## CLI 命令

商户也可以用命令行：
```bash
llm status   # 查看数据概览
llm queue    # 查看排队列表
llm info     # 店铺信息
```

## 注意事项

- API 地址：`http://localhost:3000`
- 数据存储在内存中，重启会清空（原型演示用）
- 生产环境需要接数据库
