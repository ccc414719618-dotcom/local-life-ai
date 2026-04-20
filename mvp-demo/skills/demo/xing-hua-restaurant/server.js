/**
 * 兴华家常菜 - MCP Server (Demo版)
 */

const http = require('http');

const PORT = 8004;

const db = {
  shopInfo: {
    name: '兴华家常菜',
    branch: '五道口店',
    address: '北京市海淀区成府路28号',
    phone: '010-82346789',
    hours: '10:30-22:30',
    wifi: { ssid: 'XHJC_WiFi', password: '99887766' }
  },
  queue: {
    current_wait: 5,
    tables: [
      { id: 1, name: '2人桌', available: true, current_wait: 0 },
      { id: 2, name: '4人桌', available: true, current_wait: 2 },
      { id: 3, name: '6人桌', available: true, current_wait: 1 },
      { id: 4, name: '包间(10人)', available: false, current_wait: 3 }
    ]
  },
  menu: {
    categories: ['招牌菜', '凉菜', '热菜', '主食', '汤类', '饮品'],
    items: [
      { id: 1, name: '红烧肉', price: 48, category: '招牌菜', unit: '份' },
      { id: 2, name: '糖醋里脊', price: 38, category: '招牌菜', unit: '份' },
      { id: 3, name: '宫保鸡丁', price: 32, category: '热菜', unit: '份' },
      { id: 4, name: '酸菜鱼', price: 58, category: '热菜', unit: '份' },
      { id: 5, name: '凉拌黄瓜', price: 12, category: '凉菜', unit: '份' },
      { id: 6, name: '米饭', price: 2, category: '主食', unit: '碗' }
    ]
  },
  delivery: {
    available: true,
    min_order: 30,
    delivery_fee: 6,
    range: '4公里内',
    estimated_time: '35-50分钟'
  },
  news: [
    { type: 'promotion', content: '新客满100减20' },
    { type: 'notice', content: '推出春季时令新菜，欢迎品尝' }
  ]
};

const tools = {
  get_shop_info: () => db.shopInfo,
  get_queue_status: () => ({
    tables: db.queue.tables,
    total_waiting: db.queue.current_wait
  }),
  take_queue_number: (params) => {
    const { table_type_id, people_count } = params;
    const queueNum = `X${String(Math.floor(Math.random() * 100) + 1).padStart(2, '0')}`;
    return {
      success: true,
      queue_number: queueNum,
      estimated_wait_minutes: Math.floor(Math.random() * 30) + 5,
      message: '取号成功，请留意叫号'
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
  console.log(`🍳 兴华家常菜 MCP Server 已启动 - http://localhost:${PORT}`);
});
