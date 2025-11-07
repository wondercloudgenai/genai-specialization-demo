# load the required libraries start
import pickle
import numpy as np
# load the required libraries
import pandas as pd
from google.cloud import storage
from google.cloud.bigquery import Client
import argparse
# from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error  # <-- 修改这里
# from sklearn.model_selection import train_test_split


# -----------------------------
# 修改这里：换成 Ridge 而不是 LinearRegression
# Ridge 回归支持超参数 alpha (正则化强度)
# -----------------------------
from sklearn.linear_model import Ridge                # <<< 修改 
from sklearn.model_selection import train_test_split, GridSearchCV  # <<< 修改（新增 GridSearchCV）

parser = argparse.ArgumentParser()
parser.add_argument("--alpha", type=float, required=True)

parser.add_argument("--PROJECT_ID", type=str, required=True)
parser.add_argument("--LOCATION_BQ", type=str, required=True)
parser.add_argument("--LOCATION", type=str, required=True)
parser.add_argument("--BUCKET_URI", type=str, required=True)

args = parser.parse_args()

print("Received alpha:", args.alpha, args.PROJECT_ID,args.LOCATION_BQ,args.LOCATION,args.BUCKET_URI)

PROJECT_ID = args.PROJECT_ID
LOCATION1 = args.LOCATION_BQ  
LOCATION = args.LOCATION  
BUCKET_URI =  args.BUCKET_URI  
# SERVICE_ACCOUNT_KEY_PATH = os.getenv("SERVICE_ACCOUNT_KEY_PATH")

# credentials = service_account.Credentials.from_service_account_file(
#     SERVICE_ACCOUNT_KEY_PATH,
#     scopes=['https://www.googleapis.com/auth/cloud-platform']
# )
client = Client(
    project=PROJECT_ID,
    location=LOCATION1,
    # credentials=credentials,
)

# -----------------------------
# 查询 BigQuery 数据
# -----------------------------
query = """SELECT 
    taxi_id, trip_start_timestamp, 
    trip_seconds, trip_miles, trip_total, 
    payment_type, pickup_community_area, 
    dropoff_community_area 
    FROM `genai-specialization-468108.kade_machine_learning.kade_taxi_trips`
    WHERE 
    trip_start_timestamp >= '2018-05-12' AND 
    trip_end_timestamp <= '2018-05-17' AND
    trip_seconds > 60 AND trip_seconds < 6*60*60 AND
    trip_miles > 0 AND
    trip_total > 3 AND
    pickup_community_area IS NOT NULL AND
    dropoff_community_area IS NOT NULL"""

job = client.query(query)  # 使用 BigQuery 客户端提交SQL查询任务
df = job.to_dataframe()   # 将查询结果转成 Pandas DataFrame 方便数据分析

print(df.shape)           # 输出数据维度（行数和列数）
df.columns                # 查看DataFrame所有列名
df.head()                 # 显示前5条数据，快速预览内容
df.dtypes                 # 查看每列的数据类型
df.info()                 # 输出DataFrame详细信息（非空值数量、类型、内存）
df.describe().T           # 对数值列做统计描述并转置，方便查看均值、标准差等指标'
# -----------------------------
# 数据清洗、特征工程
# -----------------------------
df = df.rename(columns={"trip_total": "trip_pricing_total"})
# 你要做一个机器学习任务，目标是预测 trip_pricing_total （出租车行程总费用），这个字段就是你的目标变量（target）。
target = "trip_pricing_total"
    # •	payment_type（付款类型，比如现金、信用卡等）
    # •	pickup_community_area（上车地点所在社区区域编号）
    # •	dropoff_community_area（下车地点所在社区区域编号）
categ_cols = ["payment_type", "pickup_community_area", "dropoff_community_area"]
    # •	trip_seconds（行程时间，单位是秒）
    # •	trip_miles（行程距离，单位是英里）
num_cols = ["trip_seconds", "trip_miles"]

# trip_seconds 是行程时间，单位是秒。为了分析更方便，把它换算成小时：
df["trip_hours"] = round(df["trip_seconds"] / 3600, 2)
# 用里程数除以小时数，得到平均速度（英里/小时）：
df["trip_speed"] = round(df["trip_miles"] / df["trip_hours"], 2)

# 提取小时（0~23）
df["hour"] = df["trip_start_timestamp"].dt.hour  # 生成新列 hour
# 提取日期中的星期几（0=周一，6=周日）和小时数，生成新的特征列。

df["trip_start_timestamp"] = pd.to_datetime(df["trip_start_timestamp"])
# 将trip_start_timestamp列转换为pandas的日期时间格式，方便日期相关操作。

# 从 trip_start_timestamp 中提取星期几和小时

# 提取星期几（0=周一，6=周日）
df["dayofweek"] = df["trip_start_timestamp"].dt.dayofweek  # 生成新列 dayofweek


# 过滤掉 trip_total <= 3 的数据（总价太低可能异常）
df = df[df["trip_pricing_total"] > 3]

# trip_miles 限制在0到300英里之间，过滤异常里程
df = df[(df["trip_miles"] > 0) & (df["trip_miles"] < 300)]

# 行程时间至少2分钟
df = df[df["trip_seconds"] >= 120]

# 乘车时间最多2小时
df = df[df["trip_hours"] <= 2]

# 行驶速度限制在每小时70英里以内，剔除异常速度
df = df[df["trip_speed"] <= 70]

df = df[df["trip_pricing_total"] < 3000].reset_index(drop=True)
# 这行代码过滤掉目标变量 trip_total 超过3000的极端大值，防止异常值影响分析，
# 并且重置索引。

df = df[df["payment_type"].isin(["Credit Card", "Cash"])].reset_index(drop=True)
# 只保留付款方式为“Credit Card”或“Cash”的数据，排除其他付款方式的样本。

df["payment_type"] = df["payment_type"].apply(
    lambda x: 0 if x == "Credit Card" else (1 if x == "Cash" else None)
)
# 将付款方式编码为数字：Credit Card编码为0，Cash编码为1，
# 方便机器学习模型使用。

df["dayofweek"] = df["dayofweek"].apply(lambda x: 0 if x in [5, 6] else 1)
# 将星期几特征二值化：周末（星期六、星期日）编码为0，工作日编码为1。

df["hour"] = df["hour"].apply(lambda x: 0 if x in [23, 0, 1, 2, 3, 4, 5, 6, 7] else 1)
# 将小时特征二值化：深夜和凌晨时间段（23点到7点）编码为0，白天编码为1。

# -----------------------------
# 准备训练数据
# -----------------------------
cols = [
    "trip_seconds",             # 行程时间（秒）
    "trip_miles",               # 行程距离（英里）
    "payment_type",             # 付款方式（编码后）
    "pickup_community_area",    # 上车社区区域编号
    "dropoff_community_area",   # 下车社区区域编号
    "dayofweek",                # 星期几（0=工作日，1=周末）
    "hour",                     # 小时段（0=夜间，1=白天）
    "trip_speed",               # 平均速度（英里/小时）
]
# x = df[cols].copy()            # 选取这些特征列，作为模型输入
# y = df[target].copy()          # 目标变量（出租车行程总价）

# 原来的：
# x = df[cols].copy()            
# y = df[target].copy()          

# 修改为 numpy array，去掉列名依赖
x = df[cols].to_numpy()          
y = df[target].to_numpy() 
# 按75%训练集、25%测试集划分数据，random_state保证每次划分一致
X_train, X_test, y_train, y_test = train_test_split(
    x, y, train_size=0.75, test_size=0.25, random_state=13
)
X_train.shape, X_test.shape     # 查看训练集和测试集形状

# -----------------------------
# 训练模型（Ridge + GridSearchCV）
# -----------------------------
# <<< 新增：设置要搜索的超参数 alpha
# alpha 控制正则化强度：
#   - alpha 越小，越接近普通线性回归（可能过拟合）
#   - alpha 越大，惩罚越强，模型更简单（可能欠拟合）
"""超参数
param_grid = {"alpha": [0.01, 0.05, 0.1, 0.5, 1, 5, 10, 50, 100]}  # <<< 新增

# <<< 新增：GridSearchCV 自动搜索超参数
grid = GridSearchCV(
    Ridge(),                # 基础模型换成 Ridge
    param_grid=param_grid,  # 要搜索的超参数范围
    cv=5,                   # 交叉验证折数
    scoring="r2",           # 评分标准（这里用 R²）
    n_jobs=-1               # 并行运行（用所有CPU核）
)
grid.fit(X_train, y_train)

# <<< 新增：取最优模型（带最佳 alpha）
reg = grid.best_estimator_
print("Best alpha:", grid.best_params_)  # 输出找到的最佳超参数
"""
# # -----------------------------
# # 老的线性回归
# # -----------------------------
# reg = LinearRegression()        # 创建线性回归模型对象
# reg.fit(X_train, y_train)       # 用训练集训练模型
# # -----------------------------
# # 老的线性回归
# # -----------------------------

# -----------------------------
# 模型评估
# -----------------------------
# # 原来：
# reg = Ridge(alpha=1.0)

# # 改成最优 alpha：
# reg = Ridge(alpha=0.1)
reg = Ridge(alpha=args.alpha)       # alpha 可自行调整 移除本地训练超参数，采用vertex ai 训练超参数
reg.fit(X_train, y_train)   # <<< 一定要训练！
y_train_pred = reg.predict(X_train)  # 训练集预测值
train_score = r2_score(y_train, y_train_pred)  # 训练集R²得分
train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))  # 训练集RMSE

y_test_pred = reg.predict(X_test)    # 测试集预测值
test_score = r2_score(y_test, y_test_pred)     # 测试集R²得分
test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))    # 测试集RMSE

print("Train R2-score:", train_score, "Train RMSE:", train_rmse)  # 输出训练集性能
print("Test R2-score:", test_score, "Test RMSE:", test_rmse)      # 输出测试集性能

# -----------------------------
# 特征系数可视化
# -----------------------------
coef_df = pd.DataFrame({"col": cols, "coeff": reg.coef_})   # 创建系数表，列名和对应系数
coef_df.set_index("col").plot(kind="bar")                  # 画出特征系数的柱状图

# -----------------------------
# 保存模型并上传到 GCS
# -----------------------------
FILE_NAME = "model.pkl"
with open(FILE_NAME, "wb") as f:
    pickle.dump(reg, f, protocol=4)  # protocol=4 兼容性更好

BLOB_PATH = "taxicab_fare_prediction/"
BLOB_NAME = BLOB_PATH + FILE_NAME

bucket = storage.Client(project=PROJECT_ID,).bucket(BUCKET_URI.replace("gs://",""))
blob = bucket.blob(BLOB_NAME)
blob.upload_from_filename(FILE_NAME)
print(f"Model uploaded to {BUCKET_URI}/{BLOB_NAME}")