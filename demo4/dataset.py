from google.cloud.bigquery import Client
from google.oauth2 import service_account
import os
from dotenv import load_dotenv
import credentials as crets

# 1. 加载 .env 文件
load_dotenv()

bqclient = Client(
    project=os.getenv("PROJECT_ID"),
    location=os.getenv("LOCATION_BQ"),
    credentials=crets.GetCredentials(),
)

def CreateImportDataset(
        client: Client , project_id: str, dataset_id: str, table_id: str
):
    dataset = client.dataset(f"{project_id}.{dataset_id}")
    dataset = client.create_dataset(dataset=dataset_id,exists_ok=True)
    print(f"Dataset {dataset.dataset_id} created in {dataset.location}")

    query = f"""
    CREATE OR REPLACE TABLE `{project_id}.{dataset_id}.{table_id}` AS
    SELECT 
        taxi_id,
        trip_start_timestamp,
        trip_end_timestamp,  -- 加上这个字段
        trip_seconds,
        trip_miles,
        trip_total,
        payment_type,
        pickup_community_area,
        dropoff_community_area
    FROM `bigquery-public-data.chicago_taxi_trips.taxi_trips`
    WHERE 
        trip_start_timestamp >= '2018-05-12'
        AND trip_end_timestamp <= '2018-05-12'
        AND trip_seconds > 60 AND trip_seconds < 6*60*60
        AND trip_miles > 0
        AND trip_total > 3 AND trip_total IS NOT NULL
        AND pickup_community_area IS NOT NULL 
        AND dropoff_community_area IS NOT NULL
"""
    # 执行 SQL 创建新表
    job = client.query(query)
    job.result()  # 等待执行完成 
    print(f"✅ 数据已导入到 {project_id}.{dataset_id}.{table_id}")
    # ✅ 数据已导入到 genai-specialization-468108.kade_machine_learning.kade_taxi_trips

def QueryDataset(
    client: Client 
): 
    query = """select 
    taxi_id, trip_start_timestamp, 
    trip_seconds, trip_miles, trip_total, 
    payment_type, pickup_community_area, 
    dropoff_community_area 
    from `genai-specialization-468108.kade_machine_learning.kade_taxi_trips`
    where 
    trip_start_timestamp >= '2018-05-12' and 
    trip_end_timestamp <= '2018-05-17' and
    trip_seconds > 60 and trip_seconds < 6*60*60 and
    trip_miles > 0 and
    trip_total > 3 and
    pickup_community_area is not NULL and
    dropoff_community_area is not NULL"""

    # query = """select 
    # taxi_id, trip_start_timestamp, 
    # trip_seconds, trip_miles, trip_total, 
    # payment_type, pickup_community_area, 
    # dropoff_community_area 
    # from `bigquery-public-data.chicago_taxi_trips.taxi_trips`
    # where 
    # trip_start_timestamp >= '2018-05-12' and 
    # trip_end_timestamp <= '2018-05-18' and
    # trip_seconds > 60 and trip_seconds < 6*60*60 and
    # trip_miles > 0 and
    # trip_total > 3 and
    # pickup_community_area is not NULL and 
    # dropoff_community_area is not NULL"""

    job = client.query(query)  # 使用 BigQuery 客户端提交SQL查询任务
    df = job.to_dataframe()   # 将查询结果转成 Pandas DataFrame 方便数据分析

    print(df.shape)           # 输出数据维度（行数和列数）
    df.columns                # 查看DataFrame所有列名
    df.head()                 # 显示前5条数据，快速预览内容
    df.dtypes                 # 查看每列的数据类型
    df.info()                 # 输出DataFrame详细信息（非空值数量、类型、内存）
    df.describe().T           # 对数值列做统计描述并转置，方便查看均值、标准差等指标'
    return df


if __name__ == "__main__":
    CreateImportDataset(bqclient,os.getenv("PROJECT_ID"), os.getenv("DATASET_ID"), os.getenv("TABLE_ID"))
    # QueryDataset(bqclient) 