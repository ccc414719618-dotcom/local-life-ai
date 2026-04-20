/**
 * 金谷园饺子馆 - MCP Server (Demo版)
 *
 * 运行: node server.js
 * 端口: 8001
 */

const http = require('http');

const PORT = 8001;

// 模拟数据
const db = {
  shopInfo: {
    name: '金谷园饺子馆',
    branch: '北邮店',
    address: '北京市海淀区杏坛路文教产业园K座南2层',
    phone: '010-62301234',
    hours: '10:00-22:00',
    wifi: { ssid: 'JinGuYuan_WiFi', password: '88888888' }
  },
  queue: {
    current_wait: 3,
    tables: [
      { id: 1, name: '小桌(2人)', available: true, current_wait: 0 },
      { id: 2, name: '中桌(4人)', available: true, current_wait: 2 },
      { id: 3, name: '大桌(6人)', available: false, current_wait: 5 }
    ]
  },
  menu: {
    categories: ['招牌饺子', '猪肉类', '牛羊肉类', '海鲜类', '凉菜', '饮品'],
    items: [
      { id: 101, name: '猪肉大葱饺子（招牌）', price: 18, category: '招牌饺子', unit: '份(20个)' },
      { id: 102, name: '牛肉萝卜饺子', price: 22, category: '牛羊肉类', unit: '份(20个)' },
      { id: 103, name: '虾仁三鲜饺子', price: 28, category: '海鲜类', unit: '份(20个)' },
      { id: 104, name: '羊肉香菜饺子', price: 24, category: '牛羊肉类', unit: '份(20个)' },
      { id: 201, name: '凉拌黄瓜', price: 12, category: '凉菜' },
      { id: 202, name: '老醋花生', price: 10, category: '凉菜' },
      { id: 301, name: '可乐', price: 5, category: '饮品' },
      { id: 302, name: '雪碧', price: 5, category: '饮品' }
    ]
  },
  delivery: {
    available: true,
    min_order: 20,
    delivery_fee: 5,
    range: '3公里内',
    estimated_time: '30-45分钟'
  },
  news: [
    { type: 'promotion', content: '会员日周三饺子8折' },
    { type: 'notice', content: '新到春季野菜饺子，限时尝鲜' }
  ]
};

// 工具实现
const tools = {
  get_shop_info: () => db.shopInfo,

  get_queue_status: (params) => {
    const { table_type_id } = params || {};
    if (table_type_id) {
      const table = db.queue.tables.find(t => t.id === table_type_id);
      return {
        table,
        total_waiting: db.queue.current_wait
      };
    }
    return {
      tables: db.queue.tables,
      total_waiting: db.queue.current_wait
    };
  },

  take_queue_number: (params) => {
    const { table_type_id, people_count } = params;
    const table = db.queue.tables.find(t => t.id === table_type_id);
    if (!table) {
      return { success: false, error: '桌型不存在' };
    }
    if (!table.available) {
      return { success: false, error: '该桌型暂无空位' };
    }
    const queueNum = `J${String(Math.floor(Math.random() * 100) + 1).padStart(2, '0')}`;
    const estimatedWait = table.current_wait * 10 + Math.floor(Math.random() * 10);
    return {
      success: true,
      queue_number: queueNum,
      table_type: table.name,
      people_count,
      estimated_wait_minutes: estimatedWait,
      message: `取号成功，请留意叫号`
    };
  },

  cancel_queue: (params) => {
    const { queue_number } = params;
    return {
      success: true,
      message: `排队号 ${queue_number} 已取消`
    };
  },

  get_menu: (params) => {
    const { category } = params || {};
    let items = db.menu.items;
    if (category) {
      items = items.filter(item => item.category === category);
    }
    return {
      categories: db.menu.categories,
      items
    };
  },

  get_delivery_info: () => db.delivery,

  get_wifi_info: () => ({
    ssid: db.shopInfo.wifi.ssid,
    password: db.shopInfo.wifi.password
  }),

  get_latest_news: () => db.news
};

// MCP 协议处理
function handleMCPRequest(body) {
  const { method, params = {}, id } = body;

  if (method === 'tools/list') {
    return {
      jsonrpc: '2.0',
      id,
      result: {
        tools: [
          { name: 'get_shop_info', description: '获取店铺信息' },
          { name: 'get_queue_status', description: '获取排队状态' },
          { name: 'take_queue_number', description: '取号排队' },
          { name: 'cancel_queue', description: '取消排队' },
          { name: 'get_menu', description: '获取菜单' },
          { name: 'get_delivery_info', description: '获取外卖信息' },
          { name: 'get_wifi_info', description: '获取Wi-Fi信息' },
          { name: 'get_latest_news', description: '获取最新活动' }
        ]
      }
    };
  }

  if (method === 'tools/call') {
    const { name, arguments: args } = params;
    const tool = tools[name];
    if (!tool) {
      return {
        jsonrpc: '2.0',
        id,
        error: { code: -32601, message: `Tool ${name} not found` }
      };
    }
    try {
      const result = tool(args || {});
      return {
        jsonrpc: '2.0',
        id,
        result: { content: [{ type: 'text', text: JSON.stringify(result) }] }
      };
    } catch (e) {
      return {
        jsonrpc: '2.0',
        id,
        error: { code: -32603, message: e.message }
      };
    }
  }

  return {
    jsonrpc: '2.0',
    id,
    error: { code: -32601, message: 'Method not found' }
  };
}

// HTTP Server
const server = http.createServer((req, res) => {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Content-Type', 'application/json');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  let body = '';
  req.on('data', chunk => body += chunk);
  req.on('end', () => {
    try {
      const request = JSON.parse(body);
      const response = handleMCPRequest(request);
      res.writeHead(200);
      res.end(JSON.stringify(response));
    } catch (e) {
      res.writeHead(400);
      res.end(JSON.stringify({ error: 'Invalid JSON' }));
    }
  });
});

server.listen(PORT, () => {
  console.log(`🍜 金谷园饺子馆 MCP Server 已启动`);
  console.log(`   端点: http://localhost:${PORT}`);
  console.log(`   工具: ${Object.keys(tools).join(', ')}`);
});
