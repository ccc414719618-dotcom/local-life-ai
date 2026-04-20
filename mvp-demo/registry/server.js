const express = require('express');
const fs = require('fs');
const path = require('path');
const merchantDB = require('./merchant-db');

const app = express();
const PORT = 3000;
const SKILLS_FILE = path.join(__dirname, 'skills.json');

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, 'public')));

// Serve skills for download
app.use('/skills', express.static(path.join(__dirname, '..', 'skills')));

// In-memory store (for demo - in production, data would be in AI agents)
const merchantStores = new Map();

// Merchant registration API
app.post('/api/merchant/register', (req, res) => {
  const { shop_id, shop_name, categories, location, contact, capabilities, health_tags } = req.body;
  
  if (!shop_id || !shop_name) {
    return res.status(400).json({ status: 'error', message: 'Missing required fields' });
  }
  
  const skill = {
    skill_id: shop_id,
    skill_name: shop_name,
    categories: categories || ['餐饮'],
    location: location || {},
    contact: contact || {},
    capabilities: capabilities || ['info'],
    health_tags: health_tags || {},
    version: '1.0.0',
    updated_at: new Date().toISOString().split('T')[0]
  };
  
  // Add to skills
  const skills = getSkills();
  const existingIndex = skills.skills.findIndex(s => s.skill_id === shop_id);
  if (existingIndex >= 0) {
    skills.skills[existingIndex] = skill;
  } else {
    skills.skills.push(skill);
  }
  fs.writeFileSync(SKILLS_FILE, JSON.stringify(skills, null, 2));
  
  res.json({ 
    status: 'success', 
    message: 'Merchant registered successfully',
    skill_id: shop_id,
    endpoint: `/mcp/${shop_id}`
  });
});

// Load skills data
function getSkills() {
  const data = fs.readFileSync(SKILLS_FILE, 'utf8');
  return JSON.parse(data);
}

// CORS headers for MCP protocol
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization');
  res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  if (req.method === 'OPTIONS') {
    return res.sendStatus(200);
  }
  next();
});

// ============= MCP Manifest Endpoints (AI-First) =============

// Global MCP Manifest - AI Agent discover endpoint
app.get('/mcp-manifest.json', (req, res) => {
  const skills = getSkills();
  
  const manifest = {
    schema_version: "1.0",
    platform: "LLAIP",
    platform_name: "本地生活 AI 平台",
    description: "让 AI 发现附近的每一个好店",
    endpoints: {
      discover: "/mcp-manifest.json",
      search: "/mcp/search",
      call: "/mcp/{service_id}/call"
    },
    services: skills.skills.map(s => ({
      id: s.skill_id,
      name: s.skill_name,
      categories: s.categories,
      location: s.location,
      endpoint: `/mcp/${s.skill_id}`,
      capabilities: s.capabilities,
      health_tags: s.health_tags ? {
        dietary_options: s.health_tags.dietary_options || [],
        health_labels: s.health_tags.health_labels || [],
        allergens: s.health_tags.allergens || []
      } : null,
      version: s.version,
      updated_at: s.updated_at
    }))
  };
  
  res.json(manifest);
});

// Single service MCP Manifest
app.get('/mcp/:serviceId/manifest.json', (req, res) => {
  const skills = getSkills();
  const skill = skills.skills.find(s => s.skill_id === req.params.serviceId);

  if (!skill) {
    return res.status(404).json({
      error: 'Service not found',
      message: `Service '${req.params.serviceId}' not found in registry`
    });
  }

  // Generate tools based on capabilities
  const tools = [];
  
  if (skill.capabilities.includes('info')) {
    tools.push({
      name: 'get_shop_info',
      description: '获取店铺基本信息（地址、营业时间、联系方式）',
      parameters: {}
    });
  }
  
  if (skill.capabilities.includes('queue')) {
    tools.push({
      name: 'get_queue_status',
      description: '获取当前排队状态',
      parameters: {
        table_type_id: { type: 'integer', required: false, description: '桌型ID（1=小桌, 2=中桌, 3=大桌）' }
      }
    });
    tools.push({
      name: 'take_queue_number',
      description: '取号排队',
      parameters: {
        table_type_id: { type: 'integer', required: true, description: '桌型ID' },
        people_count: { type: 'integer', required: true, description: '就餐人数' }
      }
    });
    tools.push({
      name: 'cancel_queue',
      description: '取消排队',
      parameters: {
        queue_number: { type: 'string', required: true, description: '排队号' }
      }
    });
  }
  
  if (skill.capabilities.includes('menu')) {
    tools.push({
      name: 'get_menu',
      description: '获取菜单',
      parameters: {
        category: { type: 'string', required: false, description: '菜品分类' }
      }
    });
  }
  
  if (skill.capabilities.includes('delivery')) {
    tools.push({
      name: 'get_delivery_info',
      description: '获取外卖配送信息',
      parameters: {}
    });
  }
  
  if (skill.capabilities.includes('wifi')) {
    tools.push({
      name: 'get_wifi_info',
      description: '获取Wi-Fi信息',
      parameters: {}
    });
  }
  
  if (skill.capabilities.includes('reservation')) {
    tools.push({
      name: 'book_table',
      description: '预订座位',
      parameters: {
        date: { type: 'string', required: true, description: '日期（YYYY-MM-DD）' },
        time: { type: 'string', required: true, description: '时间（HH:MM）' },
        people_count: { type: 'integer', required: true, description: '人数' }
      }
    });
  }

  // AI settings
  const aiSettings = skill.health_tags?.ai_settings || {
    welcome_message: `您好，欢迎光临${skill.skill_name}！有什么可以帮您的？`,
    queue_response: '目前排队情况：{wait_count}桌，预计等待{wait_minutes}分钟。'
  };

  const manifest = {
    service_id: skill.skill_id,
    service_name: skill.skill_name,
    description: `${skill.categories.join(', ')} - ${skill.location.address}`,
    endpoint: `/mcp/${skill.skill_id}`,
    location: skill.location,
    contact: skill.contact,
    capabilities: skill.capabilities,
    health_tags: skill.health_tags ? {
      dietary_options: skill.health_tags.dietary_options || [],
      health_labels: skill.health_tags.health_labels || [],
      allergens: skill.health_tags.allergens || []
    } : null,
    ai_settings: aiSettings,
    tools: tools
  };
  
  res.json(manifest);
});

// MCP Search endpoint
app.get('/mcp/search', (req, res) => {
  const skills = getSkills();
  const { q, category, capability, health_filter, user_health } = req.query;

  let results = skills.skills;

  // Text search
  if (q) {
    results = results.filter(s =>
      s.skill_name.includes(q) ||
      s.categories.some(c => c.includes(q)) ||
      s.location.address.includes(q)
    );
  }

  // Category filter
  if (category) {
    results = results.filter(s =>
      s.categories.some(c => c.includes(category))
    );
  }

  // Capability filter
  if (capability) {
    results = results.filter(s =>
      s.capabilities.includes(capability)
    );
  }

  // Health filter
  if (health_filter === 'true' && user_health) {
    try {
      const userHealth = JSON.parse(decodeURIComponent(user_health));
      results = results.filter(s => {
        if (!s.health_tags) return true;
        
        const { allergens = [], diet_goal = [] } = userHealth;
        const skillAllergens = s.health_tags.allergens || [];
        
        // Check allergen conflicts
        const hasConflict = allergens.some(a => skillAllergens.includes(a));
        if (hasConflict) return false;
        
        return true;
      });
    } catch (e) {
      // Ignore parse errors
    }
  }

  // Format for AI consumption
  const aiResults = results.map(s => ({
    id: s.skill_id,
    name: s.skill_name,
    categories: s.categories,
    location: s.location,
    distance: s.location ? `${(Math.random() * 2).toFixed(1)}km` : null,
    capabilities: s.capabilities,
    health_tags: s.health_tags ? {
      labels: s.health_tags.health_labels || [],
      allergens: s.health_tags.allergens || []
    } : null,
    endpoint: `/mcp/${s.skill_id}`
  }));

  res.json({
    total: aiResults.length,
    results: aiResults
  });
});

// MCP Call endpoint
app.post('/mcp/:serviceId/call', (req, res) => {
  const { serviceId } = req.params;
  const { tool, parameters = {} } = req.body;

  // Tool handlers
  const toolHandlers = {
    get_shop_info: () => ({
      name: '示例店铺',
      address: '北京市海淀区xx路xx号',
      hours: '09:00-22:00',
      phone: '010-xxxxxxxx'
    }),
    get_queue_status: () => {
      const status = merchantDB.getQueueStatus(serviceId);
      return {
        ...status,
        available_tables: [1, 2, 3].map(id => ({
          table_type_id: id,
          name: ['小桌(2人)', '中桌(4人)', '大桌(6人)'][id-1],
          available: true
        }))
      };
    },
    take_queue_number: () => merchantDB.takeQueue(serviceId, parameters.table_type_id, parameters.people_count),
    cancel_queue: () => merchantDB.cancelQueue(parameters.queue_number),
    get_menu: () => ({
      categories: ['招牌菜', '主食', '饮品'],
      items: [
        { id: 1, name: '招牌饺子', price: 28, category: '招牌菜' },
        { id: 2, name: '牛肉面', price: 32, category: '主食' },
        { id: 3, name: '可乐', price: 8, category: '饮品' }
      ]
    }),
    get_delivery_info: () => ({
      available: true,
      min_order: 20,
      delivery_fee: 5,
      estimated_time: '30-45分钟'
    }),
    get_wifi_info: () => ({
      ssid: 'Shop_WiFi',
      password: '88888888'
    }),
    book_table: () => merchantDB.bookTable(serviceId, parameters.date, parameters.time, parameters.people_count)
  };

  const handler = toolHandlers[tool];
  if (!handler) {
    return res.status(404).json({
      error: 'Tool not found',
      message: `Tool '${tool}' not available for this service`
    });
  }

  res.json({
    service_id: serviceId,
    tool: tool,
    result: handler()
  });
});

// ============= Merchant Dashboard API =============

// 商家后台数据
app.get('/api/merchant/:serviceId/dashboard', (req, res) => {
  const { serviceId } = req.params;
  res.json({
    stats: merchantDB.getStats(serviceId),
    queues: merchantDB.getQueueList(serviceId),
    bookings: merchantDB.getBookingList(serviceId)
  });
});

// 商家桌台状态
app.get('/api/merchant/:serviceId/tables', (req, res) => {
  const { serviceId } = req.params;
  res.json({
    tables: [
      { id: 1, name: '小桌(2人)', capacity: 2, status: 'available' },
      { id: 2, name: '中桌(4人)', capacity: 4, status: 'available' },
      { id: 3, name: '大桌(6人)', capacity: 6, status: 'occupied' }
    ]
  });
});

// ============= Location APIs =============

// 用户位置上报
app.post('/api/location/report', (req, res) => {
  const { shop_id, lat, lng, source } = req.body;
  
  // 保存用户位置（内存存储）
  if (!merchantStores.has('user_locations')) {
    merchantStores.set('user_locations', new Map());
  }
  
  const userLocations = merchantStores.get('user_locations');
  const userId = req.ip || 'anonymous';
  userLocations.set(userId, {
    lat, lng, shop_id, source,
    updated_at: new Date().toISOString()
  });
  
  res.json({ status: 'ok', message: '位置已更新' });
});

// 获取用户位置
app.get('/api/location/user', (req, res) => {
  const userId = req.ip || 'anonymous';
  const userLocations = merchantStores.get('user_locations') || new Map();
  const location = userLocations.get(userId);
  
  if (location) {
    res.json(location);
  } else {
    res.json({ lat: null, lng: null });
  }
});

// 定位页面
app.get('/locate', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'locate.html'));
});

// 商家二维码页面
app.get('/qr', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'qr.html'));
});

// 店铺列表 API
app.get('/api/shops', (req, res) => {
  const skills = getSkills();
  res.json({
    shops: skills.skills.map(s => ({
      id: s.skill_id,
      name: s.skill_name,
      address: s.location?.address || ''
    }))
  });
});

// ============= Human-Readable Web Pages =============

// Serve HTML page
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Location calibration page
app.get('/calibrate', (req, res) => {
  const { id } = req.query;
  const skills = getSkills();
  const shop = skills.skills.find(s => s.skill_id === id);
  
  const html = `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>位置校准 - ${shop?.skill_name || '商家'}</title>
  <style>
    body { font-family: -apple-system, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
    .card { background: #f5f5f5; border-radius: 12px; padding: 24px; margin-bottom: 20px; }
    h1 { font-size: 20px; margin-bottom: 16px; }
    .shop-name { font-size: 18px; font-weight: bold; margin-bottom: 8px; }
    .current { color: #666; font-size: 14px; margin-bottom: 20px; }
    .form-group { margin-bottom: 16px; }
    label { display: block; margin-bottom: 6px; font-weight: 500; }
    input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; }
    button { width: 100%; padding: 12px; background: #007AFF; color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; }
    button:hover { background: #0056b3; }
    .note { font-size: 12px; color: #888; margin-top: 8px; }
  </style>
</head>
<body>
  <h1>📍 位置校准</h1>
  <div class="card">
    <div class="shop-name">${shop?.skill_name || '未知店铺'}</div>
    <div class="current">
      当前IP定位：${shop?.location?.address || '未知'}
    </div>
    
    <form action="/api/merchant/update-location" method="POST">
      <input type="hidden" name="shop_id" value="${id}">
      
      <div class="form-group">
        <label>经度</label>
        <input type="text" name="lat" placeholder="如：39.9633" value="${shop?.location?.lat || ''}">
      </div>
      
      <div class="form-group">
        <label>纬度</label>
        <input type="text" name="lon" placeholder="如：116.308" value="${shop?.location?.lon || ''}">
      </div>
      
      <div class="form-group">
        <label>精确地址</label>
        <input type="text" name="address" placeholder="如：北京市海淀区xx路xx号" value="${shop?.location?.address || ''}">
      </div>
      
      <button type="submit">保存位置</button>
      <p class="note">提示：可以使用高德地图或百度地图获取精确坐标</p>
    </form>
  </div>
</body>
</html>`;
  
  res.type('html').send(html);
});

// Update merchant location
app.post('/api/merchant/update-location', (req, res) => {
  const { shop_id, lat, lon, address } = req.body;
  
  const skills = getSkills();
  const index = skills.skills.findIndex(s => s.skill_id === shop_id);
  
  if (index >= 0) {
    skills.skills[index].location.lat = parseFloat(lat);
    skills.skills[index].location.lon = parseFloat(lon);
    skills.skills[index].location.address = address;
    fs.writeFileSync(SKILLS_FILE, JSON.stringify(skills, null, 2));
    res.send('<script>alert("位置已更新！"); window.close();</script>');
  } else {
    res.status(404).send('店铺未找到');
  }
});

app.listen(PORT, () => {
  console.log('========================================');
  console.log('  本地生活 AI 平台 (LLAIP) - AI-First Demo');
  console.log('========================================');
  console.log(`  Web UI:        http://localhost:${PORT}`);
  console.log(`  MCP Manifest:   http://localhost:${PORT}/mcp-manifest.json`);
  console.log(`  MCP Search:     http://localhost:${PORT}/mcp/search`);
  console.log(`  MCP Call:       POST http://localhost:${PORT}/mcp/{service_id}/call`);
  console.log('========================================');
  console.log('');
  console.log('  AI-First Design:');
  console.log('  - MCP Manifest is the primary interface');
  console.log('  - HTML is for human reference only');
  console.log('  - All data stored in AI agents, not platform');
  console.log('========================================');
});
