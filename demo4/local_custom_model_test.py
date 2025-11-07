import pickle
import pandas as pd

# 1️⃣ 加载模型
with open("model.pkl", "rb") as f:
    model = pickle.load(f)

# 2️⃣ 定义特征列（顺序必须和训练时一致）
feature_names = [
    "trip_seconds",
    "trip_miles",
    "payment_type",
    "pickup_community_area",
    "dropoff_community_area",
    "dayofweek",
    "hour",
    "trip_speed"
]

# 3️⃣ 构造单条样本（用 DataFrame 包装，带上列名）
sample = pd.DataFrame(
    [[6000, 4.2, 2, 18, 30, 10, 11, 129.2]],
    columns=feature_names
)

if not hasattr(model, "positive"):
    model.positive = False

# 4️⃣ 执行预测
prediction = model.predict(sample)[0]
print("预测结果:", prediction)

# 5️⃣ 打印每个特征对预测的贡献
print("\n每个特征的贡献:")
for name, coef, val in zip(feature_names, model.coef_, sample.iloc[0]):
    contrib = coef * val
    print(f"{name}: {val} * {coef:.4f} = {contrib:.4f}")

# 6️⃣ 验证预测值
intercept = model.intercept_
print("\n截距:", intercept)
print("预测值 = 截距 + 特征贡献之和 =", intercept + sum(sample.iloc[0]*model.coef_))

# {
#   "instances": [
#     [600, 2.5, 0, 8, 10, 1, 1, 30.0],
#     [1200, 5.0, 1, 12, 15, 0, 0, 25.0]
#   ]
# }