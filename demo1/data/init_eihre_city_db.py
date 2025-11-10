import json
import uuid

import psycopg2

# 数据库连接参数

# 连接到数据库
connection = psycopg2.connect(
    host="localhost",
    user="postgres",
    password="vector",
    dbname="vector",
    port="5433",
)


def init_ehire_city_code():
    try:
        with connection.cursor() as cursor:
            with open("ehire_citys.json", mode="r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    label = item["name"]
                    sub = item["sub"]
                    for i in sub:
                        _id = uuid.uuid4().hex
                        name = i["name"]
                        ehire_code = i["id"]
                        p = {
                            "label": label,
                            "name": name,
                            "ehire_code": ehire_code,
                        }
                        cursor.execute("INSERT INTO v1_jd_zone (id, name, label, ehire_code) VALUES (%s, %s, %s, %s)",
                                       (_id, name, label, ehire_code))
                        print(f"{p} >>> 插入成功")

            # 提交事务
            connection.commit()
            # 查询数据
            cursor.execute("SELECT count(1) FROM v1_jd_zone")
            result = cursor.fetchall()
            print(f"插入数据{result}条")

    finally:
        connection.close()


def init_boss_city_code():
    try:
        with connection.cursor() as cursor:
            with open("boss_citys.json", mode="r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    label = item["name"]
                    sub = item["sub"]
                    for i in sub:
                        _id = uuid.uuid4().hex
                        name = i["name"]
                        boss_code = i["id"]
                        p = {
                            "label": label,
                            "name": name,
                            "boss_code": boss_code,
                        }
                        cursor.execute("update v1_jd_zone set boss_code = %s where label  = %s and name = %s;",
                                       (boss_code, label, name))
                        print(f"{p} >>> 插入成功")

            # 提交事务
            connection.commit()
            # 查询数据
            cursor.execute("SELECT count(1) FROM v1_jd_zone")
            result = cursor.fetchall()
            print(f"插入数据{result}条")

    finally:
        connection.close()


if __name__ == "__main__":
    init_boss_city_code()