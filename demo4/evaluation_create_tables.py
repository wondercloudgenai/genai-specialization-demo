import datapreprocess as dp
import dataset as ds
from dotenv import load_dotenv
import os
from google.cloud import bigquery

load_dotenv()

df1=dp.PreprocessData()

# === 时间过滤 ===
# 假设你只想保留 2018-05-12 ~ 2018-05-12 之间的数据
df1 = df1[
    df1["trip_start_timestamp"].between("2018-05-12 10:14:58", "2018-05-12 10:15:00")
]

print("过滤后行数:", df1.shape[0])

# 随机选择 300 行索引删除
drop_idx = df1.sample(n=300, random_state=42).index
df = df1.drop(drop_idx)

print("保留后的行数:", len(df))

# 假设你已经有 df，这里只保留需要的列
keep_cols = [
    "trip_seconds",
    "trip_miles",
    "payment_type",
    "pickup_community_area",
    "dropoff_community_area",
    "dayofweek",
    "hour",
    "trip_speed",
    "trip_pricing_total",
]
df_new = df[keep_cols]
# df_new["explanation"] = None
# df_new['prediction'] = None  # 或者生成一些默认值

# BigQuery 客户端
client = ds.Client()
# 目标表
table_id = os.getenv("EVALUATION_CREATE_TABLE_BQ")
print(table_id)

# schema 可以省略（pandas 会自动推断），也可以显式定义
job_config = bigquery.LoadJobConfig(
    write_disposition="WRITE_TRUNCATE"  # 覆盖已有表
)

# 将 DataFrame 写入 BigQuery
job = client.load_table_from_dataframe(
    df_new, table_id, job_config=job_config
)
job.result()  # 等待完成

print(f"成功写入 {table_id}, 共 {df_new.shape[0]} 行数据")