sudo ps -ef | grep 'backgroup_task.main worker' |grep -v 'grep'|awk '{print $2}' | xargs kill -9
echo "kill process successful, waiting restart..."
sleep 5
nohup /home/moski/.env/bin/celery -A backgroup_task.main worker > task.log 2>&1 &
