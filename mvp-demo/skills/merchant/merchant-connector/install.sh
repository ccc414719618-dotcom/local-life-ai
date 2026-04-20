#!/bin/bash

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  🏪  本地生活 AI - 商家端                    ║"
echo "║  让你的店被 AI 发现，7x24 自动接待           ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

read -p "店铺名称（如：金谷园饺子馆）: " shop_name
shop_name=${shop_name:-我的店铺}

echo ""
echo "╭──────────────────────────────────────╮"
echo "│  $shop_name 很好记！                 │"
echo "╰──────────────────────────────────────╯"
echo ""

echo "┌──────────────────────────────────────┐"
echo "│  接下来告诉我一些店铺信息              │"
echo "│  我好帮你配置 AI 接待功能             │"
echo "└──────────────────────────────────────┘"
echo ""

echo "【1】店铺类型"
echo "   1 餐饮  2 轻食  3 咖啡  4 超市  5 其他"
read -p "   输入编号: " shop_type

echo ""
echo "【2】地址"
echo "   正在自动获取位置..."
location_data=$(curl -s "http://ip-api.com/json/?lang=zh" 2>/dev/null)
city=$(echo "$location_data" | grep -o '"city":"[^"]*"' | cut -d'"' -f4)
region=$(echo "$location_data" | grep -o '"regionName":"[^"]*"' | cut -d'"' -f4)
lat=$(echo "$location_data" | grep -o '"lat":[0-9.-]*' | cut -d':' -f2)
lon=$(echo "$location_data" | grep -o '"lon":[0-9.-]*' | cut -d':' -f2)

if [ -n "$city" ]; then
  echo "   检测到: $city, $region"
else
  echo "   无法获取位置，请手动输入"
  city=""
fi

read -p "   详细地址: " address
if [ -n "$city" ]; then
  full_address="$city $address"
else
  full_address="$address"
fi

echo ""
echo "【3】营业时间（直接回车默认为 10:00-22:00）"
read -p "   格式 09:00-22:00: " hours
hours=${hours:-10:00-22:00}

echo ""
echo "【4】服务能力（可多选）"
echo "   1 排队取号  2 座位预约  3 外卖"
echo "   4 菜单查询  5 Wi-Fi"
read -p "   输入编号: " caps

echo ""
echo "【5】健康标签（可多选）"
echo "   1 低油脂  2 低糖  3 无麸质  4 素食"
echo "   5 纯素  6 无反式脂肪  7 清真"
read -p "   输入编号: " health

# 生成店铺ID
shop_id="shop_$(date +%s)"
shop_type_text=""
case $shop_type in
  1) shop_type_text="餐饮" ;;
  2) shop_type_text="轻食" ;;
  3) shop_type_text="咖啡" ;;
  4) shop_type_text="超市" ;;
  5) shop_type_text="其他" ;;
esac

# 解析服务能力
caps_list=""
caps_text=""
case $caps in
  *1*) caps_list="${caps_list}queue,"; caps_text="${caps_text}排队取号 " ;;
esac
case $caps in
  *2*) caps_list="${caps_list}reservation,"; caps_text="${caps_text}座位预约 " ;;
esac
case $caps in
  *3*) caps_list="${caps_list}delivery,"; caps_text="${caps_text}外卖 " ;;
esac
case $caps in
  *4*) caps_list="${caps_list}menu,"; caps_text="${caps_text}菜单查询 " ;;
esac
case $caps in
  *5*) caps_list="${caps_list}wifi,"; caps_text="${caps_text}Wi-Fi " ;;
esac
caps_list="${caps_list}info"

# 解析健康标签
health_text=""
health_list=""
case $health in
  *1*) health_list="${health_list}低油脂,"; health_text="${health_text}低油脂 " ;;
esac
case $health in
  *2*) health_list="${health_list}低糖,"; health_text="${health_text}低糖 " ;;
esac
case $health in
  *3*) health_list="${health_list}无麸质,"; health_text="${health_text}无麸质 " ;;
esac
case $health in
  *4*) health_list="${health_list}素食,"; health_text="${health_text}素食 " ;;
esac
case $health in
  *5*) health_list="${health_list}纯素,"; health_text="${health_text}纯素 " ;;
esac
case $health in
  *6*) health_list="${health_list}无反式脂肪,"; health_text="${health_text}无反式脂肪 " ;;
esac
case $health in
  *7*) health_list="${health_list}清真,"; health_text="${health_text}清真 " ;;
esac

# 设置坐标默认值
lat=${lat:-0}
lon=${lon:-0}

# 保存本地配置
mkdir -p ~/.config/local-life-ai

cat > ~/.config/local-life-ai/merchant-config.json << EOF
{
  "shop_id": "$shop_id",
  "shop_name": "$shop_name",
  "shop_type": "$shop_type_text",
  "address": "$full_address",
  "hours": "$hours",
  "location": {
    "lat": $lat,
    "lon": $lon
  },
  "capabilities": "$caps_text",
  "health_labels": "${health_list%,}",
  "platform": "http://localhost:3000"
}
EOF

# 注册到平台 MCP
echo ""
echo "⏳ 正在注册到平台..."

register_result=$(curl -s -X POST http://localhost:3000/api/merchant/register \
  -H "Content-Type: application/json" \
  -d "{
    \"shop_id\": \"$shop_id\",
    \"shop_name\": \"$shop_name\",
    \"categories\": [\"$shop_type_text\"],
    \"location\": {
      \"lat\": $lat,
      \"lon\": $lon,
      \"address\": \"$full_address\",
      \"hours\": \"$hours\"
    },
    \"contact\": {
      \"hours\": \"$hours\"
    },
    \"capabilities\": [${caps_list%,}],
    \"health_tags\": {
      \"health_labels\": [${health_list%,}]
    }
  }" 2>/dev/null || echo '{"status":"offline"}')

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║                                              ║"
echo "║   ✅ 安装完成！$shop_name 上线啦！          ║"
echo "║                                              ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

echo "┌──────────────────────────────────────────────┐"
echo "│  📋 店铺信息                               │"
echo "├──────────────────────────────────────────────┤"
echo "│  名称: $shop_name                        │"
echo "┌──────────────────────────────────────────────┐"
echo "│  🎯 AI 会帮你做这些：                       │"
echo "├──────────────────────────────────────────────┤"
echo "│  🤖 自动接待 - 7x24 在线                   │"
echo "│  📋 排队管理 - 自动取号叫号                │"
echo "│  📅 预约处理 - 接收并确认预约              │"
echo "│  🍽️ 菜单问答 - 推荐招牌菜                  │"
echo "└──────────────────────────────────────────────┘"
echo ""

echo "📁 配置: ~/.config/local-life-ai/merchant-config.json"
echo "🌐 平台: http://localhost:3000"
echo ""
echo "⚠️  位置提示：IP 定位精度为城市/区县级"
echo "   如需精确到街道，请访问："
echo "   → http://localhost:3000/calibrate?id=$shop_id"
echo ""
