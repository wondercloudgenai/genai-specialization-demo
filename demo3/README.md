# Fine Tuning For Vertex AI

**项目简介**

使用Google Vertex AI 模型微调（fine-tuning）功能, 采用监督式微调。

## 项目结构
```
fine_tuning/
├── config/
│   └── config.yaml
├── gemini_tuning/
│   ├── start.py
│   ├── dataset.py
│   └── evaluator.py
│   └── tuning.py
│── tools/
│   └── log_utils.py
├── model_generation.py
├── __init__.py
├── README.md
└── requirements.txt
```


## 快速开始

### 环境准备

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.\.venv\Scripts\activate   # Windows
```
### 安装依赖

```bash
pip install -r requirements.txt
```

### 权限配置
由于微调需要访问Vertex AI的API以及GCS的权限，所以需要配置认证：
```bash
## 方式一：使用本地认证（ADC）
gcloud auth application-default login
## 方式二：使用服务账号认证
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
```


### 数据准备

推荐数据格式：JSONL（每行一个 JSON），字段示例：
```jsonl
{"contents":[{"role":"user","parts":[{"text":"问题"}]},{"role":"model","parts":[{"text":"回答"}]}]}
{"contents":[{"role":"user","parts":[{"text":"问题"}]},{"role":"model","parts":[{"text":"回答"}]}]}
```
请把训练/验证数据放在 `dataset/` 目录下，或项目指定的路径。

### 微调参数
| 字段 | 说明 | 游戏客服场景建议                                                        |
|------|------|-----------------------------------------------------------------|
| source_model_name | 基础模型名称 | ✅ 必填，比如 "gemini-2.5-flash"                                      |
| train_dataset | 训练集 JSONL 文件（GCS 路径） | ✅ 必填，比如 gs://your-bucket/game-cs-train.jsonl                    |
| validation_dataset | 验证集 JSONL 文件（GCS 路径） | ✅ 建议提供（比如 gs://your-bucket/game-cs-valid.jsonl），这样 SDK 会在训练中做评估 |
| tuned_model_display_name | 微调后模型的展示名 | 取个有意义的名字，比如 "gemini-2.5-flash-game-cs-v1"                       |
| epoch | 训练轮次 | 推荐 3~5（一般 3 就够，数据少时可以 5）                                        |
| learning_rate_multiplier | 学习率倍数（基于默认） | 一般不用设，想更稳可设 0.5，表示降低默认学习率一半                                     |
| adapter_size | LoRA adapter 大小 | 可选 AdapterSize.SMALL 或 MEDIUM；游戏客服场景推荐 SMALL（数据量不大）             |
| export_last_checkpoint_only | 是否只导出最后一个 checkpoint | 调优数据量不大，建议导出一个即可                                                |
### 启动微调任务

训练命令：
```bash
python -m gemini_tuning.start --config=config/config.yaml
```

### 评估/推理
- 微调时：开启微调时设置validation_dataset参数，可以在训练过程中评估模型微调性能。
- 微调后：使用微调后的模型进行自定义评估，根据多维度的各项指标打分。


## 数据与微调建议
- 数据多样化：包含不同问法与长回答示例； 
- 混合开放域样本以保留通用能力； 
- 使用少量高质量样本进行微调，以避免过度拟合；
- 使用 LoRA/PEFT 等参数高效微调方法以降低对原始能力的破坏。
- 监控训练指标，如损失、准确率等，及时调整超参数。

## 日志与监控
- 训练日志会输出到控制台，也可以在Google Cloud logging中查看。
- 监控数据可以在Google Cloud Console中查看。

