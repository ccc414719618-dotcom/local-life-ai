#!/bin/bash
# Core Engine 测试快捷命令
echo "运行单元测试..."
bun test ./src/core/test.ts
echo ""
echo "运行集成测试..."
bun run test-core-engine.ts
