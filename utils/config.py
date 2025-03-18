LEAF_CHUNK_SIZE = 512
SECTION_CHUNK_SIZE = 1024
PARENT_CHUNK_SIZE = 8192

EMBEDDING_MODEL = "text-embedding-3-small"
RERANKER = "rerank-multilingual-v3.0"
TOP_K = 60
TOP_N = 3

REDIS_HOST = "127.0.0.1"
REDIS_PORT = "6379"
REDIS_NAMESPACE = "sdoctor_chatbot"
REDIS_DUMP_PATH = "/var/lib/redis/dump.rdb"

MILVUS_URL = "https://in03-df53926262ae58e.serverless.gcp-us-west1.cloud.zilliz.com"
MILVUS_COLLECTION_NAME = {"en": "en", "vi": "vi"}