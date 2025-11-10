import os
import re
import typing

import fitz  # 导入PyMuPDF，其包名为fitz
import tiktoken
from typing import List, Dict

# --- 全局设置 ---
TOKENIZER = tiktoken.get_encoding("cl100k_base")


def process_resume_pdf(
        pdf_path: str = "",
        pdf_stream: typing.Union[bytes] = None,
        chunk_size: int = 512,
        chunk_overlap: int = 64
) -> List[Dict[str, any]]:
    """
    使用PyMuPDF进行布局感知解析，然后进行智能语义切片，确保不切断句子。

    Args:
        pdf_path (str): PDF文件的路径.
        pdf_stream (bytes): PDF文件流.
        chunk_size (int): 每个文本块的【目标】token大小.
        chunk_overlap (int): 相邻文本块之间重叠的【目标】token数量.

    Returns:
        List[Dict[str, any]]: 高质量的、有意义的文本块列表。
    """
    if pdf_path and not os.path.exists(pdf_path):
        print(f"错误：文件不存在于路径 '{pdf_path}'")
        return []

    print(f"--- 开始使用 PyMuPDF 智能解析PDF文件: {pdf_path} ---")

    try:
        # 1. & 2. PDF解析与文本提取 (这部分逻辑保持不变)
        if pdf_stream is None and pdf_path:
            doc = fitz.open(pdf_path)
        else:
            doc = fitz.open(stream=pdf_stream)
        full_text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            full_text += page.get_text("text")
            full_text += "\n\n"
        full_text = re.sub(r'\n+', ' ', full_text).strip()
        full_text = re.sub(r'\s+', ' ', full_text).strip()

    except Exception as e:
        print(f"使用PyMuPDF解析PDF时发生错误: {e}")
        return []

    if not full_text:
        print("解析后无有效文本内容。")
        return []

    print("PDF解析完成，开始进行智能文本切片...")
    all_tokens = TOKENIZER.encode(full_text)
    total_tokens = len(all_tokens)
    print(f"清理后总Token数: {total_tokens}")

    # 定义句子分隔符。增加了中文标点和换行符，使其更通用。
    sentence_endings = {".", "!", "?", "。", "！", "？", "\n", "\n\n", ":"}

    chunks = []
    start = 0
    while start < total_tokens:
        # 确定一个大致的结束位置
        end = min(start + chunk_size, total_tokens)

        # 如果 end 不是文档的末尾，我们尝试找到一个更好的、语义上的结束位置
        if end < total_tokens:
            # 从目标 end 位置开始向前回溯，寻找最近的句子结尾
            # 我们设置一个回溯的搜索范围，比如 chunk_size 的 1/3，避免切出太小的块
            search_start = max(start, end - chunk_size // 3)

            # 在 token 级别上找到最后的分隔符位置
            best_end = -1
            # 从后往前遍历token
            for i in range(end, search_start, -1):
                # 解码单个token，检查是否是分隔符
                token_text = TOKENIZER.decode([all_tokens[i]])
                if token_text.strip() in sentence_endings:
                    best_end = i + 1  # 找到分隔符，切片应包含它
                    break

            # 如果在回溯范围内找到了合适的分隔符，就用它作为结束位置
            if best_end != -1:
                end = best_end

        # 提取最终的文本块
        chunk_tokens = all_tokens[start:end]
        chunk_text = TOKENIZER.decode(chunk_tokens)

        # 过滤掉太短或无意义的片段
        if len(chunk_text.strip()) > 50:
            chunks.append(chunk_text.strip())

        # 更新下一个窗口的起始位置
        next_start = start + chunk_size - chunk_overlap
        # 如果我们因为语义切分导致当前块很短，确保窗口依然能前进
        if end >= next_start:
            # 如果当前切片终点已经超过了预期的下一个起点，就从当前终点减去重叠部分开始
            next_start = end - chunk_overlap

        # 再次确保窗口前进，避免死循环
        if next_start <= start:
            start += 1
        else:
            start = next_start

    # 4. 格式化最终输出 (这部分逻辑保持不变)
    final_chunks = []
    for i, text in enumerate(chunks):
        final_chunks.append({
            "text": text,
            "chunk_id": f"chunk-{i}",
            "token_count": len(TOKENIZER.encode(text))
        })

    print(f"切片完成，共生成 {len(final_chunks)} 个高质量文本块。")
    return final_chunks


# --- 使用示例 ---
if __name__ == "__main__":
    pdf_file_path = "test.pdf"

    with open(pdf_file_path, "rb") as f:
        pdf_stream = f.read()
        sliced_chunks = process_resume_pdf(
            pdf_stream=pdf_stream,
            chunk_size=350,
            chunk_overlap=50
        )

    print("\n--- 最终高质量切片结果预览 ---")
    if sliced_chunks:
        for chunk in sliced_chunks:
            print(chunk)
            print("-" * 30)
    else:
        print("未能生成任何有效的文本块。")
