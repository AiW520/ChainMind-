"""
向量存储服务
使用内存存储实现向量存储和检索（简化版）
"""
import os
from pathlib import Path
from typing import List, Dict, Optional
import uuid


class VectorStore:
    """向量存储类，提供文档存储和检索功能"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        初始化向量存储
        
        Args:
            persist_directory: 持久化目录
        """
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        
        # 使用内存存储
        self.documents = []
    
    def add_documents(self, chunks: List[str], filename: str) -> Dict:
        """
        将文本块添加到存储
        
        Args:
            chunks: 文本块列表
            filename: 来源文件名
        
        Returns:
            添加结果
        """
        if not chunks:
            return {"status": "success", "count": 0}
        
        # 添加到内存
        for chunk in chunks:
            self.documents.append({
                "id": f"{filename}_{uuid.uuid4().hex[:8]}",
                "content": chunk,
                "filename": filename
            })
        
        return {
            "status": "success",
            "count": len(chunks),
            "filename": filename
        }
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        检索最相关的文本块（简单字符串匹配）
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
        
        Returns:
            相关文档列表，每项包含 content, filename, distance
        """
        # 简单的字符串匹配
        results = []
        for doc in self.documents:
            # 计算简单的匹配分数
            score = sum(1 for word in query.lower().split() if word in doc['content'].lower())
            if score > 0:
                results.append({
                    "content": doc['content'],
                    "filename": doc['filename'],
                    "distance": 1.0 / (score + 1)  # 分数越高，距离越小
                })
        
        # 按距离排序并返回前top_k个
        results.sort(key=lambda x: x['distance'])
        return results[:top_k]
    
    def delete_by_filename(self, filename: str) -> Dict:
        """
        删除某个文件的所有记录
        
        Args:
            filename: 文件名
        
        Returns:
            删除结果
        """
        original_count = len(self.documents)
        self.documents = [doc for doc in self.documents if doc['filename'] != filename]
        deleted_count = original_count - len(self.documents)
        
        return {
            "status": "success",
            "deleted_count": deleted_count
        }
    
    def get_stats(self) -> Dict:
        """
        获取存储统计信息
        
        Returns:
            统计信息
        """
        total_count = len(self.documents)
        
        # 按文件名统计
        filename_counts = {}
        for doc in self.documents:
            fname = doc.get('filename', 'unknown')
            filename_counts[fname] = filename_counts.get(fname, 0) + 1
        
        return {
            "status": "success",
            "total_vectors": total_count,
            "files": filename_counts
        }
    
    def clear_all(self) -> Dict:
        """
        清空存储
        
        Returns:
            操作结果
        """
        self.documents = []
        return {"status": "success", "message": "存储已清空"}


# 全局单例向量存储实例
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """获取全局向量存储实例"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
