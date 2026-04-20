#!/bin/bash
cd /Volumes/1TB/openclaw/jinrong-bot/mvp-demo/registry
node server.js > /tmp/mvp-server.log 2>&1 &
echo "Server started"
