import os
import sys
import regex as re
from typing import List, Dict, Optional, Tuple

from llama_index.core.schema import RelatedNodeInfo, NodeRelationship, TextNode
from langchain_text_splitters.character import _split_text_with_regex

# from convert_docx_to_md import convert_word_to_markdown_v2
from utils.convert_docx_to_md_simple import convert_word_to_markdown_simple
# from sep import SEPS, DEFAULT_SEPS
from utils.helper import num_tokens_from_string, to_roman
from utils.config import SECTION_CHUNK_SIZE, PARENT_CHUNK_SIZE
import nltk
from nltk.tokenize import RegexpTokenizer

custom_tokenizer = RegexpTokenizer(r'[^\n]+\n*')
# def custom_tokenizer(text):

def should_split_chunk(content: str) -> bool:
    """
    Kiểm tra xem một đoạn văn bản có cần được tách thành chunk riêng không.
    
    Args:
        content (str): Nội dung cần kiểm tra
        
    Returns:
        bool: True nếu cần tách chunk, False nếu không
    """
    # Đếm số token trong nội dung
    token_count = num_tokens_from_string(content)
    
    # So sánh với giới hạn token cho phép
    return token_count > SECTION_CHUNK_SIZE

def chunk_markdown(markdown_content):
    chunks = {}
    current_chunk_id = ""
    current_chunk_content = ""
    
    current_headings = {
        "level1": "",  # For A., B.
        "level2": "",  # For Chương I., Chương II.
        "level3": "",  # For Điều 1:, Điều 2:
        "level4": ""   # For 1., 2.
    }

    def clean_heading(text):
        return text.strip()

    def get_roman_number(text):
        match = re.search(r'(?:Chương|CHƯƠNG)\s+([IVX]+)', text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def save_current_chunk():
        nonlocal current_chunk_id, current_chunk_content
        if current_chunk_id and current_chunk_content:
            chunks[current_chunk_id] = current_chunk_content.strip()

    lines = markdown_content.strip().split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].rstrip()
        if not line:
            i += 1
            continue

        # Level 1: A., B.
        if re.search(r'^(?:\*\*)?([A-Z])\.(?:\*\*)?(?:\s+|$)', line):
            save_current_chunk()
            current_headings["level1"] = line
            current_headings["level2"] = ""
            current_headings["level3"] = ""
            current_headings["level4"] = ""
            letter = re.search(r'^(?:\*\*)?([A-Z])\.', line).group(1)
            current_chunk_id = f"L{letter}"
            current_chunk_content = line + "\n"

        # Level 2: CHƯƠNG I., CHƯƠNG II.
        elif re.search(r'^(?:\*\*)?(?:Chương|CHƯƠNG)\s+[IVX]+\.?(?:[^*]*)?(?:\*\*)?$', line, re.IGNORECASE):
            save_current_chunk()
            current_headings["level2"] = line
            current_headings["level3"] = ""
            current_headings["level4"] = ""
            roman_numeral = get_roman_number(line)
            letter = re.search(r'^(?:\*\*)?([A-Z])\.', current_headings["level1"]).group(1) if current_headings["level1"] else ""
            current_chunk_id = f"L{letter}.C{roman_numeral}"
            current_chunk_content = current_headings["level1"] + "\n" + line + "\n"

        # Level 3: Điều 1:, Điều 2:
        elif re.search(r'^(?:\*\*)?Điều\s+\d+:(?:[^*]*)?(?:\*\*)?$', line):
            content_buffer = line + "\n"
            current_headings["level3"] = line
            current_headings["level4"] = ""
            j = i + 1
            
            article_num = int(re.search(r'Điều\s+(\d+)', line).group(1))
            
            while j < len(lines):
                next_line = lines[j].rstrip()
                if (re.search(r'^(?:\*\*)?[A-Z]\.(?:\*\*)?(?:\s+|$)', next_line) or
                    re.search(r'^(?:\*\*)?(?:Chương|CHƯƠNG)\s+[IVX]+\.?', next_line) or
                    re.search(r'^(?:\*\*)?Điều\s+\d+:', next_line) or
                    re.search(r'^(?:\*\*)?(?:\d+\.)', next_line)):
                    break
                if next_line:
                    content_buffer += next_line + "\n"
                j += 1

            if should_split_chunk(current_chunk_content + content_buffer):
                save_current_chunk()
                letter = re.search(r'^(?:\*\*)?([A-Z])\.', current_headings["level1"]).group(1) if current_headings["level1"] else ""
                roman_numeral = get_roman_number(current_headings["level2"])
                current_chunk_id = f"L{letter}.C{roman_numeral}.D{article_num}"
                current_chunk_content = (
                    current_headings["level1"] + "\n" +
                    current_headings["level2"] + "\n" +
                    content_buffer
                )
            else:
                current_chunk_content += content_buffer
            i = j - 1

        # Level 4: 1., 2.
        elif re.search(r'^(?:\*\*)?(?:\d+\.)(?:[^*]*)?(?:\*\*)?$', line):
            content_buffer = line + "\n"
            current_headings["level4"] = line
            section_num = re.search(r'^(?:\*\*)?(\d+)\.', line).group(1)
            j = i + 1
            
            while j < len(lines):
                next_line = lines[j].rstrip()
                if (re.search(r'^(?:\*\*)?[A-Z]\.(?:\*\*)?(?:\s+|$)', next_line) or
                    re.search(r'^(?:\*\*)?(?:Chương|CHƯƠNG)\s+[IVX]+\.?', next_line) or
                    re.search(r'^(?:\*\*)?Điều\s+\d+:', next_line) or
                    re.search(r'^(?:\*\*)?(?:\d+\.)', next_line)):
                    break
                if next_line:
                    content_buffer += next_line + "\n"
                j += 1

            if should_split_chunk(current_chunk_content + content_buffer):
                save_current_chunk()
                letter = re.search(r'^(?:\*\*)?([A-Z])\.', current_headings["level1"]).group(1) if current_headings["level1"] else ""
                roman_numeral = get_roman_number(current_headings["level2"])
                article_num = int(re.search(r'Điều\s+(\d+)', current_headings["level3"]).group(1))
                current_chunk_id = f"L{letter}.C{roman_numeral}.D{article_num}.S{section_num}"
                current_chunk_content = (
                    current_headings["level1"] + "\n" +
                    current_headings["level2"] + "\n" +
                    current_headings["level3"] + "\n" +
                    content_buffer
                )
            else:
                current_chunk_content += content_buffer
            i = j - 1

        else:
            current_chunk_content += line + "\n"

        i += 1

    save_current_chunk()
    return chunks

def recursive_split_chunk(chunk_id, chunk_content, max_tokens_per_chunk):
    token_count = num_tokens_from_string(chunk_content)
    if token_count <= max_tokens_per_chunk:
        return {chunk_id: chunk_content}

    sub_chunks = {}
    sentences = custom_tokenizer.tokenize(chunk_content)
    current_sub_chunk_content = ""
    sub_chunk_counter = 1

    # Lấy tất cả các heading từ nội dung
    headers = []
    for line in chunk_content.split('\n'):
        if re.match(r'^\s*(?:\*\*)?(?:[\d.]+|CHƯƠNG|Điều)\s*', line):
            headers.append(line.strip())

    # Thêm headers vào đầu mỗi sub-chunk
    headers_text = '\n'.join(headers) + '\n' if headers else ""

    for sentence in sentences:
        sentence = sentence.rstrip()
        if not sentence:
            continue

        # Bỏ qua câu nếu nó là một trong các header
        if any(header.strip() == sentence.strip() for header in headers):
            continue

        sentence_with_newline = sentence + "\n"
        if num_tokens_from_string(headers_text + current_sub_chunk_content + sentence_with_newline) <= max_tokens_per_chunk:
            current_sub_chunk_content += sentence_with_newline
        else:
            if current_sub_chunk_content:
                sub_chunk_id = f"{chunk_id}.{sub_chunk_counter}"
                sub_chunk_content = headers_text + current_sub_chunk_content.rstrip()

                sub_chunks.update(
                    recursive_split_chunk(
                        sub_chunk_id,
                        sub_chunk_content,
                        max_tokens_per_chunk,
                    )
                )
                sub_chunk_counter += 1

            current_sub_chunk_content = sentence_with_newline

    if current_sub_chunk_content:
        sub_chunk_id = f"{chunk_id}.{sub_chunk_counter}"
        sub_chunk_content = headers_text + current_sub_chunk_content.rstrip()

        sub_chunks.update(
            recursive_split_chunk(
                sub_chunk_id,
                sub_chunk_content,
                max_tokens_per_chunk,
            )
        )

    return sub_chunks

def recursive_chunk_markdown_with_token_limit(markdown_content, max_tokens_per_chunk=1024):
    """
    Chia markdown thành chunk theo heading và đệ quy chia nhỏ nếu vượt quá token limit.
    """
    initial_chunks = chunk_markdown(markdown_content) # Chia chunk ban đầu theo heading
    final_chunks = {}
    for chunk_id, chunk_content in initial_chunks.items():
        final_chunks.update(
            recursive_split_chunk(chunk_id, chunk_content, max_tokens_per_chunk)
        ) # Đệ quy chia nhỏ các chunk ban đầu nếu cần
    return final_chunks

if __name__ == "__main__":
    # Chia chunk nội dung với recursive chunking và token limit
    path = r'D:\\Phong\\Python\\LLM\\1. Tài liệu hành chính nhân sự-20250317T040824Z-001\\1. Tài liệu hành chính nhân sự\\1. Tài liệu chi tiết\\00A. FM_Quy định chấm công ( bản mềm đã duyệt từ 04.11.2021).docx'
    md = convert_word_to_markdown_simple(path)
    print(md)
    # md = """ """
    final_chunks = recursive_chunk_markdown_with_token_limit(md, SECTION_CHUNK_SIZE)

    # In các chunk đã được chia để kiểm tra
    print(len(final_chunks))
    for i, (chunk_id, content) in enumerate(final_chunks.items()):
        token_count = num_tokens_from_string(content)
        print(f"Chunk ID: {i} (Tokens: {token_count})") # In kèm số token
        print("Content:\n", content)
        print("-" * 50)