from google.cloud import aiplatform
from dotenv import load_dotenv
import os
import credentials as cred
import datapreprocess as data
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import pandas as pd

load_dotenv()
df=data.PreprocessData()
# print(df)
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

target = "trip_pricing_total"
x = df[cols].copy()            # 选取这些特征列，作为模型输入
y = df[target].copy()          # 目标变量（出租车行程总价）

# 按75%训练集、25%测试集划分数据，random_state保证每次划分一致
X_train, X_test, y_train, y_test = train_test_split(
    x, y, train_size=0.75, test_size=0.25, random_state=13
)
test_json = {"instances": [X_test.iloc[0].tolist(), X_test.iloc[1].tolist()]}  
# 准备两个测试样本（测试集的前两条），转换成列表格式，作为请求payload

def plot_attributions(attrs):
    """
    接受特征归因值，绘制条形图表示各特征的重要性
    """
    rows = {"feature_name": [], "attribution": []}
    for i, val in enumerate(features):  
        rows["feature_name"].append(val)  
        rows["attribution"].append(attrs["Input_feature"][i])  
    attr_df = pd.DataFrame(rows).set_index("feature_name")  
    attr_df.plot(kind="bar")  
    plt.show()  
    return

features = X_train.columns.to_list()  
# 获取训练集的特征名称列表

def explain_tabular_sample(
    project: str, location: str, endpoint_id: str, instances: list  
):
    """
    调用Vertex AI端点，发送预测请求并获取特征归因解释结果，打印并绘制
    """
    aiplatform.init(project=project, location=location, credentials=cred.GetCredentials(),)  
    # 初始化客户端
    endpoint = aiplatform.Endpoint(endpoint_id)
    response = endpoint.explain(instances=instances)  
    # 调用端点explain方法，传入测试样本，返回解释和预测结果

    print("#" * 10 + "Explanations" + "#" * 10)  
    for explanation in response.explanations:  
        print(" explanation")  
        attributions = explanation.attributions  # 取出归因信息

        for attribution in attributions:  
            print("  attribution")  
            print("   baseline_output_value:", attribution.baseline_output_value)  
            print("   instance_output_value:", attribution.instance_output_value)  
            print("   output_display_name:", attribution.output_display_name)  
            print("   approximation_error:", attribution.approximation_error)  
            print("   output_name:", attribution.output_name)  
            output_index = attribution.output_index  
            for output_index in output_index:  
                print("   output_index:", output_index)  

            plot_attributions(attribution.feature_attributions)  
            # 绘制该样本的特征归因条形图

    print("#" * 10 + "Predictions" + "#" * 10)  
    for prediction in response.predictions:  
        print(prediction)  
        # 打印模型预测结果

    return response

test_json = [X_test.iloc[0].tolist(), X_test.iloc[1].tolist()]  
# 准备测试样本列表格式

prediction = explain_tabular_sample(os.getenv("PROJECT_ID"), os.getenv("LOCATION"), os.getenv("ENDPOINT_ID"), test_json)  
# 调用解释函数，发送请求，获得并打印解释及预测

# ##########Explanations##########
#  explanation
#   attribution
#    baseline_output_value: 3.8885688650039567 基线预测值，比如模型在没有输入特征时的默认输出（类似“起点”）。
#    instance_output_value: 7.835568915449318  当前样本模型的预测值。
#    output_display_name: 模型输出的可读名称，这里是空的。
#    approximation_error: 1.0767001030476328e-18  归因计算的近似误差，越小越好，表明解释结果准确。
#    output_name: Predicted_taxi_fare   模型输出的名字，这里是 Predicted_taxi_fare，即出租车费用预测
#    output_index: -1
#  explanation
#   attribution
#    baseline_output_value: 3.8885688650039567
#    instance_output_value: 12.469287764089437
#    output_display_name: 
#    approximation_error: 3.860452983579596e-19
#    output_name: Predicted_taxi_fare
#    output_index: -1
# ##########Predictions##########
# 7.835568915449318
# 12.46928776408944