"""
RAG (Retrieval-Augmented Generation) 路由
提供向量检索和增强问答功能
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import httpx
import json

from ..services.vector_store import get_vector_store

router = APIRouter(prefix="/rag", tags=["RAG检索增强"])


# ============== 请求/响应模型 ==============

class AddChunksRequest(BaseModel):
    """添加文本块到向量库"""
    chunks: List[str]
    filename: str

class QueryRequest(BaseModel):
    """RAG 问答请求"""
    query: str
    top_k: Optional[int] = 5

class SourceItem(BaseModel):
    """来源片段"""
    content: str
    filename: str
    distance: Optional[float] = None

class QueryResponse(BaseModel):
    """RAG 问答响应"""
    answer: str
    sources: List[SourceItem]


# ============== 流式响应辅助函数 ==============

async def generate_streaming_response(prompt: str, model: str = "llama3:8b"):
    """生成流式响应"""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": True
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                        except json.JSONDecodeError:
                            continue
    except Exception as e:
        yield f"错误: {str(e)}"


# ============== API 路由 ==============

@router.post("/add", response_model=dict)
async def add_chunks(request: AddChunksRequest):
    """
    将文本块添加到向量库

    - **chunks**: 文本块列表
    - **filename**: 来源文件名
    """
    if not request.chunks:
        raise HTTPException(status_code=400, detail="chunks 不能为空")

    vector_store = get_vector_store()
    result = vector_store.add_documents(request.chunks, request.filename)

    return result


@router.post("/query", response_model=QueryResponse)
async def rag_query(request: QueryRequest):
    """
    RAG 问答：检索相关片段 + LLM 生成回答

    - **query**: 用户问题
    - **top_k**: 检索的相关片段数量（默认5）
    """
    vector_store = get_vector_store()

    # 1. 检索相关文档
    retrieved_docs = vector_store.search(request.query, top_k=request.top_k)

    # 2. 构建上下文
    if retrieved_docs:
        context_parts = []
        for i, doc in enumerate(retrieved_docs, 1):
            context_parts.append(f"[文档{i}] ({doc['filename']}):\n{doc['content']}")
        context = "\n\n".join(context_parts)

        prompt = f"""你是一个知识库问答助手。请根据以下参考资料回答用户的问题。
如果问题与参考资料相关，请基于参考资料回答；如果无关，你可以根据自己的知识回答。（但是务必用中文回答）

参考资料：
{context}

用户问题：{request.query}

请基于参考资料回答，如果参考资料中没有相关信息，请说明"根据提供的信息无法回答这个问题"。"""
    else:
        # 没有检索到相关文档
        prompt = f"""你是一个知识库问答助手。请回答用户的问题。

用户问题：{request.query}

注意：如果没有足够的信息来回答问题，请如实说明。"""

    # 3. 调用 LLM 生成回答
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3:8b",
                    "prompt": prompt,
                    "stream": False
                }
            )
            result = response.json()
            answer = result.get("response", "抱歉，暂时无法生成回答")
    except Exception as e:
        answer = f"抱歉，AI 服务暂时不可用：{str(e)}"

    # 4. 构建响应
    sources = [
        SourceItem(
            content=doc["content"],
            filename=doc["filename"],
            distance=doc.get("distance")
        )
        for doc in retrieved_docs
    ]

    return QueryResponse(answer=answer, sources=sources)


@router.post("/query/stream")
async def rag_query_stream(request: QueryRequest):
    """
    RAG 问答（流式）：检索相关片段 + LLM 流式生成回答

    - **query**: 用户问题
    - **top_k**: 检索的相关片段数量（默认5）
    """
    vector_store = get_vector_store()

    # 1. 检索相关文档
    retrieved_docs = vector_store.search(request.query, top_k=request.top_k)

    # 2. 构建上下文
    if retrieved_docs:
        context_parts = []
        for i, doc in enumerate(retrieved_docs, 1):
            context_parts.append(f"[文档{i}] ({doc['filename']}):\n{doc['content']}")
        context = "\n\n".join(context_parts)

        prompt = f"""你是一个知识库问答助手。请根据以下参考资料回答用户的问题。

参考资料：
{context}

用户问题：{request.query}

请基于参考资料回答，如果参考资料中没有相关信息，请说明"根据提供的信息无法回答这个问题"。"""
    else:
        # 没有检索到相关文档
        prompt = f"""你是一个知识库问答助手。请回答用户的问题。（用中文回答）

用户问题：{request.query}

注意：如果没有足够的信息来回答问题，请如实说明。"""

    # 3. 构建来源信息
    sources = [
        SourceItem(
            content=doc["content"],
            filename=doc["filename"],
            distance=doc.get("distance")
        )
        for doc in retrieved_docs
    ]

    # 4. 返回流式响应
    async def stream_generator():
        full_response = ""
        try:
            async for chunk in generate_streaming_response(prompt, "llama3:8b"):
                full_response += chunk
                # 发送 SSE 格式的数据
                yield f"data: {json.dumps({'token': chunk, 'done': False})}\n\n"

            # 流式结束后，发送完成信号
            yield f"data: {json.dumps({'token': '', 'done': True, 'sources': [s.dict() for s in sources]})}\n\n"

        except Exception as e:
            error_msg = f"错误: {str(e)}"
            yield f"data: {json.dumps({'token': error_msg, 'done': True, 'error': True})}\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/search")
async def search_docs(query: str, top_k: int = 5):
    """
    单纯检索文档（不调用 LLM）

    - **query**: 查询文本
    - **top_k**: 返回结果数量
    """
    vector_store = get_vector_store()
    results = vector_store.search(query, top_k=top_k)

    return {
        "query": query,
        "count": len(results),
        "results": results
    }


@router.get("/stats")
async def get_stats():
    """
    获取向量库统计信息
    """
    vector_store = get_vector_store()
    return vector_store.get_stats()


@router.delete("/clear")
async def clear_vector_store():
    """
    清空向量库（谨慎操作）
    """
    vector_store = get_vector_store()
    return vector_store.clear_all()


@router.delete("/file/{filename}")
async def delete_file_vectors(filename: str):
    """
    删除某个文件的所有向量

    - **filename**: 文件名
    """
    vector_store = get_vector_store()
    return vector_store.delete_by_filename(filename)
