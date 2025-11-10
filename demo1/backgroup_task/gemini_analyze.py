import itertools
import json
import traceback
from json import JSONDecodeError

import vertexai
from vertexai.generative_models import SafetySetting, GenerativeModel, Part
from google.oauth2.service_account import Credentials

model_name = "gemini-1.5-pro-002"
credentials = Credentials.from_service_account_info({
    ...
})
project_id = "wonder-ai1"
region = "us-central1"
vertexai.init(project=project_id, location=region, credentials=credentials)
generation_config = {
    "max_output_tokens": 8192,
    "temperature": 0.5,
    "top_p": 0.9,
    # "top_p": 0.95,
}
safety_settings = [
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    ),
]

prompt = """角色：招聘专员，
    # 任务： 根据招聘的岗位信息，对即将输入的候选人的简历（主要有工作经历，项目经验、学校专业等）进行专业的评估，输出一个json的评估报告
    # 评估内容：
    重要前提： 评估简历存在大量的乱码、或者没有完整语句、或者无法获取到候选人的名称，则该候选人的匹配度为0
    候选人和岗位的匹配度， 输出百分数, 对应的key为suitability，范围为0-100
    获选人适配岗位的理由： 输出字符串, 对应的key为reason
    候选人在岗位上优势： 输出列表，对应的key为advantages
    候选人在岗位的劣势： 输出列表， 对应的key为disadvantages
    如果简历内容出现大量缺失(名字等个人信息、工作过的公司、工作经历、项目经验、等)， 则该候选人的匹配度为0
    简历提供的信息不完整信息（如名称、公司名称、岗位名称、工作内容等）， 则该候选人的匹配度为0
    返回结果的数据格式为列表，子项内容为：{"key"：简历id, "result": 评估结果}
    # 输出示例：
    {"key": "", "result": {"suitability": 50, "reason": "", "advantages": [], "disadvantages": []}}
    """

job_info = """
职位名称：商务销售代表/商务销售经理

岗位职责：
负责公司产品或服务的销售推广，开发新客户并维护现有客户关系；
根据公司销售目标，制定个人销售计划并完成业绩指标；
分析客户需求，提供专业解决方案，促成合作签约；
跟踪行业动态及竞争对手信息，及时反馈市场趋势；
参与商务谈判、合同签订及回款跟进；
协助市场部门策划推广活动，提升品牌影响力。

任职要求：
大专及以上学历，市场营销、商务管理、经济类相关专业优先；
具备X年以上销售经验，有[行业名称，如IT、医疗器械、快消品等]行业资源者优先；
优秀的沟通能力、谈判技巧及客户开发能力；
目标导向，抗压能力强，适应短期出差；
熟练使用Office办公软件及CRM系统。
"""

cvs = [
    {
        "cv_id": "6f7b983df30246c0bf1e66b1e56f0940",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/7d3173b40e924fc5a5f5fd3f2dd88ed7.pdf"
    },
    {
        "cv_id": "dd12070b13fe4979ad90fe43a1e01f61",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/be518833c78f41e484ff9f90b47dc03a.pdf"
    },
    {
        "cv_id": "8a6f0519c9254b608371d9d4509806f4",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/e637b292fe804859a7e3705763f33a2f.pdf"
    },
    {
        "cv_id": "c8a2e649c3f941709063a929834f353e",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/f92c199076a440d5852ae8420f34c11c.pdf"
    },
    {
        "cv_id": "efc2dd45396a4509ab5c162a64892ae5",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/cdbbf59a74104edb9ee5edc63bf39169.pdf"
    },
    {
        "cv_id": "454a6aaae8fa4c9a892d47d8bda87b55",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/65814e5e085842b797fa9b1ff486e160.pdf"
    },
    {
        "cv_id": "593187ff484546ddbb60f3dd18fd8ceb",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/a9b4c89c133f41ad8c8ec372d8b9c19c.pdf"
    },
    {
        "cv_id": "61d0775c36b943eabd600295d87de452",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/31816d360d84436fb9a32d960d852d8a.pdf"
    },
    {
        "cv_id": "67da30a4645d474cb14291aff1cfd8a1",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/c4db46b051604da7889a685cf3f27904.pdf"
    },
    {
        "cv_id": "3ff81b7f469442e48a6b18c2e7729348",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/e26775845722458c921fd8b5d000f787.pdf"
    },
    {
        "cv_id": "29892b89f4bf4d0bb0c1dfd95e0d2c90",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/075af9a3f43948c5b7441695aa1093eb.pdf"
    },
    {
        "cv_id": "7138128ea90b4caca6fed96821e692d9",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/2c55b589f17740ffa5457ac3c7281343.pdf"
    },
    {
        "cv_id": "24017e8312964ff5811b376d2dbe7cc6",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/440e877f606542dabf4dee9cdf12f7be.pdf"
    },
    {
        "cv_id": "ae5944a984054a0183c8851a60b32587",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/c702d4cde9e444b5a740c1802964d999.pdf"
    },
    {
        "cv_id": "8773b5eb12374780aa47afa88008b540",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/f8d2038a85074ec3a984b76f41f744e2.pdf"
    },
    {
        "cv_id": "2a4f005de804439d90966a513ec51768",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/a86b2d46da954134b2b5dae0d8dd2842.pdf"
    },
    {
        "cv_id": "af0b90992a2342469510ac4dd631c427",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/d82f7033407f46d9b152a66ee943e3fe.pdf"
    },
    {
        "cv_id": "567cf35f63fd4658bb781c47e00ae352",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/0cf3db38a6c54ac6a81d403491b5fb05.pdf"
    },
    {
        "cv_id": "cbb09c412f9e411cae1ad8dd6d9594eb",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/1bf93196507c43e496b31cc29e61e1e9.pdf"
    },
    {
        "cv_id": "27c6bce4e4584a78837e5ff068ff9675",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/0068cd520cbb4213a2858f7baee7c9a0.pdf"
    },
    {
        "cv_id": "48c7a4875bb242f190dba2d6a08e482a",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/a1cd1477e63442a4adefab8092b0d176.pdf"
    },
    {
        "cv_id": "349fb58c600541a384d39864f04aa1ab",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/e0f078a6e92a42acaa554094a67844bd.pdf"
    },
    {
        "cv_id": "0adba75aa48e4c4399c2743354361922",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/a4574d8016684565a0e3aef1f5e95faf.pdf"
    },
    {
        "cv_id": "12fd66679370401d878aa70dcdbdf26e",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/c23352c0d67d46ea8bf072b63f4fdcad.pdf"
    },
    {
        "cv_id": "e0b32ebf68a849a4b2cfae38dd8f51e6",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/0a9839dc3d1a49c093dc04f8a10e30a1.pdf"
    },
    {
        "cv_id": "28316b2b877e45a888e3e280b2524591",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/ae8b412e2ba94287bab180d4914a7f52.pdf"
    },
    {
        "cv_id": "8c66b2b198a940118b8ff7333093d709",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/a1086a4188d946419f72e4b3aa095f67.pdf"
    },
    {
        "cv_id": "21ca86ed33544576af5d6142b86240a6",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/98581a6707f642bf9d4d8daaba2d5d12.pdf"
    },
    {
        "cv_id": "1a1fad2e9e854d8d98fc00b373ccab18",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/2b9b3e41a4b44cbf8358a71c5c167ae3.pdf"
    },
    {
        "cv_id": "dbd143b1056c4a6f8347ed485c202b69",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/64c819d19d984d8e9f57f47b8cfda091.pdf"
    },
    {
        "cv_id": "d138de2473b54378bde1fde78d7e8042",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/a705c51a580a454cadc573799a92f01f.pdf"
    },
    {
        "cv_id": "d0ce846583c44563886dca79c50c6fab",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/f4b8d28fa5b748a6aa9dff21e26ba795.pdf"
    },
    {
        "cv_id": "e44f8ce0b7b4436babe6674f5fb894e1",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/85cdf3734fa94682b31fb7c0e0efc4f4.pdf"
    },
    {
        "cv_id": "417da3f281b24adaadc6684d57ba2cb4",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/53e5c6eb2be6457884e00f7e14db6c42.pdf"
    },
    {
        "cv_id": "fbebe1c74ab645f99544232cc2173de0",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/c764ce77fa4b460bbc1eb83abbfded07.pdf"
    },
    {
        "cv_id": "b26c4a308aa24355900693486b1d377e",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/60e28bd5fe604e7da03b340e3ac947c4.pdf"
    },
    {
        "cv_id": "6f0053f121a4486895f6ae9dac4e6afe",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/267823d0d49541eb8d475c7c8eeb7f90.pdf"
    },
    {
        "cv_id": "9b6b939ebd8b47818b521c7ef54afa86",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/3b226d752d5b4d68a35a9b403c537ce7.pdf"
    },
    {
        "cv_id": "bb2a5f16dca5423f9988fb5c9ff19469",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/da07a55bc1754852a2444feb7a0171a4.pdf"
    },
    {
        "cv_id": "aa045768a5744e9e84b686d2e9913ec9",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/1553a16b99144299a82731e4612f6c98.pdf"
    },
    {
        "cv_id": "29abb714dfd442abb3b3a4764327ea78",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/4ba5df16fbb94b59a1c4d8782e05b102.pdf"
    },
    {
        "cv_id": "f78f039b13564644b1056fbd4f586fda",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/3a8b4e374cc64ab4a75bce7ef104aa40.pdf"
    },
    {
        "cv_id": "38959a9cd90247a3bcc4684a00e6d919",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/30b795115c444bebab5fa3a020b04ce0.pdf"
    },
    {
        "cv_id": "644ef6d9732749bd84fa17623297cf8b",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/ef1cd62b244c4c89b77ec826a4abedbe.pdf"
    },
    {
        "cv_id": "2dc914fbbe2846658d9ed6ee6f60e682",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/c95ebff999cc4a6d9dbaa49b199af4e0.pdf"
    },
    {
        "cv_id": "15565f567b0c462aa32f5ad6a69ee0cb",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/5fb0b0a5fabb46f3a52d10e973ee7e23.pdf"
    },
    {
        "cv_id": "1672c262d5c943d5b34bb2baf0d34cc7",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/2d1e5d67f6344307943ccca9b48da9c5.pdf"
    },
    {
        "cv_id": "10dde540167b4fdea9c99164cd884224",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/6d21a3afd2dc4f24813d224d8a2bcb2e.pdf"
    },
    {
        "cv_id": "0e5103ba35a24e7abd52df5e7768fdc1",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/5afb03a1d9c549a4842b50f093a8c8ff.pdf"
    },
    {
        "cv_id": "45b7eb2e5aa843f08fda97b892bed0aa",
        "save_path": "gs://cvinfo/21a5aee70cae497990280904d0e775f8/4b156fba9d864542894035c9ff100d68.pdf"
    }
]

batch_global = 15


def batch_iterable(iterable, batch_size=batch_global):
    """每次从可迭代对象中取出 batch_size 个元素，直到取完"""
    iterator = iter(iterable)  # 确保传入的是迭代器
    while True:
        batch = list(itertools.islice(iterator, batch_size))
        if not batch:
            break  # 如果取不到数据，结束循环
        yield batch  # 返回当前批次（生成器模式）


def analyze_cv_single():
    generative_model = GenerativeModel(
        model_name,
        system_instruction=[prompt]
    )
    total_tokens_count = 0
    for cv in cvs:
        content = ["岗位信息\n{}".format(job_info)]
        content.append("\nID: {}, 简历:".format(cv["cv_id"]))
        content.append(Part.from_uri(mime_type="application/pdf", uri=cv["save_path"]))
        content.append("""\n请输出评估结果""")
        try:
            responses = generative_model.generate_content(
                content,
                generation_config=generation_config,
                safety_settings=safety_settings,
                stream=False,
            )
            total_tokens = responses.usage_metadata.total_token_count
            data = responses.candidates[0].content.parts[0].text
            total_tokens_count += total_tokens
            try:
                analytic_result = json.loads(data.replace("```json", "").replace("```", "").strip())
                print("Analytic single, use tokens count {}, result: {}...".format(total_tokens, str(analytic_result)[:120]))
            except JSONDecodeError:
                print("json数据结果解析异常")
                return False
        except Exception as e:
            print(traceback.format_exc())
            print(f"分析异常：{e}")

    print("Analyze count number: {}, use total tokens {}".format(len(cvs), total_tokens_count))


def analyze_cvs_batch():
    generative_model = GenerativeModel(
        model_name,
        system_instruction=[prompt]
    )
    total_tokens_count = 0
    for items in batch_iterable(cvs):
        content = ["岗位信息\n{}".format(job_info)]
        for item in items:
            content.append("\nID: {}, 简历:".format(item["cv_id"]))
            content.append(Part.from_uri(mime_type="application/pdf", uri=item["save_path"]))
        content.append("""\n请输出评估结果""")

        try:
            responses = generative_model.generate_content(
                content,
                generation_config=generation_config,
                safety_settings=safety_settings,
                stream=False,
            )
            total_tokens = responses.usage_metadata.total_token_count
            data = responses.candidates[0].content.parts[0].text
            total_tokens_count += total_tokens
            try:
                analytic_result = json.loads(data.replace("```json", "").replace("```", "").strip())
                print("Analytic batch {}, use tokens count {}, result: {}...".format(batch_global, total_tokens, str(analytic_result)[:120]))
            except JSONDecodeError:
                print("json数据结果解析异常")
                return False
            print(f"解析分析结果成功，数量：{len(analytic_result)}")
        except Exception as e:
            print(traceback.format_exc())
            print(f"分析异常：{e}")

    print("Analyze count number: {}, use total tokens {}".format(len(cvs), total_tokens_count))


def analyze_cvs(model=model_name):
    generative_model = GenerativeModel(
        model,
        system_instruction=[prompt]
    )
    result = []
    for items in batch_iterable(cvs):
        content = ["岗位信息\n{}".format(job_info)]
        for item in items:
            content.append("\nID: {}, 简历:".format(item["cv_id"]))
            content.append(Part.from_uri(mime_type="application/pdf", uri=item["save_path"]))
        content.append("""\n请输出评估结果""")

        try:
            print(f"Model name: {model}，开始分析简历匹配度，共分析简历{len(items)}份")
            responses = generative_model.generate_content(
                content,
                generation_config=generation_config,
                safety_settings=safety_settings,
                stream=False,
            )
            data = responses.candidates[0].content.parts[0].text
            try:
                analytic_result = json.loads(data.replace("```json", "").replace("```", "").strip())
                result.extend(analytic_result)
            except JSONDecodeError:
                print("json数据结果解析异常")
                return False
            print(f"解析分析结果成功，数量：{len(analytic_result)}")
            for i in analytic_result:
                print(f">>>>>: {i}")
        except Exception as e:
            print(traceback.format_exc())
            print(f"分析异常：{e}")

    with open(f"analyze_{model_name}.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)


# if __name__ == "__main__":
#     import argparse
#     arg_parser = argparse.ArgumentParser()
#     arg_parser.add_argument("--model_name", default=model_name, required=False)
#     args = arg_parser.parse_args()
#     model_name = args.model_name
#     analyze_cvs(model=model_name)


if __name__ == "__main__":
    analyze_cvs_batch()
