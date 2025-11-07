#!/bin/bash

# 查找匹配的进程的PID
PID=$(ps -ef | grep 'main:app --port 8080 --reload' | grep -v 'grep' | head -n 1 | awk '{print $2}')

# 检查是否找到了进程
if [ -n "$PID" ]; then
    echo "Killing process $PID"
    sudo kill -9 $PID
else
    echo "No matching process found to kill."
fi

# 等待5秒
sleep 5

# 重新启动应用
echo "Starting the application..."
sudo nohup /home/moski/.env/bin/uvicorn main:app --port 8080 --reload >> web.log 2>&1 &
echo "Application started."

