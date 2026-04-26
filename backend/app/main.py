"""
FastAPI 主应用入口
ChainMind - 本地知识库问答系统
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import upload, chat, rag, memory, agent

# 创建 FastAPI 应用
app = FastAPI(
    title="ChainMind API",
    description="基于 FastAPI + Ollama + LangChain 的本地知识库问答系统",
    version="1.0.0"
)

# 配置 CORS（允许前端跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(upload)
app.include_router(chat)
app.include_router(rag)
app.include_router(memory)
app.include_router(agent)


@app.get("/")
async def root():
    """根路径 - 健康检查"""
    return {
        "name": "ChainMind API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "upload": "/upload",
            "chat": "/chat",
            "rag": "/rag",
            "memory": "/memory",
            "agent": "/agent"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
