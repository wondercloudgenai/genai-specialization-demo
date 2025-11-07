# Agent智能聊天系统

基于 Google ADK 构建的智能Agent聊天助手系统，解决了 Google API 的工具限制问题，允许同时使用多种工具功能。

## 功能特性

- **智能路由系统**：根据用户输入自动选择最合适的 Agent
- **完美集成 ADK Web 界面**：提供友好的用户交互界面
- **实时监控和自动记忆功能**：会话结束后自动保存到内存
- **支持 RESTful API 调用**：可手动选择 Agent 或使用智能路由
- **关键词自动识别**：根据关键词自动判断用户意图并调用相应功能

## 技术栈

- **后端框架**：
  - FastAPI
  - Uvicorn
- **语言**：
  - Python 3.11+
- **依赖库**：
  - google-adk==1.13.0
  - uvicorn==0.35.0
  - fastapi==0.116.1
  - protobuf==6.31.1
  - google-cloud-aiplatform==1.111.0
  - python-dotenv==1.1.1
- **部署**：
  - Docker
  - Google Cloud Run

## 项目结构

```
.
├── chat-agent/                     # Agent 实现目录
│   ├── sub_agents/                 # 子 Agent 目录
│   │   ├── google_search/          # Google 搜索子 Agent
│   │   └── vertexai_search/        # VertexAI 搜索子 Agent
│   ├── chat_agent.py               # 主 Agent 实现
│   └── prompt.py                   # 提示词定义
├── main.py                         # FastAPI 应用入口
├── Dockerfile                      # Docker 配置
├── requirements.txt                # 项目依赖
└── .env                            # 环境变量配置
```

## 核心组件说明

### 多Agent架构

本系统采用多Agent架构设计，包括：

1. **主Agent (root_agent)** - 统一智能助手
   - 集成所有功能的统一入口
   - 智能路由分发用户请求到合适的子Agent
   - 自动保存会话到内存银行

2. **子Agent**
   - Google搜索Agent - 专门处理Google搜索任务
   - VertexAI搜索Agent - 专门处理VertexAI搜索任务

### 智能路由机制

系统通过关键词匹配实现智能路由：
- 搜索相关关键词 → 调用搜索功能
- 记忆相关关键词 → 调用记忆功能
- 自定义相关关键词 → 调用自定义功能
- 其他情况 → 使用综合服务

## 快速开始

### 环境准备

1. Python 3.11+
2. Google Cloud 账户
3. Docker (可选，用于部署)

### 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd muti-agent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 配置环境变量

复制 `.env` 文件并根据需要进行修改：

```bash
cp .env.example .env
```

关键配置项：
- `GOOGLE_CLOUD_PROJECT`: Google Cloud 项目ID
- `GOOGLE_CLOUD_LOCATION`: Google Cloud 位置
- `AGENT_ENGINE_ID`: Agent Engine ID
- `DATASTORE_ID`: 数据存储ID
- `MODEL_ID`: 使用的模型ID (如 gemini-2.5-flash)

### 本地运行

```bash
# 启动服务
python main.py

# 或者使用 uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

访问 `http://localhost:8080` 查看 ADK Web 界面。

## 部署

### 使用 Docker 部署

```bash
# 构建 Docker 镜像
docker build -t muti-agent .

# 运行容器
docker run -p 8080:8080 \
  -e GOOGLE_CLOUD_PROJECT=your-project-id \
  -e GOOGLE_CLOUD_LOCATION=your-location \
  -e AGENT_ENGINE_ID=your-agent-engine-id \
  -e DATASTORE_ID=your-datastore-id \
  -v /path/to/credentials.json:/app/credentials.json \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
  muti-agent
```

### 使用 Google Cloud Run 部署

#### 准备工作

1. 安装并配置 [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
2. 初始化 gcloud 并设置项目：
   ```bash
   gcloud init
   ```
3. 启用相关服务：
   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   ```

#### 构建并部署到 Cloud Run

使用 gcloud CLI 直接部署（推荐方式）：

```bash
gcloud run deploy muti-agent \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=your-project-id \
  --set-env-vars GOOGLE_CLOUD_LOCATION=us-central1 \
  --set-env-vars AGENT_ENGINE_ID=your-agent-engine-id \
  --set-env-vars DATASTORE_ID=your-datastore-id \
  --set-env-vars MODEL_ID=gemini-2.5-flash
```

或者，先构建容器镜像再部署：

```bash
# 构建并推送镜像到 Container Registry
gcloud builds submit --tag gcr.io/your-project-id/muti-agent

# 部署到 Cloud Run
gcloud run deploy muti-agent \
  --image gcr.io/your-project-id/muti-agent \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=your-project-id \
  --set-env-vars GOOGLE_CLOUD_LOCATION=us-central1 \
  --set-env-vars AGENT_ENGINE_ID=your-agent-engine-id \
  --set-env-vars DATASTORE_ID=your-datastore-id \
  --set-env-vars MODEL_ID=gemini-2.5-flash
```

部署完成后，Cloud Run 会提供一个 URL，你可以通过该 URL 访问你的应用。

## 使用说明

系统会根据用户输入的关键词自动选择相应的功能：

1. **搜索相关关键词**（搜索、查找、查询、search、find、google、网页、网站、新闻、最新、信息、资料）
   → 使用搜索功能，优先选择最合适的搜索工具

2. **记忆相关关键词**（记忆、历史、之前、上次、记住、保存、记录、回忆、历史记录、对话历史、上下文、memory、history、remember、save、recall、context）
   → 使用记忆功能，保存或检索信息

3. **自定义相关关键词**（特殊、自定义、特殊功能、高级功能、专业功能、定制、个性化、专门、特定、custom、special、advanced、specific、personalized）
   → 使用自定义功能，执行高级操作

4. **其他情况**
   → 使用综合服务，提供一般性帮助

## API 文档

启动服务后，可以通过以下方式访问 API 文档：

- API 文档: `http://localhost:8080/api/docs`

## 安全性

- 通过 Google Cloud SDK 进行认证
- 使用环境变量管理敏感配置
- 建议在生产环境中使用 HTTPS

## 已知限制

- 必须使用 Google Cloud 服务
- 需要有效的 Google Cloud 项目和相关服务配置
- 依赖 Google ADK 框架功能

## 开发指南

### 代码结构说明

- `main.py` - 应用入口，初始化 FastAPI 应用
- `chat-agent/chat_agent.py` - 主 Agent 实现，包含智能路由和自动保存逻辑
- `chat-agent/prompt.py` - 系统提示词定义
- `chat-agent/sub_agents/` - 各个子 Agent 的实现
- `chat-agent/sub_agents/google_search/` - Google 搜索子 Agent
- `chat-agent/sub_agents/vertexai_search/` - VertexAI 搜索子 Agent

### 添加新功能

1. 在 `chat-agent/sub_agents/` 目录下创建新的子 Agent
2. 在 `chat-agent/chat_agent.py` 中的关键词识别逻辑中添加相应的路由规则
3. 将新 Agent 添加到主 Agent 的工具列表中

### 代码注释规范

项目中的所有代码都包含详细的中文注释，便于理解和维护：
- 函数注释说明功能、参数和返回值
- 关键代码行添加行内注释解释逻辑
- 类和模块有整体功能说明
