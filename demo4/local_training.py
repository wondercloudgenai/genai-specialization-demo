import datapreprocess as datep
# from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, root_mean_squared_error
import pandas as pd
# load the required libraries start
import pickle

# from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error  # <-- 修改这里
import numpy as np
# from sklearn.model_selection import train_test_split


# -----------------------------
# 修改这里：换成 Ridge 而不是 LinearRegression
# Ridge 回归支持超参数 alpha (正则化强度)
# -----------------------------
from sklearn.linear_model import Ridge                # <<< 修改 
from sklearn.model_selection import train_test_split, GridSearchCV  # <<< 修改（新增 GridSearchCV）

def train_model():
    
    df = datep.PreprocessData()

    target = "trip_pricing_total"

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

    y_train_pred = reg.predict(X_train)  # 训练集预测值
    train_score = r2_score(y_train, y_train_pred)  # 训练集R²得分
    train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))  # 训练集RMSE

    y_test_pred = reg.predict(X_test)    # 测试集预测值
    test_score = r2_score(y_test, y_test_pred)     # 测试集R²得分
    test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))    # 测试集RMSE

    print("Train R2-score:", train_score, "Train RMSE:", train_rmse)  # 输出训练集性能
    print("Test R2-score:", test_score, "Test RMSE:", test_rmse)      # 输出测试集性能

    coef_df = pd.DataFrame({"col": cols, "coeff": reg.coef_})   # 创建系数表，列名和对应系数
    coef_df.set_index("col").plot(kind="bar")                  # 画出特征系数的柱状图

    FILE_NAME = "model.pkl"         # 模型文件名
    with open(FILE_NAME, "wb") as file:
        pickle.dump(reg, file)      # 将训练好的模型序列化保存为文件

if __name__ == "__main__":
    # CreateImportDataset(bqclient,os.getenv("PROJECT_ID_Genai"), os.getenv("DATASET_ID"), os.getenv("TABLE_ID"))
    train_model() 