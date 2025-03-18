import tiktoken
from .config import EMBEDDING_MODEL

def num_tokens_from_string(text: str, model_name: str = EMBEDDING_MODEL) -> int:
    """Calculates the number of tokens in a given text string based on the specified model's encoding."""
    encoding = tiktoken.encoding_for_model(model_name)
    return len(encoding.encode(text))

def to_roman(num):
    roman_map = {
        1: "I",
        4: "IV",
        5: "V",
        9: "IX",
        10: "X",
        40: "XL",
        50: "L",
        90: "XC",
        100: "C",
        400: "XD",
        500: "D",
        900: "CM",
        1000: "M",
    }
    i = 12
    result = ""
    for value, numeral in sorted(roman_map.items(), reverse=True):
        while num >= value:
            result += numeral
            num -= value
    return result

def roman_to_int(roman_num):
    """Chuyển số La Mã sang số thập phân để sắp xếp"""
    roman_values = {
        'I': 1,
        'V': 5,
        'X': 10,
        'L': 50,
        'C': 100,
        'D': 500,
        'M': 1000
    }
    
    total = 0
    prev_value = 0
    
    for char in reversed(roman_num):
        curr_value = roman_values[char]
        if curr_value >= prev_value:
            total += curr_value
        else:
            total -= curr_value
        prev_value = curr_value
        
    return total

import re
def clean_markdown(md_text):
    md_text = re.sub(r"[ \t]+$", "", md_text, flags=re.MULTILINE)

    md_text = re.sub(r"\n\s*\n+", "\n", md_text)

    return md_text