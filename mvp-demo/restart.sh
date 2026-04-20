#!/bin/bash
lsof -ti :3000 | xargs kill -9 2>/dev/null
sleep 1
cd /Volumes/1TB/openclaw/jinrong-bot/mvp-demo/registry
node server.js > /dev/null 2>&1 &
echo "Started on PID $!"
