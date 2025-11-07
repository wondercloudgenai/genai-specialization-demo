# vector_app_server_v1

向量英才招聘者服务端代码

## 一、代码目录说明

├─admin             后台管理相关api接口

├─backgroup_task    后台celery异步任务

├─curd              数据持久层相关代码

├─data              存放临时文件

│  ├─log            存放临时APP RUN日志

│  ├─static         静态文件

│  └─tmp            存放临时文件

├─model             数据持久化实例对象

├─routers           路由Router/Controller代码

├─schema            请求表单对象包含校验部分

├─services          业务层代码

│  ├─exceptions     全局Exceptions处理器

│  └─middlewares    中间件代码

└─tools             独立的工具函数/类

## 二、部署方法
1、安装python环境，请参考[python安装](https://www.python.org/downloads/)，该项目使用的python版本为3.11

2、安装依赖包，使用pip安装依赖包，命令如下：
```bash
pip install -r requirements.txt
```
3、安装docker，请参考[docker安装](https://docs.docker.com/get-docker/)

4、安装redis服务，
```bash
docker pull redis:latest
```

5、启动redis服务，命令如下：
```bash
docker run -d \
    --name redis \
    --restart always \
    -p 6379:6379 \
    -v /data/redis:/data \
    redis:latest
```

6、安装postgresql服务，由于本项目会用到vector数据扩展，需要拉取pgvector，pgvector是postgresql数据库，增加了vector扩展，命令如下：
```bash
docker pull pgvector:latest
```

7、启动pgvector，命令如下：
```bash
docker run -d \
    --name pgvector-db \
    -p 5433:5432 \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=vector \
    -e POSTGRES_DB=vector \
    -v /data/pgdata:/var/lib/postgresql/data \
    pgvector:latest
```

8、修改项目中的配置文件，即本项目中的根目录下的settings.py文件，需重点修改以下几个字段：
* pg_host: str = Field("localhost:5433", alias="pg_host")，该字段为pgvector数据库的连接地址，默认为localhost:5433，端口号为步骤7中pgvector-db绑定到宿主机上的端口号
* pg_db: str = Field("vector", alias="pg_db")，步骤7中指定的数据库名称
* pg_user: str = Field("postgres", alias="pg_user")，步骤7中指定的用户名
* pg_password: str = Field(r"vector", alias="pg_password")，步骤7中指定的密码
* REDIS_URL: str = "redis://localhost:6379/0"，需注意步骤6中启动redis服务时，指定的端口号，默认为6379

9、初始化一些原始数据
> 1、 初始化地域信息，执行`data/init_ehire_city_db.py`
> 
> 2、 初始超级管理员账号，执行`initialize_script.py`,管理员密码可以自己设置
> 

10、启动后台异步任务celery，需注意celery安装的位置，命令如下：
```bash
sudo sh restart_task.sh
```

11、启动项目，需注意uvicorn安装的位置，命令如下：
```bash
sudo sh restart.sh
```

13、配置nginx，配置完成后记得重启nginx
```bash
server{
        listen 80;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;    #添加透传配置
        listen [::]:80;
        index index.html index.htm index.nginx-debian.html;
        client_max_body_size 100M;
        server_name v2.aihunting.work aihunting.work www.aihunting.work;
        access_log   /var/log/nginx/aplt_access.log;
        error_log   /var/log/nginx/aplt_error.log;
        location / {
            root /var/www/applicant;
            index index.html;
            try_files $uri $uri/ @router;
        }
        location @router {
            rewrite  ^.*$ /index.html last;
        }
        location /api2/ {
                proxy_pass http://localhost:8090/;
        }
        location /api1/ {
                proxy_pass http://aihunting.work/;
        }
        location /docs {
                proxy_pass http://localhost:8090;
        }
        location /api/v2 {
                proxy_pass http://localhost:8090;
        }
        location /openapi.json {
                proxy_pass http://localhost:8090;
        }

        location /api/v2/ws {
                proxy_pass http://localhost:8090;
                proxy_http_version 1.1;
                proxy_set_header Upgrade $http_upgrade;
                proxy_set_header Connection "upgrade";
        }

}
server {
        listen 80 ;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;    #添加透传配置
        listen [::]:80;
        index index.html index.htm index.nginx-debian.html;
        client_max_body_size 100M;
        server_name aplt.aihunting.work v1.aihunting.work;

         location / {
                root /var/www/html;
                index index.html;
                try_files $uri $uri/ @router;
        }
        location /tencent16086498621472188839.txt {
                proxy_pass http://localhost:8080;
        }
        location @router {
                rewrite ^.*$ /index.html last;
        }
        location /api2/ {
                proxy_pass http://localhost/;
        }
        location /docs {
                proxy_pass http://localhost:8080;
        }
        location /openapi.json {
                proxy_pass http://localhost:8080;
        }

        location /api/v1 {
                proxy_pass http://localhost:8080;
        }
        location /api/v1/ws {
                proxy_pass http://localhost:8080;
                proxy_http_version 1.1;
                proxy_set_header Upgrade $http_upgrade;
                proxy_set_header Connection "upgrade";
        }
}
server{
        listen 80;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real_IP $remote_addr;
        listen [::]:80;
        index index.html index.htm;
        server_name admin.aihunting.work;
        location / {
                root /var/www/admin;
                index index.html;
                try_files $uri $uri/ @router;
        }

        location @router{
                rewrite ^.*$ /index.html last;
        }
        location /api1/ {
                proxy_pass http://localhost/;
        }
        location /api2/ {
                proxy_pass http://localhost:8090/;
        }

        location /api/v1 {
                proxy_pass http://localhost:8080;
        }
        location /api/v2 {
                proxy_pass http://localhost:8090;
        }

}
```

14、本项目实际代码是部署在谷歌云服务器上，但域名实际上是指向阿里云服务器的，所以需要再阿里云服务器上配置nginx转发，同时配置域名DNS