"""
文档处理服务
功能：从各类文档（PDF、TXT、MD）中提取文本，并切分成小块
"""
import os
from pathlib import Path
from typing import List

def load_document(file_path: str, file_extension: str) -> str:
    """
    根据文件类型加载文档
    
    Args:
        file_path: 文件路径
        file_extension: 文件扩展名（.txt, .md, .pdf）
    
    Returns:
        文档文本内容
    """
    if file_extension == ".txt" or file_extension == ".md":
        # 直接读取文本文件
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    elif file_extension == ".pdf":
        # 使用 pypdf 读取 PDF
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    
    else:
        raise ValueError(f"不支持的文件类型: {file_extension}")


def split_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
    """
    将长文本切分成小块
    
    Args:
        text: 要切分的文本
        chunk_size: 每个块的最大字符数
        chunk_overlap: 相邻块之间的重叠字符数
    
    Returns:
        切分后的文本块列表
    """
    chunks = []
    start = 0
    
    while start < len(text):
        # 计算当前块的结束位置
        end = start + chunk_size
        
        # 如果不是最后一块，尝试在句子边界处切割
        if end < len(text):
            # 往后查找最后一个换行符或句子结束符
            for sep in ['\n\n', '\n', '。', '！', '？', '. ', '! ', '? ']:
                last_sep = text.rfind(sep, start, end)
                if last_sep > start:
                    end = last_sep + len(sep)
                    break
        
        # 提取当前块
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # 移动起始位置（考虑重叠）
        start = end - chunk_overlap
        if start <= 0:
            start = end
    
    return chunks


def process_document(file_path: str) -> dict:
    """
    处理单个文档：加载 + 切分
    
    Args:
        file_path: 文件路径
    
    Returns:
        包含文档信息的字典
    """
    file_path = Path(file_path)
    file_extension = file_path.suffix.lower()
    
    # 加载文档
    text = load_document(str(file_path), file_extension)
    
    # 切分文档
    chunks = split_text(text)
    
    return {
        "file_name": file_path.name,
        "file_size": os.path.getsize(file_path),
        "total_chars": len(text),
        "total_chunks": len(chunks),
        "chunks": chunks
    }
