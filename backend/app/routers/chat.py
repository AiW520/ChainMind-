"""
Chat Router v2.0 - Multi-Agent Collaboration System
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import httpx
import json
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

from ..services.vector_store import get_vector_store

router = APIRouter(prefix="/chat", tags=["chat"])

chat_history = {}

class ChatRequest(BaseModel):
    question: str
    session_id: str = "default"
    use_rag: bool = True
    top_k: int = 3

class SourceItem(BaseModel):
    content: str
    filename: str
    distance: Optional[float] = None
    vector_score: Optional[float] = None
    bm25_score: Optional[float] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceItem]
    used_rag: bool
    agent_flow: Optional[dict] = None

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
async def call_ollama_with_retry(prompt: str, model: str = "llama3:8b"):
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            }
        )
        response.raise_for_status()
        return response.json()

class QueryRewriteAgent:
    @staticmethod
    async def rewrite(query: str) -> dict:
        prompt = """You are a query rewriting expert. Analyze and optimize the following query:

Query: {}

Tasks:
1. Identify user intent
2. Expand synonyms and related terms
3. Resolve ambiguity
4. Generate 2-3 optimized query variants

Output JSON format:
{{
    "intent": "intent description",
    "variants": ["variant1", "variant2", "variant3"],
    "keywords": ["kw1", "kw2"]
}}

Output JSON:""".format(query)

        try:
            result = await call_ollama_with_retry(prompt)
            response = result.get("response", "")
            
            try:
                data = json.loads(response)
            except:
                data = {
                    "intent": query,
                    "variants": [query],
                    "keywords": query.split()[:5]
                }
            
            return {
                "success": True,
                "intent": data.get("intent", query),
                "variants": data.get("variants", [query]),
                "keywords": data.get("keywords", [])
            }
        except Exception as e:
            return {
                "success": False,
                "intent": query,
                "variants": [query],
                "keywords": query.split()[:5],
                "error": str(e)
            }

class RetrievalAgent:
    @staticmethod
    async def retrieve(query: str, top_k: int = 5) -> dict:
        vector_store = get_vector_store()
        results = vector_store.search(
            query,
            top_k=top_k,
            use_hybrid=True,
            use_rerank=True
        )
        stats = vector_store.get_stats()
        
        return {
            "success": True,
            "results": results,
            "total_chunks": stats.get("total_vectors", 0),
            "query": query
        }

class AnswerGenerationAgent:
    @staticmethod
    def build_prompt(query: str, contexts: List[str], intent: str = "") -> str:
        context_str = "\n\n".join([
            "[Doc{}]:\n{}".format(i+1, ctx)
            for i, ctx in enumerate(contexts)
        ])
        
        return """You are a professional knowledge base QA assistant.

Context:
{}

User Question:
{}

Requirements:
1. Answer must be based on provided documents
2. If no relevant info, state clearly
3. Be accurate and concise
4. Keep answer within 300 words

Answer:""".format(context_str, query)

    @staticmethod
    async def generate(query: str, contexts: List[str], intent: str = "") -> dict:
        prompt = AnswerGenerationAgent.build_prompt(query, contexts, intent)
        
        try:
            result = await call_ollama_with_retry(prompt)
            answer = result.get("response", "Sorry, cannot generate answer")
            
            return {
                "success": True,
                "answer": answer.strip(),
                "prompt_used": prompt[:200] + "..."
            }
        except Exception as e:
            return {
                "success": False,
                "answer": "AI service unavailable: {}".format(str(e)),
                "error": str(e)
            }

class VerificationAgent:
    @staticmethod
    async def verify(query: str, answer: str, contexts: List[str]) -> dict:
        context_str = "\n\n".join(["[Doc{}]: {}".format(i+1, ctx) for i, ctx in enumerate(contexts)])
        
        prompt = """You are a fact-checking expert. Verify if the answer is accurate based on documents.

Documents:
{}

Question:
{}

Answer to verify:
{}

Output JSON:
{{
    "accuracy": "high/medium/low",
    "issues": ["issue1", "issue2"],
    "suggestions": ["suggestion1"],
    "has_hallucination": true/false
}}

Output JSON:""".format(context_str, query, answer)

        try:
            result = await call_ollama_with_retry(prompt)
            response = result.get("response", "")
            
            try:
                data = json.loads(response)
            except:
                data = {
                    "accuracy": "medium",
                    "issues": [],
                    "suggestions": [],
                    "has_hallucination": False
                }
            
            return {
                "success": True,
                "accuracy": data.get("accuracy", "medium"),
                "issues": data.get("issues", []),
                "suggestions": data.get("suggestions", []),
                "has_hallucination": data.get("has_hallucination", False)
            }
        except Exception as e:
            return {
                "success": False,
                "accuracy": "unknown",
                "issues": [str(e)],
                "suggestions": [],
                "has_hallucination": None,
                "error": str(e)
            }

class MultiAgentCoordinator:
    def __init__(self):
        self.query_rewrite_agent = QueryRewriteAgent()
        self.retrieval_agent = RetrievalAgent()
        self.generation_agent = AnswerGenerationAgent()
        self.verification_agent = VerificationAgent()

    async def process(self, query: str, use_rag: bool = True, top_k: int = 3) -> dict:
        agent_flow = {
            "query_rewrite": {"status": "pending", "result": None},
            "retrieval": {"status": "pending", "result": None},
            "generation": {"status": "pending", "result": None},
            "verification": {"status": "pending", "result": None}
        }
        
        final_answer = ""
        sources = []
        intent = query
        
        try:
            agent_flow["query_rewrite"]["status"] = "running"
            rewrite_result = await self.query_rewrite_agent.rewrite(query)
            agent_flow["query_rewrite"]["status"] = "completed"
            agent_flow["query_rewrite"]["result"] = rewrite_result
            if rewrite_result.get("success"):
                intent = rewrite_result.get("intent", query)
        except Exception as e:
            agent_flow["query_rewrite"]["status"] = "error"
            agent_flow["query_rewrite"]["error"] = str(e)
        
        try:
            agent_flow["retrieval"]["status"] = "running"
            retrieval_result = await self.retrieval_agent.retrieve(query, top_k)
            agent_flow["retrieval"]["status"] = "completed"
            agent_flow["retrieval"]["result"] = retrieval_result
            if retrieval_result.get("success"):
                sources = retrieval_result.get("results", [])
        except Exception as e:
            agent_flow["retrieval"]["status"] = "error"
            agent_flow["retrieval"]["error"] = str(e)
        
        try:
            agent_flow["generation"]["status"] = "running"
            contexts = [r.get("content", "") for r in sources]
            
            if use_rag and contexts:
                generation_result = await self.generation_agent.generate(query, contexts, intent)
            else:
                generation_result = await self.generation_agent.generate(query, [], intent)
            
            agent_flow["generation"]["status"] = "completed"
            agent_flow["generation"]["result"] = generation_result
            if generation_result.get("success"):
                final_answer = generation_result.get("answer", "")
        except Exception as e:
            agent_flow["generation"]["status"] = "error"
            agent_flow["generation"]["error"] = str(e)
            final_answer = "Error generating answer: {}".format(str(e))
        
        if final_answer and use_rag and sources:
            try:
                agent_flow["verification"]["status"] = "running"
                verification_result = await self.verification_agent.verify(
                    query, final_answer,
                    [r.get("content", "") for r in sources]
                )
                agent_flow["verification"]["status"] = "completed"
                agent_flow["verification"]["result"] = verification_result
            except Exception as e:
                agent_flow["verification"]["status"] = "error"
                agent_flow["verification"]["error"] = str(e)
        
        return {
            "answer": final_answer,
            "sources": sources,
            "used_rag": use_rag and bool(sources),
            "agent_flow": agent_flow
        }

_coordinator = None

def get_coordinator():
    global _coordinator
    if _coordinator is None:
        _coordinator = MultiAgentCoordinator()
    return _coordinator

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    coordinator = get_coordinator()
    
    result = await coordinator.process(
        query=request.question,
        use_rag=request.use_rag,
        top_k=request.top_k
    )
    
    if request.session_id not in chat_history:
        chat_history[request.session_id] = []
    chat_history[request.session_id].append({
        "question": request.question,
        "answer": result["answer"]
    })
    
    sources = [
        SourceItem(
            content=s.get("content", ""),
            filename=s.get("filename", "unknown"),
            distance=s.get("distance"),
            vector_score=s.get("vector_score"),
            bm25_score=s.get("bm25_score")
        )
        for s in result.get("sources", [])
    ]
    
    return ChatResponse(
        answer=result["answer"],
        sources=sources,
        used_rag=result["used_rag"],
        agent_flow=result.get("agent_flow")
    )

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    coordinator = get_coordinator()
    
    result = await coordinator.process(
        query=request.question,
        use_rag=request.use_rag,
        top_k=request.top_k
    )
    
    sources = result.get("sources", [])
    
    async def stream_generator():
        full_answer = result["answer"]
        
        for i in range(0, len(full_answer), 3):
            chunk = full_answer[i:i+3]
            data_dict = {"type": "token", "data": {"token": chunk, "done": False}}
            yield "data: " + json.dumps(data_dict) + "\n\n"
            await asyncio.sleep(0.01)
        
        done_dict = {"type": "done", "data": {"sources": sources}}
        yield "data: " + json.dumps(done_dict) + "\n\n"
    
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
    return {
        "session_id": session_id,
        "messages": chat_history.get(session_id, [])
    }

@router.delete("/history/{session_id}")
async def clear_history(session_id: str):
    if session_id in chat_history:
        chat_history[session_id] = []
    return {"status": "success", "message": "Session {} history cleared".format(session_id)}
