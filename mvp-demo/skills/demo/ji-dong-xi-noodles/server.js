/**
 * 季多西面馆 - MCP Server (Demo版)
 */

const http = require('http');

const PORT = 8003;

const db = {
  shopInfo: {
    name: '季多西面馆',
    branch: '北邮店',
    address: '北京市海淀区西土城路10号',
    phone: '010-62234567',
    hours: '07:00-21:00',
    wifi: { ssid: 'JDX_WiFi', password: '66668888' }
  },
  menu: {
    categories: ['拉面类', '刀削面类', '拌面类', '小吃', '饮品'],
    items: [
      { id: 1, name: '牛肉拉面', price: 22, category: '拉面类', unit: '碗' },
      { id: 2, name: '羊肉拉面', price: 24, category: '拉面类', unit: '碗' },
      { id: 3, name: '刀削面', price: 18, category: '刀削面类', unit: '碗' },
      { id: 4, name: '油泼面', price: 16, category: '拌面类', unit: '碗' },
      { id: 5, name: '炸酱面', price: 15, category: '拌面类', unit: '碗' },
      { id: 6, name: '肉夹馍', price: 8, category: '小吃', unit: '个' },
      { id: 7, name: '凉皮', price: 10, category: '小吃', unit: '份' }
    ]
  },
  delivery: {
    available: true,
    min_order: 15,
    delivery_fee: 3,
    range: '2公里内',
    estimated_time: '20-30分钟'
  },
  news: [
    { type: 'promotion', content: '早餐时段（7:00-9:00）豆浆免费' },
    { type: 'notice', content: '新增番茄牛腩拉面，限时尝鲜价18元' }
  ]
};

const tools = {
  get_shop_info: () => db.shopInfo,
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
  console.log(`🍜 季多西面馆 MCP Server 已启动 - http://localhost:${PORT}`);
});
