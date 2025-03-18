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
        "level1": "",     # CHƯƠNG
        "level2": "",     # x.y (previously level 3)
        "level3": "",     # x.y.z (previously level 4)
        "level4": ""      # Bước (previously level 5)
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

        # CHƯƠNG (Level 1)
        if re.search(r'^\s*(?:\*\*)?(?:Chương|CHƯƠNG)\s+[IVX]+[^*]*(?:\*\*)?$', line, re.IGNORECASE):
            save_current_chunk()
            current_headings["level1"] = line
            current_headings["level2"] = ""
            current_headings["level3"] = ""
            current_headings["level4"] = ""
            roman_numeral = get_roman_number(line)
            current_chunk_id = f"C{roman_numeral}"
            current_chunk_content = line + "\n"

        # Level 2 (previously level 3) - x.y format
        elif re.search(r'^\s*(?:\*\*)?(?:\d+\.\d+)[^*]*(?:\*\*)?$', line):
            content_buffer = line + "\n"
            current_headings["level2"] = line
            current_headings["level3"] = ""
            current_headings["level4"] = ""
            section_num = re.search(r'(?:\d+\.\d+)', line).group(0)
            j = i + 1
            
            while j < len(lines):
                next_line = lines[j].rstrip()
                if (re.search(r'^\s*(?:\*\*)?(?:Chương|CHƯƠNG)\s+[IVX]+[^*]*(?:\*\*)?$', next_line) or
                    re.search(r'^\s*(?:\*\*)?(?:\d+\.\d+)[^*]*(?:\*\*)?$', next_line) or
                    re.search(r'^\s*(?:\*\*)?(?:\d+\.\d+\.\d+)[^*]*(?:\*\*)?$', next_line) or
                    re.search(r'^\s*(?:\*\*)?Bước\s+\d+\s*:', next_line)):
                    break
                if next_line:
                    content_buffer += next_line + "\n"
                j += 1

            if should_split_chunk(current_chunk_content + content_buffer):
                save_current_chunk()
                current_chunk_id = f"C{get_roman_number(current_headings['level1'])}.S{section_num.replace('.', '_')}"
                current_chunk_content = current_headings["level1"] + "\n" + content_buffer
            else:
                current_chunk_content += content_buffer
            i = j - 1

        # Level 3 (previously level 4) - x.y.z format
        elif re.search(r'^\s*(?:\*\*)?(?:\d+\.\d+\.\d+)[^*]*(?:\*\*)?$', line):
            content_buffer = line + "\n"
            current_headings["level3"] = line
            current_headings["level4"] = ""
            subsection_num = re.search(r'(?:\d+\.\d+\.\d+)', line).group(0)
            j = i + 1
            
            while j < len(lines):
                next_line = lines[j].rstrip()
                if (re.search(r'^\s*(?:\*\*)?(?:Chương|CHƯƠNG)\s+[IVX]+[^*]*(?:\*\*)?$', next_line) or
                    re.search(r'^\s*(?:\*\*)?(?:\d+\.\d+)[^*]*(?:\*\*)?$', next_line) or
                    re.search(r'^\s*(?:\*\*)?(?:\d+\.\d+\.\d+)[^*]*(?:\*\*)?$', next_line) or
                    re.search(r'^\s*(?:\*\*)?Bước\s+\d+\s*:', next_line)):
                    break
                if next_line:
                    content_buffer += next_line + "\n"
                j += 1

            if should_split_chunk(current_chunk_content + content_buffer):
                save_current_chunk()
                section_num = re.search(r'(?:\d+\.\d+)', current_headings["level2"]).group(0)
                current_chunk_id = f"C{get_roman_number(current_headings['level1'])}.S{section_num.replace('.', '_')}.SS{subsection_num.replace('.', '_')}"
                current_chunk_content = (current_headings["level1"] + "\n" + 
                                      current_headings["level2"] + "\n" + 
                                      content_buffer)
            else:
                current_chunk_content += content_buffer
            i = j - 1

        # Level 4 (Bước format) section
        elif re.search(r'^\s*(?:\*\*)?Bước\s+\d+\s*:', line):
            content_buffer = line + "\n"
            current_headings["level4"] = line
            step_num = int(re.search(r'Bước\s+(\d+)\s*:', line).group(1))
            j = i + 1
            
            while j < len(lines):
                next_line = lines[j].rstrip()
                if (re.search(r'^\s*(?:\*\*)?(?:Chương|CHƯƠNG)\s+[IVX]+[^*]*(?:\*\*)?$', next_line) or
                    re.search(r'^\s*(?:\*\*)?(?:\d+\.\d+)[^*]*(?:\*\*)?$', next_line) or
                    re.search(r'^\s*(?:\*\*)?(?:\d+\.\d+\.\d+)[^*]*(?:\*\*)?$', next_line) or
                    re.search(r'^\s*(?:\*\*)?Bước\s+\d+\s*:', next_line)):
                    break
                if next_line:
                    content_buffer += next_line + "\n"
                j += 1
        
            if should_split_chunk(current_chunk_content + content_buffer):
                save_current_chunk()
                # Add error handling for missing parent sections
                try:
                    section_num = re.search(r'(?:\d+\.\d+)', current_headings["level2"]).group(0)
                except (AttributeError, KeyError):
                    section_num = "0.0"  # Default value if section number is missing
                    
                try:
                    subsection_num = re.search(r'(?:\d+\.\d+\.\d+)', current_headings["level3"]).group(0)
                except (AttributeError, KeyError):
                    subsection_num = "0.0.0"  # Default value if subsection number is missing
        
                # Build chunk ID with available information
                chunk_id_parts = []
                chunk_id_parts.append(f"C{get_roman_number(current_headings['level1']) or 'I'}")
                
                if section_num != "0.0":
                    chunk_id_parts.append(f"S{section_num.replace('.', '_')}")
                
                if subsection_num != "0.0.0":
                    chunk_id_parts.append(f"SS{subsection_num.replace('.', '_')}")
                
                chunk_id_parts.append(f"B{step_num}")
                
                current_chunk_id = ".".join(chunk_id_parts)
                
                # Build content with available headings
                content_parts = []
                if current_headings["level1"]:
                    content_parts.append(current_headings["level1"])
                if current_headings["level2"]:
                    content_parts.append(current_headings["level2"])
                if current_headings["level3"]:
                    content_parts.append(current_headings["level3"])
                content_parts.append(content_buffer)
                
                current_chunk_content = "\n".join(content_parts)
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
    path = r'D:\\Phong\\Python\\LLM\\Tailieu\\Tailieu\\QT.NS.15_ XLKL_ Quy trình xử lý kỷ luật.docx'
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