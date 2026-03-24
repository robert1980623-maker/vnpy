#!/bin/bash
# Crontab 安装脚本

echo "📋 当前 crontab 配置:"
crontab -l 2>/dev/null || echo "(无配置)"

echo ""
echo "📝 新配置内容:"
cat /tmp/new_crontab.txt

echo ""
read -p "是否安装新配置？(y/n): " confirm

if [ "$confirm" = "y" ]; then
    crontab /tmp/new_crontab.txt
    echo ""
    echo "✅ 安装完成！新配置:"
    crontab -l
else
    echo "❌ 已取消"
fi
