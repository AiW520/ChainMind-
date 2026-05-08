"""
向量存储服务 v2.0
混合检索：向量检索 + BM25 + Rerank
"""
import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import uuid
import math
from collections import Counter


class BM25Index:
    """BM25检索器"""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents = []
        self.avgdl = 0
        self.doc_freqs = {}
        self.idf = {}
        self.doc_lengths = []

    def index(self, documents: List[Dict]):
        """构建BM25索引"""
        self.documents = documents
        self.doc_lengths = []
        self.doc_freqs = {}

        # 统计词频
        for doc in documents:
            content = doc['content'].lower()
            words = re.findall(r'\w+', content)
            self.doc_lengths.append(len(words))

            # 文档频率
            unique_words = set(words)
            for word in unique_words:
                self.doc_freqs[word] = self.doc_freqs.get(word, 0) + 1

        self.avgdl = sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 0

        # 计算IDF
        N = len(documents)
        for word, df in self.doc_freqs.items():
            self.idf[word] = math.log((N - df + 0.5) / (df + 0.5) + 1)

    def search(self, query: str, k: int = 10) -> List[Dict]:
        """BM25检索"""
        if not self.documents:
            return []

        query_words = re.findall(r'\w+', query.lower())
        if not query_words:
            return []

        scores = []
        for i, doc in enumerate(self.documents):
            score = self._calculate_score(query_words, i)
            scores.append((i, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [
            {
                **self.documents[idx],
                "bm25_score": score,
                "distance": 1.0 / (score + 1)
            }
            for idx, score in scores[:k] if score > 0
        ]

    def _calculate_score(self, query_words: List[str], doc_idx: int) -> float:
        """计算单个文档的BM25分数"""
        doc_content = self.documents[doc_idx]['content'].lower()
        doc_words = re.findall(r'\w+', doc_content)
        doc_len = self.doc_lengths[doc_idx]
        word_freqs = Counter(doc_words)

        score = 0.0
        for word in query_words:
            if word not in self.idf:
                continue

            freq = word_freqs.get(word, 0)
            if freq == 0:
                continue

            idf = self.idf[word]
            numerator = freq * (self.k1 + 1)
            denominator = freq + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
            score += idf * numerator / denominator

        return score


class SimpleVectorStore:
    """简化向量存储（基于词频相似度）"""

    def __init__(self):
        self.documents = []
        self.vocab = set()

    def add_documents(self, chunks: List[str], filename: str) -> Dict:
        """添加文档"""
        if not chunks:
            return {"status": "success", "count": 0}

        for chunk in chunks:
            words = set(re.findall(r'\w+', chunk.lower()))
            self.vocab.update(words)

            self.documents.append({
                "id": f"{filename}_{uuid.uuid4().hex[:8]}",
                "content": chunk,
                "filename": filename,
                "words": words,
                "word_count": len(words)
            })

        return {
            "status": "success",
            "count": len(chunks),
            "filename": filename,
            "total_docs": len(self.documents)
        }

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """向量相似度检索"""
        query_words = set(re.findall(r'\w+', query.lower()))
        if not query_words:
            return []

        scores = []
        for doc in self.documents:
            if not doc['words']:
                continue

            # 余弦相似度
            intersection = len(query_words & doc['words'])
            query_norm = math.sqrt(len(query_words))
            doc_norm = math.sqrt(doc['word_count'])

            if query_norm == 0 or doc_norm == 0:
                continue

            similarity = intersection / (query_norm * doc_norm)
            scores.append((doc, similarity))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [
            {
                "content": doc['content'],
                "filename": doc['filename'],
                "vector_score": sim,
                "distance": 1.0 / (sim + 0.1)
            }
            for doc, sim in scores[:top_k]
        ]

    def get_all_documents(self) -> List[Dict]:
        """获取所有文档"""
        return self.documents


class HybridRetriever:
    """混合检索器：向量 + BM25"""

    def __init__(self):
        self.vector_store = SimpleVectorStore()
        self.bm25_index = BM25Index()
        self._indexed = False

    def add_documents(self, chunks: List[str], filename: str) -> Dict:
        """添加文档并重建索引"""
        result = self.vector_store.add_documents(chunks, filename)
        self._rebuild_bm25_index()
        return result

    def _rebuild_bm25_index(self):
        """重建BM25索引"""
        docs = self.vector_store.get_all_documents()
        if docs:
            self.bm25_index.index(docs)
            self._indexed = True

    def search(
        self,
        query: str,
        top_k: int = 5,
        vector_weight: float = 0.6,
        bm25_weight: float = 0.4
    ) -> List[Dict]:
        """混合检索"""
        if not self._indexed:
            self._rebuild_bm25_index()

        # 向量检索
        vector_results = {
            r['content']: r for r in self.vector_store.search(query, top_k * 2)
        }

        # BM25检索
        bm25_results = {
            r['content']: r for r in self.bm25_index.search(query, top_k * 2)
        }

        # 归一化分数
        max_vector_score = max((r['vector_score'] for r in vector_results.values()), default=1)
        max_bm25_score = max((r['bm25_score'] for r in bm25_results.values()), default=1)

        # 合并结果
        all_contents = set(vector_results.keys()) | set(bm25_results.keys())
        combined_scores = []

        for content in all_contents:
            vector_score = vector_results.get(content, {}).get('vector_score', 0)
            bm25_score = bm25_results.get(content, {}).get('bm25_score', 0)

            # 归一化
            norm_vector = vector_score / max_vector_score if max_vector_score > 0 else 0
            norm_bm25 = bm25_score / max_bm25_score if max_bm25_score > 0 else 0

            # 混合分数
            hybrid_score = vector_weight * norm_vector + bm25_weight * norm_bm25

            combined_scores.append({
                "content": content,
                "filename": vector_results.get(content, {}).get('filename') or bm25_results.get(content, {}).get('filename', 'unknown'),
                "vector_score": vector_score,
                "bm25_score": bm25_score,
                "hybrid_score": hybrid_score,
                "distance": 1.0 / (hybrid_score + 0.1)
            })

        # 按混合分数排序
        combined_scores.sort(key=lambda x: x['hybrid_score'], reverse=True)
        return combined_scores[:top_k]


class Reranker:
    """结果重排序器（基于更精细的匹配）"""

    def __init__(self):
        pass

    def rerank(
        self,
        query: str,
        documents: List[Dict],
        top_k: int = 5
    ) -> List[Dict]:
        """重排序"""
        if not documents:
            return []

        query_words = set(re.findall(r'\w+', query.lower()))

        scored_docs = []
        for doc in documents:
            content = doc['content'].lower()
            content_words = set(re.findall(r'\w+', content))

            # 计算各项指标
            exact_matches = sum(1 for w in query_words if w in content_words)

            # 词序一致性（n-gram重叠）
            query_bigrams = set(zip(query_words, query_words))
            content_bigrams = set(zip(content_words, content_words))
            bigram_overlap = len(query_bigrams & content_bigrams) / max(len(query_bigrams), 1)

            # 位置评分（查询词在文档中的位置）
            position_score = 0
            for i, word in enumerate(query_words):
                if word in content_words:
                    position_score += 1.0 / (i + 1)

            # 综合评分
            final_score = (
                exact_matches * 2.0 +
                bigram_overlap * 1.5 +
                position_score * 0.5 +
                doc.get('hybrid_score', 0) * 1.0
            )

            scored_docs.append({
                **doc,
                "rerank_score": final_score,
                "exact_matches": exact_matches,
                "bigram_overlap": round(bigram_overlap, 3)
            })

        scored_docs.sort(key=lambda x: x['rerank_score'], reverse=True)
        return scored_docs[:top_k]


class VectorStore:
    """向量存储类，提供高级检索功能"""

    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        self.hybrid_retriever = HybridRetriever()
        self.reranker = Reranker()
        self.query_count = 0
        self.hit_count = 0

    def add_documents(self, chunks: List[str], filename: str) -> Dict:
        """添加文档"""
        return self.hybrid_retriever.add_documents(chunks, filename)

    def search(
        self,
        query: str,
        top_k: int = 5,
        use_rerank: bool = True,
        use_hybrid: bool = True
    ) -> List[Dict]:
        """检索文档"""
        self.query_count += 1

        if use_hybrid:
            results = self.hybrid_retriever.search(query, top_k * 2 if use_rerank else top_k)
        else:
            results = self.hybrid_retriever.vector_store.search(query, top_k * 2 if use_rerank else top_k)

        if use_rerank and results:
            results = self.reranker.rerank(query, results, top_k)
            self.hit_count += 1

        return results

    def delete_by_filename(self, filename: str) -> Dict:
        """删除文件的所有向量"""
        original_count = len(self.hybrid_retriever.vector_store.documents)
        self.hybrid_retriever.vector_store.documents = [
            doc for doc in self.hybrid_retriever.vector_store.documents
            if doc['filename'] != filename
        ]
        self.hybrid_retriever._rebuild_bm25_index()
        deleted_count = original_count - len(self.hybrid_retriever.vector_store.documents)

        return {
            "status": "success",
            "deleted_count": deleted_count
        }

    def get_stats(self) -> Dict:
        """获取统计信息"""
        docs = self.hybrid_retriever.vector_store.documents
        total_count = len(docs)

        filename_counts = {}
        for doc in docs:
            fname = doc.get('filename', 'unknown')
            filename_counts[fname] = filename_counts.get(fname, 0) + 1

        hit_rate = self.hit_count / max(self.query_count, 1)

        return {
            "status": "success",
            "total_vectors": total_count,
            "files": filename_counts,
            "query_count": self.query_count,
            "hit_rate": round(hit_rate, 3),
            "rerank_enabled": True,
            "hybrid_search_enabled": True
        }

    def clear_all(self) -> Dict:
        """清空存储"""
        self.hybrid_retriever.vector_store.documents = []
        self.hybrid_retriever.vector_store.vocab = set()
        self.hybrid_retriever._indexed = False
        return {"status": "success", "message": "存储已清空"}


_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """获取全局向量存储实例"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
