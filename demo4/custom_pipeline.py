import credentials as cred
import dataset as ds
import os
import datapreprocess as dp
import local_training as tr
import uploadgcs as ul
import modelupload as mu
import createEndpoint as ce
import deployEndpoint as de
import custom_job as cj


def RemotePipeline():
    print("RemotePipeline")
    # 先执行这个函数，拿到最优的超参数，然后在训练模型
    min_value = cj.CustomJobHyperparameterTuningJob()
    # min_value=0.31622776601683789
    # 1.自动化部署 训练完自动上传到gcs
    cj.CustomJob(min_value)
    # 2.注册模型+创建端点+部署端点
    model_resource_name = mu.ModelUpLoad()
    endpoint_resource_name = ce.CreateEndpoint()
    de.DeployEndpoint(model_resource_name,endpoint_resource_name)


# 如果不想分步骤，可以直接跑main.py
def LocalPipeline():
    print("LocalPipeline")
    # # 1. 认证
    # credentials = cred.GetCredentials()
    # # 2.数据准备
    # # 2.1 数据导入
    # ds.CreateImportDataset(ds.bqclient,os.getenv("PROJECT_ID"), os.getenv("DATASET_ID"), os.getenv("TABLE_ID"))
    # # 2.2 数据查询
    # ds.QueryDataset(ds.bqclient)
    # # 3.数据处理 //前面三个执行后，只需要执行下面，上面的无需单独执行
    # dp.PreprocessData()
    # 4.模型训练
    tr.train_model()
    # 5.上传模型到gcs
    ul.UploadGCS()
    # 6.模型注册
    model_resource_name = mu.ModelUpLoad()
    # 7.创建端点
    endpoint_resource_name = ce.CreateEndpoint()
    # 8.部署端点
    de.DeployEndpoint(model_resource_name,endpoint_resource_name)

def ModelEvaluationPipeline():
    print("ModelEvaluationPipeline")
    cj.CustomEvaluationJob()

def ModelEvaluationMetricsPipeline():
    print("ModelEvaluationMetricsPipeline")
    cj.CustomEvaluationMetricsJob()


if __name__ == "__main__":
    # RemotePipeline()
    # LocalPipeline()
    ModelEvaluationPipeline()
    # ModelEvaluationMetricsPipeline()