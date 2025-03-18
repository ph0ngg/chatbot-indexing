from llama_index.core import (
    ServiceContext,
    VectorStoreIndex,
    SimpleDirectoryReader
)
from llama_index.vector_stores.milvus import MilvusVectorStore
from pymilvus import connections
from chunking import recursive_chunk_markdown_with_token_limit
import sys, os
from docx import Document

# sys.path.append(r'D:\\Phong\\Python\\LLM\\indexing\\final\\utils')
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.convert_docx_to_md_simple import convert_word_to_markdown_simple
from utils.helper import num_tokens_from_string




def data_processing(documents):
    for chunk_id, chunk_content in documents.items():
        token_count =  num_tokens_from_string(chunk_content)
        new_documents = Document(
            text = chunk_content,
            metadata = {'chunk_id': chunk_id, 'token_count': token_count}
        )
    return new_documents

# Kết nối Milvus local
connections.connect(alias='default', host='localhost', port='19530')

# Khởi tạo MilvusVectorStore
milvus_store = MilvusVectorStore(
    collection_name="document_chunks",
    uri="http://localhost:19530",   # URI chạy local
    dim=384                        # Kích thước vector embedding (phù hợp với mô hình đang dùng)
)

# Tạo ServiceContext
uri = "http://localhost:19530"
vector_store = MilvusVectorStore(
    uri = uri,
    token = None, 
    collection_name= "vi",
    enable_sparse=True,
    hybrid_ranker="RRFRanker",
    overwrite=True,
    dim=384,
)

# Load dữ liệu từ file
# documents = SimpleDirectoryReader("./documents").load_data()
path = r'"D:\\Phong\\Python\\LLM\\1. Tài liệu hành chính nhân sự-20250317T040824Z-001\\1. Tài liệu hành chính nhân sự\\1. Tài liệu chi tiết\\Chính sách phúc lợi sức khỏe cho CBNV.docx"'
md = convert_word_to_markdown_simple(path)
documents = recursive_chunk_markdown_with_token_limit(md, 1024)

service_context = ServiceContext.from_defaults(embed_model = 'sentence-transformers/all-MiniLM-L6-v2')

# Tạo index từ dữ liệu
index = VectorStoreIndex.from_documents(
    data_processing(documents), 
    vector_store=milvus_store,
    service_context=service_context
)

# Lưu index vào Milvus
index.storage_context.persist()

# Truy vấn thử
query_engine = index.as_query_engine()
response = query_engine.query("Quy trình xử lý kỷ luật của công ty là gì?")
print(response)