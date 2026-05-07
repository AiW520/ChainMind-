"""
RAG Router v2.0
Enhanced retrieval with hybrid search + rerank + streaming output
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import httpx
import json
import asyncio

from ..services.vector_store import get_vector_store

router = APIRouter(prefix="/rag", tags=["RAG"])


class AddChunksRequest(BaseModel):
    chunks: List[str]
    filename: str


class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5


class SourceItem(BaseModel):
    content: str
    filename: str
    distance: Optional[float] = None
    vector_score: Optional[float] = None
    bm25_score: Optional[float] = None
    hybrid_score: Optional[float] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceItem]


def build_enhanced_prompt(query: str, contexts: List[dict]) -> str:
    """Build enhanced prompt with better structure"""
    if not contexts:
        return f"""You are a professional knowledge base assistant. Please answer the user's question.

User Question: {query}

Instructions:
1. If you don't have enough information, state it clearly
2. Be accurate and concise
3. Answer in the same language as the question

Answer:"""

    context_str = "\n\n".join([
        "[Document {}] (Source: {}):\n{}\nRelevance Score: {:.2f}".format(
            i + 1, 
            ctx.get("filename", "unknown"),
            ctx.get("content", ""),
            ctx.get("hybrid_score", ctx.get("vector_score", 0.5))
        )
        for i, ctx in enumerate(contexts)
    ])

    return f"""You are a professional knowledge base assistant. Answer based on the provided documents.

## Reference Documents
{context_str}

## User Question
{query}

## Answer Guidelines
1. MUST base your answer on the provided reference documents
2. If documents don't contain relevant information, clearly state: "Based on the provided documents, I cannot answer this question"
3. Be accurate, concise, and professional
4. Cite sources when appropriate (e.g., "According to Document 1...")
5. Answer in the same language as the question
6. Keep the answer within 300 words

## Answer"""


async def stream_ollama_response(prompt: str, model: str = "llama3:8b"):
    """Stream response from Ollama API"""
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
        yield f"\n[Error: {str(e)}]"


@router.post("/add", response_model=dict)
async def add_chunks(request: AddChunksRequest):
    """Add text chunks to vector store"""
    if not request.chunks:
        raise HTTPException(status_code=400, detail="Chunks cannot be empty")

    vector_store = get_vector_store()
    result = vector_store.add_documents(request.chunks, request.filename)

    return result


@router.post("/query", response_model=QueryResponse)
async def rag_query(request: QueryRequest):
    """RAG query with hybrid search + rerank"""
    vector_store = get_vector_store()

    # Use hybrid search with rerank
    retrieved_docs = vector_store.search(
        request.query, 
        top_k=request.top_k,
        use_hybrid=True,
        use_rerank=True
    )

    # Build enhanced prompt
    prompt = build_enhanced_prompt(request.query, retrieved_docs)

    # Call LLM
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
            answer = result.get("response", "Sorry, unable to generate answer")
    except Exception as e:
        answer = "AI service unavailable: {}".format(str(e))

    # Build sources
    sources = [
        SourceItem(
            content=doc.get("content", ""),
            filename=doc.get("filename", "unknown"),
            distance=doc.get("distance"),
            vector_score=doc.get("vector_score"),
            bm25_score=doc.get("bm25_score"),
            hybrid_score=doc.get("hybrid_score")
        )
        for doc in retrieved_docs
    ]

    return QueryResponse(answer=answer, sources=sources)


@router.post("/query/stream")
async def rag_query_stream(request: QueryRequest):
    """RAG query with streaming output"""
    vector_store = get_vector_store()

    # Use hybrid search with rerank
    retrieved_docs = vector_store.search(
        request.query,
        top_k=request.top_k,
        use_hybrid=True,
        use_rerank=True
    )

    # Build enhanced prompt
    prompt = build_enhanced_prompt(request.query, retrieved_docs)

    # Build sources
    sources = [
        {
            "content": doc.get("content", ""),
            "filename": doc.get("filename", "unknown"),
            "distance": doc.get("distance"),
            "vector_score": doc.get("vector_score"),
            "bm25_score": doc.get("bm25_score"),
            "hybrid_score": doc.get("hybrid_score")
        }
        for doc in retrieved_docs
    ]

    async def stream_generator():
        try:
            async for chunk in stream_ollama_response(prompt, "llama3:8b"):
                data = {"token": chunk, "done": False}
                yield "data: " + json.dumps(data) + "\n\n"
                await asyncio.sleep(0.001)

            # Send completion signal with sources
            done_data = {"token": "", "done": True, "sources": sources}
            yield "data: " + json.dumps(done_data) + "\n\n"

        except Exception as e:
            error_data = {"token": "\n[Error: {}]".format(str(e)), "done": True, "error": True}
            yield "data: " + json.dumps(error_data) + "\n\n"

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
async def search_docs(query: str, top_k: int = 5, use_hybrid: bool = True, use_rerank: bool = True):
    """Search documents without LLM generation"""
    vector_store = get_vector_store()
    results = vector_store.search(
        query, 
        top_k=top_k,
        use_hybrid=use_hybrid,
        use_rerank=use_rerank
    )

    return {
        "query": query,
        "count": len(results),
        "results": results
    }


@router.get("/stats")
async def get_stats():
    """Get vector store statistics"""
    vector_store = get_vector_store()
    return vector_store.get_stats()


@router.delete("/clear")
async def clear_vector_store():
    """Clear all vectors (use with caution)"""
    vector_store = get_vector_store()
    return vector_store.clear_all()


@router.delete("/file/{filename}")
async def delete_file_vectors(filename: str):
    """Delete all vectors for a file"""
    vector_store = get_vector_store()
    return vector_store.delete_by_filename(filename)
