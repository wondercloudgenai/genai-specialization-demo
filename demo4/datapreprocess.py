import matplotlib.pyplot as plt
import dataset as ds
import seaborn as sns
# load the required libraries
import pandas as pd
# pip install --upgrade seaborn 需要升级到Successfully installed seaborn-0.13.2
import warnings


def PreprocessData():
    
    df = ds.QueryDataset(ds.bqclient)

    # 你要做一个机器学习任务，目标是预测 trip_pricing_total （出租车行程总费用），这个字段就是你的目标变量（target）。
    target = "trip_pricing_total"
        # •	payment_type（付款类型，比如现金、信用卡等）
        # •	pickup_community_area（上车地点所在社区区域编号）
        # •	dropoff_community_area（下车地点所在社区区域编号）
    categ_cols = ["payment_type", "pickup_community_area", "dropoff_community_area"]
        # •	trip_seconds（行程时间，单位是秒）
        # •	trip_miles（行程距离，单位是英里）
    num_cols = ["trip_seconds", "trip_miles"]


        # •	直方图（Histogram）：看数据的分布情况，比如集中在哪些值，是否偏斜，是否有多峰等。
        # •	箱线图（Boxplot）：看数据的分布情况和异常值（离群点）。
    df = df.rename(columns={"trip_total": "trip_pricing_total"})
    # 遍历数值型特征列 + 目标列
    for i in num_cols + [target]:
        print("Plotting histogram for column: ", df[i])
        # 创建一个 1 行 2 列的图像区域（figsize=(12, 4) 表示整个图宽 12 英寸，高 4 英寸）
        _, ax = plt.subplots(1, 2, figsize=(12, 4))
        
        # 绘制直方图（Histogram）
        df[i].plot(kind="hist", bins=100, ax=ax[0])  # bins=100 表示分成 100 个柱子
        ax[0].set_title(str(i) + " -Histogram")     # 设置直方图标题
        
        # 绘制箱型图（Boxplot）
        df[i].plot(kind="box", ax=ax[1])             # 直接在右侧子图画箱线图
        ax[1].set_title(str(i) + " -Boxplot")        # 设置箱型图标题
        
        # 显示当前图像
        plt.show()


    # trip_seconds 是行程时间，单位是秒。为了分析更方便，把它换算成小时：
    df["trip_hours"] = round(df["trip_seconds"] / 3600, 2)
    # 画出这个新列的箱线图（box plot），可以看出行程时间的分布情况和异常值
    df["trip_hours"].plot(kind="box")
    plt.show()
        
    # 用里程数除以小时数，得到平均速度（英里/小时）：
    df["trip_speed"] = round(df["trip_miles"] / df["trip_hours"], 2)
    # 同样画箱线图查看速度的分布和异常值。
    df["trip_speed"].plot(kind="box")
    plt.show()

    # 在 pandas 里直接用 rename 就行：
    df = df.rename(columns={"trip_total": "trip_pricing_total"})
    # generate a pairplot for 200K samples
    # 用 Seaborn 的 pairplot，随机抽样21万条数据，画出几个数值变量之间的两两关系散点图矩阵：
    try:
        sns.pairplot(
            # trip_seconds（行程时间）和 trip_miles（行程里程）是线性相关的（一般时间越长，距离越远）
            # 这两个变量和目标变量 trip_total（行程总价）也有一定的关系
            data=df[["trip_seconds", "trip_miles", "trip_pricing_total", "trip_speed"]].sample(
                218656
            )
        )
        plt.show()
    except Exception as e:
        print("error")
        warnings.filterwarnings("ignore")
        print(e)
        
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

    # 重置索引
    df.reset_index(drop=True, inplace=True)
    # 查看过滤后数据的形状（行数，列数）
    print(df.shape)

    # 对分类列循环，打印类别数量，画出类别比例柱状图
    # 遍历所有类别型特征列
    for i in categ_cols:
        # 打印当前列的唯一值数量
        print(f"Unique values in {i}:", df[i].nunique())
        # 计算当前列每个取值的占比（normalize=True 表示返回比例而不是数量）
        # 并画柱状图
        df[i].value_counts(normalize=True).plot(kind="bar", figsize=(10, 4))
        # 给图加标题（当前列名）
        plt.title(i)
        # 显示图形
        plt.show()

    # 再次遍历所有类别型特征列
    for i in categ_cols:
        # 创建新的画布，指定大小
        plt.figure(figsize=(10, 4))
        # 绘制箱型图（x轴是类别特征列，y轴是目标变量 target）
        sns.boxplot(x=i, y=target, data=df)
        # 将 x 轴标签旋转 45 度，避免文字重叠
        plt.xticks(rotation=45)
        # 给图加标题
        plt.title(i)
        # 显示图形
        plt.show()

    # 这段代码是对分类变量（categ_cols 中的列）分别画箱线图（boxplot）。
    # 箱线图显示不同类别对应的目标变量（trip_total）的分布情况，
    # 可以帮助我们观察不同类别之间目标变量的差异和异常值。

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

    df["trip_start_timestamp"] = pd.to_datetime(df["trip_start_timestamp"])
    # 将trip_start_timestamp列转换为pandas的日期时间格式，方便日期相关操作。

    # 从 trip_start_timestamp 中提取星期几和小时

    # 提取星期几（0=周一，6=周日）
    df["dayofweek"] = df["trip_start_timestamp"].dt.dayofweek  # 生成新列 dayofweek

    # 提取小时（0~23）
    df["hour"] = df["trip_start_timestamp"].dt.hour  # 生成新列 hour
    # 提取日期中的星期几（0=周一，6=周日）和小时数，生成新的特征列。

    # 创建一个 1 行 2 列的绘图区（ax 是包含两个子图对象的数组）
    _, ax = plt.subplots(1, 2, figsize=(10, 4))

    # 按 dayofweek 分组，计算 trip_pricing_total 的总和，并在第一个子图 ax[0] 绘制柱状图
    df.groupby("dayofweek")["trip_pricing_total"].sum().plot(
        kind="bar", ax=ax[0]
    )
    ax[0].set_title("Sum of trip_pricing_total")  # 设置第一个子图的标题

    # 按 dayofweek 分组，计算 trip_pricing_total 的平均值，并在第二个子图 ax[1] 绘制柱状图
    df.groupby("dayofweek")["trip_pricing_total"].mean().plot(
        kind="bar", ax=ax[1]
    )
    ax[1].set_title("Avg. of trip_pricing_total")  # 设置第二个子图的标题

    plt.show()
    # 这部分代码绘制按星期几聚合的 trip_total 总和和平均值的柱状图，
    # 用于观察不同星期几的业务量和平均消费情况。

    # 创建一个 1 行 2 列的绘图区（ax 是两个子图对象）
    _, ax = plt.subplots(1, 2, figsize=(10, 4))

    # 按小时分组，计算 trip_pricing_total 的总和
    df.groupby("hour")["trip_pricing_total"].sum().plot(kind="bar", ax=ax[0])
    ax[0].set_title("Sum of trip_pricing_total")  # 设置第一个子图标题

    # 按小时分组，计算 trip_pricing_total 的平均值
    df.groupby("hour")["trip_pricing_total"].mean().plot(kind="bar", ax=ax[1])
    ax[1].set_title("Avg. of trip_pricing_total")  # 设置第二个子图标题


    # 显示绘制的所有图表
    plt.show()

    df["dayofweek"] = df["dayofweek"].apply(lambda x: 0 if x in [5, 6] else 1)
    # 将星期几特征二值化：周末（星期六、星期日）编码为0，工作日编码为1。

    df["hour"] = df["hour"].apply(lambda x: 0 if x in [23, 0, 1, 2, 3, 4, 5, 6, 7] else 1)
    # 将小时特征二值化：深夜和凌晨时间段（23点到7点）编码为0，白天编码为1。

    df.describe().T
    # 对整个数据框（DataFrame）做统计描述，显示各列的计数、均值、标准差、最小值、25%、50%、75%分位数和最大值，
    # 帮助快速了解数据的整体分布和范围。
    print(df.columns.tolist())
    return df

if __name__ == "__main__":
    PreprocessData()