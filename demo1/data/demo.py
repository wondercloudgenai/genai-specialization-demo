import csv
import json
import random


def sss(n):
    with open("sss.jsonl", "r", encoding="utf8") as f:
        r = []
        for line in f.readlines():
            item = json.loads(line)
            item["_id"] = f"doc{n}"
            r.append(item)
            n += 1
        for i in r:
            print(i)


def bbb():
    docs_ids = set()
    with open("embedding_docs_corpus0819.jsonl", "r", encoding="utf8") as f:
        for i in f.readlines():
            item = json.loads(i)
            docs_ids.add(item["_id"])
    print(docs_ids)

    queries_ids = set()
    with open("embedding_queries0819.jsonl", "r", encoding="utf8") as f:
        for i in f.readlines():
            item = json.loads(i)
            queries_ids.add(item["_id"])
    print(queries_ids)


    with open("docs_queries_label.jsonl", "r", encoding="utf8") as f:
        train_labels = []
        test_labels = []
        validation_labels = []
        for i in f.readlines():
            item = json.loads(i.strip(","))
            q_id, c_id, score = item["query-id"], item["corpus-id"], item["score"]
            if q_id not in queries_ids:
                print(f"不存在q_id,{item}")
                continue
            if c_id not in docs_ids:
                print(f"不存在c_id,{item}")
                continue
            if score not in [0, 1, 2, 3]:
                print("score不正确")
                continue
            train_labels.append(item)
        test_labels = random.sample(train_labels, k=120)
        validation_labels = random.sample(train_labels, k=120)
        for i in test_labels:
            train_labels.remove(i)
        for i in validation_labels:
            if i in train_labels:
                train_labels.remove(i)

    headers = list(test_labels[0].keys())
    with open("embedding_docs_queries_label0819_train.tsv", 'w', newline='', encoding='utf-8') as tsvfile:
        # 创建一个写入器，并指定分隔符为制表符（\t）
        writer = csv.writer(tsvfile, delimiter='\t')

        # 写入表头
        writer.writerow(headers)

        # 遍历所有数据并写入每一行
        for row_dict in train_labels:
            # 按照表头的顺序提取字典中的值
            row_to_write = [row_dict[h] for h in headers]
            writer.writerow(row_to_write)

    print(f"数据成功写入到文件: train")

    with open("embedding_docs_queries_label0819_test.tsv", 'w', newline='', encoding='utf-8') as tsvfile:
        # 创建一个写入器，并指定分隔符为制表符（\t）
        writer = csv.writer(tsvfile, delimiter='\t')

        # 写入表头
        writer.writerow(headers)

        # 遍历所有数据并写入每一行
        for row_dict in test_labels:
            # 按照表头的顺序提取字典中的值
            row_to_write = [row_dict[h] for h in headers]
            writer.writerow(row_to_write)

    print(f"数据成功写入到文件: test")

    with open("embedding_docs_queries_label0819_validation.tsv", 'w', newline='', encoding='utf-8') as tsvfile:
        # 创建一个写入器，并指定分隔符为制表符（\t）
        writer = csv.writer(tsvfile, delimiter='\t')

        # 写入表头
        writer.writerow(headers)

        # 遍历所有数据并写入每一行
        for row_dict in validation_labels:
            # 按照表头的顺序提取字典中的值
            row_to_write = [row_dict[h] for h in headers]
            writer.writerow(row_to_write)

    print(f"数据成功写入到文件: validation")
