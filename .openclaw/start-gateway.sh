#!/bin/bash
export CHROME_USER_DATA_DIR="$HOME/Library/Application Support/Google/Chrome/Default"

export OPENCLAW_ACCOUNT_ID=jinrong-bot
export OPENCLAW_GATEWAY_PORT=18793
export FEISHU_APP_SECRET=NAZDpp63znkfGzcskC1hgh5xRMPV51jr

cd /Volumes/1TB/openclaw/jinrong-bot
exec /usr/local/bin/node /Users/Zhuanz/.npm-global/lib/node_modules/openclaw/dist/index.js gateway --port 18793
