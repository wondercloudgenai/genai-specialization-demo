import csv
import json

# import pypandoc
import os

import jsonlines


def convert_with_pandoc(pdf_dirpath, output_file):
    """使用pypandoc将PDF转换为Markdown。"""
    if not os.path.exists(pdf_dirpath):
        print(f"错误: 路径 '{pdf_dirpath}' 不存在。")
        return

    with open(output_file, "w", encoding="utf-8") as f:
        for filename in os.listdir(pdf_dirpath):
            if not filename.endswith(".pdf"):
                continue
            filepath = os.path.join(pdf_dirpath, filename)
            try:
                # 核心转换命令
                # format='pdf' 告诉pandoc输入是pdf，'gfm'是一种流行的markdown方言（GitHub Flavored Markdown）
                output = pypandoc.convert_file(filepath, 'gfm', format='pdf')
                print(f"{filename}转换成功！")
                f.write(output + "\n")

            except Exception as e:
                print(f"转换失败: {e}")


def aaa():
    def bbb(item):
        return {
            "contents": [
                {"role": "user", "parts": [{"texts": item["input_text"]}]},
                {"role": "model", "parts": [{"texts": item["output_text"]}]},
            ]
        }

    with open("finetune_data_train.jsonl", "r", encoding="utf-8") as f:
        n = 0
        r1, r2, r3, r4 = [], [], [], []
        for line in f.readlines():
            finetune_data = json.loads(line)
            item = bbb(finetune_data)
            if n < 210:
                r1.append(item)
            elif n < 240:
                r2.append(item)
            else:
                r3.append(item)
            n += 1
        with jsonlines.open("finetune_data_train_0830.jsonl", "w") as writer:
            writer.write_all(r1)
        with jsonlines.open("finetune_data_validation_0830.jsonl", "w") as writer:
            writer.write_all(r2)
        with jsonlines.open("finetune_data_test_0830.jsonl", "w") as writer:
            writer.write_all(r3)


def covert_jsonl2csv(input_file, output_file):
    r = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f.readlines():
            line = line.strip()
            data = json.loads(line)
            input_text = data["contents"][0]["parts"][0]["texts"]
            output_text = data["contents"][1]["parts"][0]["texts"]
            r.append((input_text, output_text))

    headers = ["input_text", "output_text"]

    # 3. 写入TSV文件
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as tsvfile:
            # 创建一个写入器，并指定分隔符为制表符（\t）
            writer = csv.writer(tsvfile, delimiter='\t')

            # 写入表头
            writer.writerow(headers)

            # 遍历所有数据并写入每一行
            for row in r:
                writer.writerow(row)
        print("转化成功")
    except Exception as e:
        print("转化失败，{}".format(e))


if __name__ == '__main__':
    covert_jsonl2csv("finetune_data_test.jsonl", "finetune_data_train.csv")
