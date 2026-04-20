/**
 * 宏缘火锅 - MCP Server (Demo版)
 */

const http = require('http');

const PORT = 8002;

const db = {
  shopInfo: {
    name: '宏缘火锅',
    branch: '学院路店',
    address: '北京市海淀区学院路甲38号',
    phone: '010-82345678',
    hours: '11:00-23:00',
    wifi: { ssid: 'HongYuHotpot_5G', password: '12345678' }
  },
  queue: {
    current_wait: 8,
    tables: [
      { id: 1, name: '小桌(2-3人)', available: true, current_wait: 1 },
      { id: 2, name: '中桌(4-6人)', available: true, current_wait: 3 },
      { id: 3, name: '大桌(8-10人)', available: false, current_wait: 6 }
    ]
  },
  menu: {
    categories: ['锅底', '招牌涮品', '肉类', '海鲜', '蔬菜', '主食'],
    items: [
      { id: 1, name: '麻辣牛油锅底', price: 38, category: '锅底', unit: '份' },
      { id: 2, name: '菌汤养生锅底', price: 32, category: '锅底', unit: '份' },
      { id: 3, name: '鲜毛肚', price: 48, category: '招牌涮品', unit: '份' },
      { id: 4, name: '鲜鹅肠', price: 38, category: '招牌涮品', unit: '份' },
      { id: 5, name: '手切牛肉', price: 58, category: '肉类', unit: '份' },
      { id: 6, name: '虾滑', price: 36, category: '海鲜', unit: '份' }
    ]
  },
  delivery: {
    available: true,
    min_order: 100,
    delivery_fee: 10,
    range: '5公里内',
    estimated_time: '40-60分钟'
  },
  news: [
    { type: 'promotion', content: '午市套餐7折优惠（11:00-14:00）' },
    { type: 'notice', content: '新到鲜切羊肉，欢迎品尝' }
  ]
};

const tools = {
  get_shop_info: () => db.shopInfo,
  get_queue_status: (params) => ({
    tables: db.queue.tables,
    total_waiting: db.queue.current_wait
  }),
  take_queue_number: (params) => {
    const { table_type_id, people_count } = params;
    const queueNum = `H${String(Math.floor(Math.random() * 100) + 1).padStart(2, '0')}`;
    return {
      success: true,
      queue_number: queueNum,
      estimated_wait_minutes: Math.floor(Math.random() * 40) + 10,
      message: '取号成功'
    };
  },
  book_table: (params) => ({
    success: true,
    booking_id: `BK${Date.now()}`,
    message: '预约成功'
  }),
  get_menu: () => db.menu,
  get_delivery_info: () => db.delivery,
  get_wifi_info: () => db.shopInfo.wifi,
  get_latest_news: () => db.news
};

const server = http.createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Content-Type', 'application/json');
  if (req.method === 'OPTIONS') { res.writeHead(200); res.end(); return; }

  let body = '';
  req.on('data', chunk => body += chunk);
  req.on('end', () => {
    try {
      const { method, params = {}, id } = JSON.parse(body);
      let result;

      if (method === 'tools/list') {
        result = { tools: Object.keys(tools).map(name => ({ name, description: `调用${name}` })) };
      } else if (method === 'tools/call') {
        const tool = tools[params.name];
        result = tool ? { content: [{ type: 'text', text: JSON.stringify(tool(params.arguments || {})) }] } : { error: 'not found' };
      }

      res.writeHead(200);
      res.end(JSON.stringify({ jsonrpc: '2.0', id, result }));
    } catch (e) {
      res.writeHead(400);
      res.end(JSON.stringify({ error: 'Invalid JSON' }));
    }
  });
});

server.listen(PORT, () => {
  console.log(`🍲 宏缘火锅 MCP Server 已启动 - http://localhost:${PORT}`);
});
