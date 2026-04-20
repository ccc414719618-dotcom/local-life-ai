#!/usr/bin/env python3
"""
Quinn 金融报告推送飞书
使用飞书 Card 消息格式推送专业分析报告
"""

import sys
import os
import json
from datetime import datetime

# 添加finance模块路径
sys.path.insert(0, '/Volumes/1TB/openclaw/jinrong-bot')
from finance.report_generator import ReportGenerator


def format_feishu_card(report_text: str) -> dict:
    """将报告文本格式化为飞书交互卡片"""
    
    # 解析报告各部分
    lines = report_text.split('\n')
    
    # 构建卡片元素
    elements = []
    current_section = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('==='):
            # 标题行
            continue
        elif line.startswith('📊') or line.startswith('🌡️') or line.startswith('🥇') or line.startswith('📈') or line.startswith('📉'):
            # 部分标题
            if current_section:
                elements.append({"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(current_section)}})
                current_section = []
            elements.append({"tag": "hr"})
            elements.append({"tag": "div", "text": {"tag": "lark_md", "content": f"**{line}**"}})
        elif line.startswith('【'):
            # 小标题
            current_section.append(f"**{line}**")
        elif line.startswith('├') or line.startswith('└') or line.startswith('│'):
            # 内容行
            current_section.append(line)
        elif line.startswith('🔴') or line.startswith('🟢') or line.startswith('📈') or line.startswith('📉'):
            # 重要信号
            elements.append({"tag": "div", "text": {"tag": "lark_md", "content": line}})
        elif line.startswith('⚠️'):
            # 免责声明
            elements.append({"tag": "hr"})
            elements.append({"tag": "note", "elements": [{"tag": "plain_text", "content": line}]})
        else:
            current_section.append(line)
    
    if current_section:
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(current_section)}})
    
    # 构建完整卡片
    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": "🔍 QUINN 金融分析报告"},
                "template": "purple"
            },
            "elements": elements
        }
    }
    
    return card


def send_feishu(card: dict, webhook_url: str = None) -> bool:
    """发送飞书卡片消息"""
    if not webhook_url:
        # 使用飞书机器人的 webhook（需要配置）
        # 这里简化处理，实际应该用 Bot API
        return False
    
    try:
        import urllib.request
        data = json.dumps(card).encode('utf-8')
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read()).get('code') == 0
    except:
        return False


def main():
    """生成报告并打印（实际推送需要配置webhook）"""
    print("正在生成金融分析报告...")
    
    generator = ReportGenerator(use_akshare=False)
    report = generator.generate_daily_report(['bitcoin', 'ethereum', 'solana'])
    
    print("\n" + "="*60)
    print(report)
    print("="*60)
    
    # 实际推送时取消注释
    # card = format_feishu_card(report)
    # if send_feishu(card, WEBHOOK_URL):
    #     print("\n✅ 报告已推送飞书")
    # else:
    #     print("\n⚠️ 请配置飞书 Webhook URL")
    
    return report


if __name__ == '__main__':
    main()
