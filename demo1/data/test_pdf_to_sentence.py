import re

import PyPDF2

# 打开PDF文件
with open('大客户销售经理-张先生.pdf', 'rb') as file:
    reader = PyPDF2.PdfReader(file)
    text = ''

    # 提取每一页的文本
    for page in reader.pages:
        text += page.extract_text()
    print(text)
    split_texts = re.split(r"[,，。、\s\t/]", str(text))
    r = [i.strip() for i in split_texts if i and len(i) >= 2]
    print(r)
