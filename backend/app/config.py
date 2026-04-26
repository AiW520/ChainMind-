"""
配置文件
ChainMind - 本地知识库问答系统
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent.parent

# 数据目录
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
CHROMA_DIR = DATA_DIR / "chroma_db"

# 确保目录存在
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

# API配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b")

# RAG配置
DEFAULT_TOP_K = 3
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Embedding配置
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
