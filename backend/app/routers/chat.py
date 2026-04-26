from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import httpx
import json
import asyncio

from ..services.vector_store import get_vector_store

router = APIRouter(prefix="/chat", tags=["聊天"])

# 模拟的对话历史
chat_history = {}

# AI 对话 API 数据模型设计
class ChatRequest(BaseModel):
    question: str
    session_id: str = "default"
    use_rag: bool = True  # 是否启用 RAG 增强
    top_k: int = 3  # RAG 检索数量


class SourceItem(BaseModel):
    content: str
    filename: str
    distance: Optional[float] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceItem]
    used_rag: bool

#  Ollama 本地模型 API 交互的流式响应生成器
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


async def chat_with_rag(request: ChatRequest):
    """带RAG增强的聊天"""
    vector_store = get_vector_store()
    retrieved_docs = vector_store.search(request.question, top_k=request.top_k)

    sources = []
    if retrieved_docs:
        context_parts = []
        for i, doc in enumerate(retrieved_docs, 1):
            context_parts.append(f"[文档{i}] ({doc['filename']}):\n{doc['content']}")
        context = "\n\n".join(context_parts)

        prompt = f"""你是一个知识库问答助手。请根据以下参考资料回答用户的问题。
如果问题与参考资料相关，请基于参考资料回答；如果无关，你可以根据自己的知识回答。（但是务必用中文回答）

参考资料：
{context}

用户问题：{request.question}

回答："""

        sources = [
            SourceItem(
                content=doc["content"],
                filename=doc["filename"],
                distance=doc.get("distance")
            )
            for doc in retrieved_docs
        ]
    else:
        prompt = f"你是一个知识库问答助手，请回答用户的问题。（用中文回答）\n\n问题：{request.question}"

    return prompt, sources


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    聊天问答接口
    支持 RAG 增强：从向量库检索相关文档，作为上下文回答
    """
    # 1. 如果启用 RAG，先检索相关文档
    prompt = None
    sources = []
    used_rag = False

    if request.use_rag:
        try:
            prompt, sources = await chat_with_rag(request)
            used_rag = True
        except Exception as e:
            prompt = f"你是一个知识库问答助手，请回答用户的问题。（用中文回答）\n\n问题：{request.question}"
    else:
        prompt = f"你是一个知识库问答助手，请回答用户的问题。（用中文回答）\n\n问题：{request.question}"

    # 2. 调用 Ollama API 生成回答（非流式，作为后备）
    answer = ""
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
            answer = result.get("response", "抱歉，暂时无法回答")
    except Exception as e:
        answer = f"抱歉，AI 服务暂时不可用：{str(e)}"

    # 3. 保存历史
    if request.session_id not in chat_history:
        chat_history[request.session_id] = []
    chat_history[request.session_id].append({
        "question": request.question,
        "answer": answer
    })

    return ChatResponse(
        answer=answer,
        sources=sources,
        used_rag=used_rag
    )


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    流式聊天问答接口
    支持 RAG 增强：从向量库检索相关文档，作为上下文回答
    """
    # 1. 如果启用 RAG，先检索相关文档
    prompt = None
    sources = []
    used_rag = False

    if request.use_rag:
        try:
            prompt, sources = await chat_with_rag(request)
            used_rag = True
        except Exception as e:
            prompt = f"你是一个知识库问答助手，请回答用户的问题。（用中文回答）\n\n问题：{request.question}"
    else:
        prompt = f"你是一个知识库问答助手，请回答用户的问题。（用中文回答）\n\n问题：{request.question}"

    # 2. 保存历史
    if request.session_id not in chat_history:
        chat_history[request.session_id] = []
    chat_history[request.session_id].append({
        "question": request.question,
        "answer": ""  # 先占位，流式完成后再更新
    })

    # 3. 返回流式响应
    async def stream_generator():
        full_response = ""
        try:
            async for chunk in generate_streaming_response(prompt, "llama3:8b"):
                full_response += chunk
                # 发送 SSE 格式的数据
                yield f"data: {json.dumps({'token': chunk, 'done': False})}\n\n"

            # 流式结束后，发送完成信号
            yield f"data: {json.dumps({'token': '', 'done': True, 'sources': [s.dict() for s in sources]})}\n\n"

            # 更新历史记录
            if chat_history[request.session_id]:
                chat_history[request.session_id][-1]["answer"] = full_response

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


@router.get("/history/{session_id}")
async def get_history(session_id: str):
    """获取聊天历史"""
    return {"session_id": session_id, "messages": chat_history.get(session_id, [])}


@router.delete("/history/{session_id}")
async def clear_history(session_id: str):
    """清除聊天历史"""
    if session_id in chat_history:
        chat_history[session_id] = []
    return {"status": "success", "message": f"会话 {session_id} 的历史已清除"}
