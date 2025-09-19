#!/bin/bash

# 数据导出系统前端启动脚本

echo "启动数据导出系统前端..."

# 检查Node.js是否安装
if ! command -v node &> /dev/null; then
    echo "错误: 未找到Node.js，请先安装Node.js"
    exit 1
fi

# 检查npm是否安装
if ! command -v npm &> /dev/null; then
    echo "错误: 未找到npm，请先安装npm"
    exit 1
fi

# 当前已在前端目录

# 检查是否已安装依赖
if [ ! -d "node_modules" ]; then
    echo "安装前端依赖..."
    npm install
fi

# 启动开发服务器
echo "启动前端开发服务器..."
echo "访问地址: http://localhost:3000"
npm run dev