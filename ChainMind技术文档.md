# ChainMind：基于RAG的智能知识库系统开发指南

## 项目介绍

ChainMind是一个基于RAG（Retrieval-Augmented Generation）技术的智能知识库系统，它可以：

- 上传和处理多种格式的文档（.txt, .md, .pdf）
- 基于文档内容进行智能问答
- 提供RAG检索增强功能
- 支持多轮对话和记忆功能
- 具有现代化的Web界面

本项目采用前后端分离架构，后端使用FastAPI构建，前端使用React + Tailwind CSS开发。

## 环境搭建

### 后端环境

**所需依赖：**
- Python 3.8+
- FastAPI
- Uvicorn
- PyPDF
- 其他依赖包

**安装步骤：**

```bash
# 1. 进入后端目录
cd backend

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动后端服务
cd app
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 前端环境

**所需依赖：**
- Node.js 16+
- React
- Tailwind CSS
- Vite

**安装步骤：**

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 启动前端服务
npm run dev
```

**访问地址：**
- 前端：http://localhost:3000
- 后端API：http://localhost:8000

## 项目架构

### 整体架构

```
┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │
│   前端 React    │────▶│  后端 FastAPI   │
│   + Tailwind    │     │   + Uvicorn     │
│                 │◀────│                 │
└─────────────────┘     └─────────────────┘
                            ▲
                            │
                   ┌────────┴────────┐
                   │                 │
        ┌──────────▼──────────┐      │
        │                     │      │
        │    路由层 (routers)  │      │
        │                     │      │
        └──────────┬──────────┘      │
                   │                 │
                   ▼                 │
        ┌────────────────────┐       │
        │                    │       │
        │  服务层 (services)  │       │
        │                    │       │
        └────────────────────┘       │
                   │                 │
                   ▼                 │
        ┌────────────────────┐       │
        │                    │       │
        │    数据存储层      │◀──────┘
        │ (向量存储 + 文件)  │
        └────────────────────┘
```

## 后端模块详细分析

### 1. 主入口文件 (main.py)

```python
"""
FastAPI 应用主入口
功能：初始化应用，配置CORS，注册路由
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import upload, chat, rag, memory, agent

# 创建 FastAPI 应用
app = FastAPI(
    title="ChainMind API",
    description="基于RAG的智能知识库系统API",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该设置具体的前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(upload.router)
app.include_router(chat.router)
app.include_router(rag.router)
app.include_router(memory.router)
app.include_router(agent.router)

# 健康检查端点
@app.get("/health")
async def health_check():
    """
    健康检查端点
    用于监控服务状态
    
    Returns:
        dict: 包含服务状态的字典
    """
    return {"status": "healthy", "message": "ChainMind API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**函数/方法详细说明：**

1. **health_check()**
   - **功能**：健康检查端点，用于监控服务状态
   - **参数**：无
   - **返回值**：`dict` - 包含服务状态的字典
   - **使用场景**：用于监控系统健康状态，确保服务正常运行

### 2. 配置文件 (config.py)

```python
"""
应用配置文件
功能：存储应用的配置参数
"""

# Ollama 配置
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3"

# 文档处理配置
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# 向量存储配置
VECTOR_STORE_PERSIST_DIR = "./chroma_db"
```

**配置参数说明：**

1. **OLLAMA_BASE_URL**
   - **功能**：Ollama API的基础URL
   - **值**：`"http://localhost:11434"`
   - **使用场景**：用于调用Ollama模型进行AI生成

2. **OLLAMA_MODEL**
   - **功能**：默认使用的Ollama模型
   - **值**：`"llama3"`
   - **使用场景**：指定AI对话使用的模型

3. **CHUNK_SIZE**
   - **功能**：文档切分的块大小
   - **值**：`500`
   - **使用场景**：控制文档切分的粒度

4. **CHUNK_OVERLAP**
   - **功能**：相邻文档块的重叠字符数
   - **值**：`50`
   - **使用场景**：确保文档上下文的连续性

5. **VECTOR_STORE_PERSIST_DIR**
   - **功能**：向量存储的持久化目录
   - **值**：`"./chroma_db"`
   - **使用场景**：指定向量存储的存储位置

### 3. 上传路由 (upload.py)

```python
"""
文档上传路由
功能：接收用户上传的文档，保存到服务器，并调用文档处理服务
"""
import os
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from services.document_processor import process_document
from services.vector_store import get_vector_store

from pathlib import Path
import os

router = APIRouter(prefix="/upload", tags=["文档上传"])

# 支持的文件类型
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}

def get_upload_dir():
    """
    获取上传目录的绝对路径
    确保上传目录存在
    
    Returns:
        Path: 上传目录的Path对象
    """
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    upload_dir = data_dir / "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir

@router.post("/file")
async def upload_file(file: UploadFile = File(...)):
    """
    上传单个文档
    
    Args:
        file: 要上传的文件（支持 .txt, .md, .pdf）
    
    Returns:
        dict: 文档处理结果，包含文件名、页数、切割块数等
    """
    # 检查文件扩展名
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_extension}，仅支持: {', '.join(SUPPORTED_EXTENSIONS)}"
        )
    
    # 检查文件大小（限制 10MB）
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小超过 10MB 限制")
    
    # 保存文件
    upload_dir = get_upload_dir()
    file_path = upload_dir / file.filename
    with open(file_path, "wb") as buffer:
        buffer.write(contents)
    
    # 处理文档
    try:
        result = process_document(str(file_path))
        result["status"] = "success"
        
        # 自动将 chunks 添加到向量库
        if result.get("chunks"):
            vector_store = get_vector_store()
            vector_store.add_documents(result["chunks"], file.filename)
            result["vector_stored"] = True
        
        return result
    except Exception as e:
        # 处理失败，删除已上传的文件
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"文档处理失败: {str(e)}")

@router.post("/files")
async def upload_multiple_files(files: List[UploadFile] = File(...)):
    """
    批量上传文档
    
    Args:
        files: 要上传的文件列表
    
    Returns:
        dict: 所有文档的处理结果
    """
    results = []
    uploaded_files = []
    
    for file in files:
        # 检查文件类型
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in SUPPORTED_EXTENSIONS:
            results.append({
                "file_name": file.filename,
                "status": "error",
                "error": f"不支持的文件类型: {file_extension}"
            })
            continue
        
        # 保存文件
        contents = await file.read()
        upload_dir = get_upload_dir()
        file_path = upload_dir / file.filename
        
        try:
            with open(file_path, "wb") as buffer:
                buffer.write(contents)
            uploaded_files.append(file_path)
            
            # 处理文档
            result = process_document(str(file_path))
            result["status"] = "success"
            
            # 自动将 chunks 添加到向量库
            if result.get("chunks"):
                vector_store = get_vector_store()
                vector_store.add_documents(result["chunks"], file.filename)
                result["vector_stored"] = True
            
            results.append(result)
        except Exception as e:
            results.append({
                "file_name": file.filename,
                "status": "error",
                "error": str(e)
            })
            # 清理已上传的文件
            if file_path.exists():
                file_path.unlink()
    
    return {
        "total": len(files),
        "success_count": sum(1 for r in results if r["status"] == "success"),
        "results": results
    }

@router.get("/list")
async def list_uploaded_files():
    """
    列出已上传的所有文档
    
    Returns:
        dict: 包含已上传文件列表的字典
    """
    files = []
    upload_dir = get_upload_dir()
    for file_path in upload_dir.iterdir():
        if file_path.is_file():
            files.append({
                "name": file_path.name,
                "size": file_path.stat().st_size,
                "extension": file_path.suffix
            })
    return {"files": files}

@router.delete("/{filename}")
async def delete_file(filename: str):
    """
    删除指定的已上传文件
    
    Args:
        filename: 要删除的文件名
    
    Returns:
        dict: 删除结果
    """
    upload_dir = get_upload_dir()
    file_path = upload_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    file_path.unlink()
    return {"status": "deleted", "filename": filename}
```

**函数/方法详细说明：**

1. **get_upload_dir()**
   - **功能**：获取上传目录的绝对路径，确保目录存在
   - **参数**：无
   - **返回值**：`Path` - 上传目录的Path对象
   - **使用场景**：在文件上传和管理操作中获取正确的文件存储路径

2. **upload_file(file: UploadFile)**
   - **功能**：上传单个文档并处理
   - **参数**：
     - `file`：要上传的文件，支持.txt、.md、.pdf格式
   - **返回值**：`dict` - 包含文档处理结果的字典
   - **使用场景**：处理用户上传的单个文档，包括验证、保存、处理和添加到向量库

3. **upload_multiple_files(files: List[UploadFile])**
   - **功能**：批量上传文档并处理
   - **参数**：
     - `files`：要上传的文件列表
   - **返回值**：`dict` - 包含所有文档处理结果的字典
   - **使用场景**：一次性处理多个文件上传

4. **list_uploaded_files()**
   - **功能**：列出所有已上传的文档
   - **参数**：无
   - **返回值**：`dict` - 包含已上传文件列表的字典
   - **使用场景**：查看服务器上已上传的所有文档

5. **delete_file(filename: str)**
   - **功能**：删除指定的已上传文件
   - **参数**：
     - `filename`：要删除的文件名
   - **返回值**：`dict` - 删除结果
   - **使用场景**：移除不需要的已上传文件

### 4. 聊天路由 (chat.py)

```python
"""
聊天路由
功能：提供基于RAG的智能聊天功能
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.vector_store import get_vector_store

router = APIRouter(prefix="/chat", tags=["聊天"])

# 聊天历史存储（内存实现）
chat_history = []

class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    user_id: str = "default"

class ChatResponse(BaseModel):
    """聊天响应模型"""
    response: str
    sources: list = []

@router.post("/")
async def chat(request: ChatRequest):
    """
    聊天接口
    
    Args:
        request: 聊天请求，包含用户消息和用户ID
    
    Returns:
        ChatResponse: 聊天响应，包含回答和相关文档来源
    """
    try:
        # 获取向量存储
        vector_store = get_vector_store()
        
        # 搜索相关文档
        sources = vector_store.search(request.message, top_k=3)
        
        # 构建上下文
        context = "\n".join([f"来源: {source['filename']}\n内容: {source['content']}" for source in sources])
        
        # 构建提示词
        prompt = f"基于以下上下文回答用户问题:\n\n{context}\n\n用户问题: {request.message}"
        
        # 这里应该调用LLM模型，现在返回模拟响应
        response = f"基于文档内容的回答: {request.message}"
        
        # 保存到聊天历史
        chat_history.append({
            "user_id": request.user_id,
            "message": request.message,
            "response": response,
            "sources": sources
        })
        
        return ChatResponse(response=response, sources=sources)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"聊天失败: {str(e)}")

@router.get("/history")
async def get_chat_history(user_id: str = "default"):
    """
    获取聊天历史
    
    Args:
        user_id: 用户ID，默认为"default"
    
    Returns:
        dict: 包含聊天历史记录的字典
    """
    user_history = [msg for msg in chat_history if msg["user_id"] == user_id]
    return {"history": user_history}

@router.delete("/history")
async def clear_chat_history(user_id: str = "default"):
    """
    清空聊天历史
    
    Args:
        user_id: 用户ID，默认为"default"
    
    Returns:
        dict: 操作结果
    """
    global chat_history
    chat_history = [msg for msg in chat_history if msg["user_id"] != user_id]
    return {"status": "success", "message": "聊天历史已清空"}
```

**函数/方法详细说明：**

1. **chat(request: ChatRequest)**
   - **功能**：处理用户聊天请求，基于文档内容生成回答
   - **参数**：
     - `request`：聊天请求对象，包含用户消息和用户ID
   - **返回值**：`ChatResponse` - 包含回答和相关文档来源的响应
   - **使用场景**：处理用户的聊天消息，提供基于RAG的智能回答

2. **get_chat_history(user_id: str)**
   - **功能**：获取指定用户的聊天历史
   - **参数**：
     - `user_id`：用户ID，默认为"default"
   - **返回值**：`dict` - 包含聊天历史记录的字典
   - **使用场景**：查看用户的历史聊天记录

3. **clear_chat_history(user_id: str)**
   - **功能**：清空指定用户的聊天历史
   - **参数**：
     - `user_id`：用户ID，默认为"default"
   - **返回值**：`dict` - 操作结果
   - **使用场景**：清除用户的历史聊天记录

### 5. RAG路由 (rag.py)

```python
"""
RAG路由
功能：提供检索增强生成功能
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.vector_store import get_vector_store

router = APIRouter(prefix="/rag", tags=["RAG检索增强"])

class RAGRequest(BaseModel):
    """RAG请求模型"""
    query: str
    top_k: int = 5

class RAGResponse(BaseModel):
    """RAG响应模型"""
    query: str
    results: list
    total: int

@router.post("/query")
async def rag_query(request: RAGRequest):
    """
    RAG检索接口
    
    Args:
        request: RAG请求，包含查询文本和返回结果数量
    
    Returns:
        RAGResponse: 检索结果，包含查询文本、结果列表和总数
    """
    try:
        # 获取向量存储
        vector_store = get_vector_store()
        
        # 执行搜索
        results = vector_store.search(request.query, top_k=request.top_k)
        
        return RAGResponse(
            query=request.query,
            results=results,
            total=len(results)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")

@router.get("/stats")
async def get_rag_stats():
    """
    获取RAG统计信息
    
    Returns:
        dict: 向量存储统计信息
    """
    try:
        vector_store = get_vector_store()
        stats = vector_store.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")
```

**函数/方法详细说明：**

1. **rag_query(request: RAGRequest)**
   - **功能**：执行RAG检索，根据查询文本搜索相关文档
   - **参数**：
     - `request`：RAG请求对象，包含查询文本和返回结果数量
   - **返回值**：`RAGResponse` - 包含查询结果的响应
   - **使用场景**：在前端RAG搜索面板中执行文档检索

2. **get_rag_stats()**
   - **功能**：获取向量存储的统计信息
   - **参数**：无
   - **返回值**：`dict` - 包含向量存储统计信息的字典
   - **使用场景**：查看向量存储的状态和统计数据

### 6. 记忆路由 (memory.py)

```python
"""
记忆路由
功能：管理用户记忆和上下文
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from services.memory import get_memory

router = APIRouter(prefix="/memory", tags=["记忆管理"])

class MemoryItem(BaseModel):
    """记忆项模型"""
    id: str
    content: str
    timestamp: float

class MemoryRequest(BaseModel):
    """记忆请求模型"""
    content: str
    user_id: str = "default"

@router.post("/")
async def add_memory(request: MemoryRequest):
    """
    添加记忆
    
    Args:
        request: 记忆请求，包含记忆内容和用户ID
    
    Returns:
        dict: 添加结果
    """
    try:
        memory = get_memory()
        result = memory.add_memory(request.content, request.user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加记忆失败: {str(e)}")

@router.get("/")
async def get_memories(user_id: str = "default", limit: int = 10):
    """
    获取记忆列表
    
    Args:
        user_id: 用户ID，默认为"default"
        limit: 返回数量限制，默认为10
    
    Returns:
        dict: 包含记忆列表的字典
    """
    try:
        memory = get_memory()
        memories = memory.get_memories(user_id, limit)
        return {"memories": memories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取记忆失败: {str(e)}")

@router.delete("/{memory_id}")
async def delete_memory(memory_id: str):
    """
    删除记忆
    
    Args:
        memory_id: 记忆ID
    
    Returns:
        dict: 删除结果
    """
    try:
        memory = get_memory()
        result = memory.delete_memory(memory_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除记忆失败: {str(e)}")

@router.get("/recall")
async def recall_memories(query: str, user_id: str = "default", top_k: int = 3):
    """
    回忆相关记忆
    
    Args:
        query: 查询文本
        user_id: 用户ID，默认为"default"
        top_k: 返回结果数量，默认为3
    
    Returns:
        dict: 包含相关记忆列表的字典
    """
    try:
        memory = get_memory()
        memories = memory.recall_memories(query, user_id, top_k)
        return {"memories": memories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"回忆失败: {str(e)}")
```

**函数/方法详细说明：**

1. **add_memory(request: MemoryRequest)**
   - **功能**：添加新的记忆
   - **参数**：
     - `request`：记忆请求对象，包含记忆内容和用户ID
   - **返回值**：`dict` - 添加结果
   - **使用场景**：为用户添加新的记忆项

2. **get_memories(user_id: str, limit: int)**
   - **功能**：获取用户的记忆列表
   - **参数**：
     - `user_id`：用户ID，默认为"default"
     - `limit`：返回数量限制，默认为10
   - **返回值**：`dict` - 包含记忆列表的字典
   - **使用场景**：查看用户的记忆历史

3. **delete_memory(memory_id: str)**
   - **功能**：删除指定的记忆
   - **参数**：
     - `memory_id`：记忆ID
   - **返回值**：`dict` - 删除结果
   - **使用场景**：移除不需要的记忆项

4. **recall_memories(query: str, user_id: str, top_k: int)**
   - **功能**：根据查询文本回忆相关记忆
   - **参数**：
     - `query`：查询文本
     - `user_id`：用户ID，默认为"default"
     - `top_k`：返回结果数量，默认为3
   - **返回值**：`dict` - 包含相关记忆列表的字典
   - **使用场景**：基于用户的查询找到相关的记忆内容

### 7. 智能代理路由 (agent.py)

```python
"""
智能代理路由
功能：提供基于工具的智能代理功能
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from services.agent import Agent, AgentConfig, get_agent
from services.tool_registry import get_tool_registry

router = APIRouter(prefix="/agent", tags=["智能代理"])

class AgentRequest(BaseModel):
    """智能代理请求模型"""
    message: str
    user_id: str = "default"

class AgentResponse(BaseModel):
    """智能代理响应模型"""
    response: str
    tool_calls: List[Dict] = []

@router.post("/")
async def agent_chat(request: AgentRequest):
    """
    智能代理聊天接口
    
    Args:
        request: 智能代理请求，包含用户消息和用户ID
    
    Returns:
        AgentResponse: 代理响应和工具调用结果
    """
    try:
        # 获取智能代理
        agent = get_agent()
        
        # 处理用户消息
        response = agent.process_message(request.message, request.user_id)
        
        return AgentResponse(
            response=response.get("response", ""),
            tool_calls=response.get("tool_calls", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"代理处理失败: {str(e)}")

@router.get("/tools")
async def get_agent_tools():
    """
    获取智能代理可用工具
    
    Returns:
        dict: 工具列表
    """
    try:
        tool_registry = get_tool_registry()
        tools = tool_registry.get_tools()
        return {"tools": tools}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取工具失败: {str(e)}")
```

**函数/方法详细说明：**

1. **agent_chat(request: AgentRequest)**
   - **功能**：处理智能代理的聊天请求
   - **参数**：
     - `request`：智能代理请求对象，包含用户消息和用户ID
   - **返回值**：`AgentResponse` - 包含代理响应和工具调用结果
   - **使用场景**：与智能代理进行交互，可能涉及工具调用

2. **get_agent_tools()**
   - **功能**：获取智能代理可用的工具列表
   - **参数**：无
   - **返回值**：`dict` - 包含工具列表的字典
   - **使用场景**：查看智能代理可以使用的工具

### 8. 文档处理服务 (document_processor.py)

```python
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
        str: 文档文本内容
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
        chunk_size: 每个块的最大字符数，默认为500
        chunk_overlap: 相邻块之间的重叠字符数，默认为50
    
    Returns:
        List[str]: 切分后的文本块列表
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
        dict: 包含文档信息的字典
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
```

**函数/方法详细说明：**

1. **load_document(file_path: str, file_extension: str)**
   - **功能**：根据文件类型加载文档内容
   - **参数**：
     - `file_path`：文件路径
     - `file_extension`：文件扩展名（.txt, .md, .pdf）
   - **返回值**：`str` - 文档文本内容
   - **使用场景**：从不同类型的文件中提取文本内容

2. **split_text(text: str, chunk_size: int, chunk_overlap: int)**
   - **功能**：将长文本切分为小块，考虑句子边界
   - **参数**：
     - `text`：要切分的文本
     - `chunk_size`：每个块的最大字符数，默认为500
     - `chunk_overlap`：相邻块之间的重叠字符数，默认为50
   - **返回值**：`List[str]` - 切分后的文本块列表
   - **使用场景**：为RAG系统准备合适大小的文本块

3. **process_document(file_path: str)**
   - **功能**：处理单个文档，包括加载和切分
   - **参数**：
     - `file_path`：文件路径
   - **返回值**：`dict` - 包含文档信息的字典
   - **使用场景**：完整处理上传的文档，为向量存储做准备

### 9. 向量存储服务 (vector_store.py)

```python
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
            persist_directory: 持久化目录，默认为"./chroma_db"
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
            Dict: 添加结果
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
            top_k: 返回结果数量，默认为5
        
        Returns:
            List[Dict]: 相关文档列表，每项包含 content, filename, distance
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
            Dict: 删除结果
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
            Dict: 统计信息
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
            Dict: 操作结果
        """
        self.documents = []
        return {"status": "success", "message": "存储已清空"}


# 全局单例向量存储实例
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """
    获取全局向量存储实例
    
    Returns:
        VectorStore: 向量存储实例
    """
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
```

**函数/方法详细说明：**

1. **VectorStore.__init__(self, persist_directory: str)**
   - **功能**：初始化向量存储
   - **参数**：
     - `persist_directory`：持久化目录，默认为"./chroma_db"
   - **使用场景**：创建向量存储实例，准备存储文档块

2. **VectorStore.add_documents(self, chunks: List[str], filename: str)**
   - **功能**：将文本块添加到向量存储
   - **参数**：
     - `chunks`：文本块列表
     - `filename`：来源文件名
   - **返回值**：`Dict` - 添加结果
   - **使用场景**：将处理后的文档块存储到向量库中

3. **VectorStore.search(self, query: str, top_k: int)**
   - **功能**：检索与查询相关的文本块
   - **参数**：
     - `query`：查询文本
     - `top_k`：返回结果数量，默认为5
   - **返回值**：`List[Dict]` - 相关文档列表
   - **使用场景**：在RAG系统中根据用户查询找到相关文档

4. **VectorStore.delete_by_filename(self, filename: str)**
   - **功能**：删除指定文件的所有记录
   - **参数**：
     - `filename`：文件名
   - **返回值**：`Dict` - 删除结果
   - **使用场景**：当文件被删除时，从向量库中移除相关记录

5. **VectorStore.get_stats(self)**
   - **功能**：获取向量存储的统计信息
   - **参数**：无
   - **返回值**：`Dict` - 统计信息
   - **使用场景**：查看向量存储的状态和统计数据

6. **VectorStore.clear_all(self)**
   - **功能**：清空向量存储
   - **参数**：无
   - **返回值**：`Dict` - 操作结果
   - **使用场景**：重置向量存储，移除所有记录

7. **get_vector_store()**
   - **功能**：获取全局向量存储实例
   - **参数**：无
   - **返回值**：`VectorStore` - 向量存储实例
   - **使用场景**：在应用的不同部分获取共享的向量存储实例

### 10. 记忆服务 (memory.py)

```python
"""
记忆服务
功能：管理用户记忆和上下文
"""
import time
from typing import List, Dict, Optional
import uuid


class MemoryService:
    """记忆服务类，提供记忆管理功能"""
    
    def __init__(self):
        """
        初始化记忆服务
        """
        # 使用内存存储
        self.memories = []
    
    def add_memory(self, content: str, user_id: str = "default") -> Dict:
        """
        添加记忆
        
        Args:
            content: 记忆内容
            user_id: 用户ID，默认为"default"
        
        Returns:
            Dict: 添加结果
        """
        memory_id = str(uuid.uuid4())
        memory = {
            "id": memory_id,
            "content": content,
            "user_id": user_id,
            "timestamp": time.time()
        }
        self.memories.append(memory)
        
        return {
            "status": "success",
            "id": memory_id,
            "message": "记忆添加成功"
        }
    
    def get_memories(self, user_id: str = "default", limit: int = 10) -> List[Dict]:
        """
        获取用户记忆
        
        Args:
            user_id: 用户ID，默认为"default"
            limit: 返回数量限制，默认为10
        
        Returns:
            List[Dict]: 记忆列表
        """
        user_memories = [m for m in self.memories if m["user_id"] == user_id]
        # 按时间倒序排序
        user_memories.sort(key=lambda x: x["timestamp"], reverse=True)
        return user_memories[:limit]
    
    def delete_memory(self, memory_id: str) -> Dict:
        """
        删除记忆
        
        Args:
            memory_id: 记忆ID
        
        Returns:
            Dict: 删除结果
        """
        original_count = len(self.memories)
        self.memories = [m for m in self.memories if m["id"] != memory_id]
        deleted = original_count > len(self.memories)
        
        return {
            "status": "success" if deleted else "error",
            "message": "记忆删除成功" if deleted else "记忆不存在"
        }
    
    def recall_memories(self, query: str, user_id: str = "default", top_k: int = 3) -> List[Dict]:
        """
        回忆相关记忆
        
        Args:
            query: 查询文本
            user_id: 用户ID，默认为"default"
            top_k: 返回结果数量，默认为3
        
        Returns:
            List[Dict]: 相关记忆列表
        """
        user_memories = [m for m in self.memories if m["user_id"] == user_id]
        
        # 简单的字符串匹配
        results = []
        for memory in user_memories:
            score = sum(1 for word in query.lower().split() if word in memory['content'].lower())
            if score > 0:
                results.append({
                    **memory,
                    "relevance": score
                })
        
        # 按相关性排序
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:top_k]
    
    def get_stats(self) -> Dict:
        """
        获取记忆统计信息
        
        Returns:
            Dict: 统计信息
        """
        total_count = len(self.memories)
        
        # 按用户统计
        user_counts = {}
        for memory in self.memories:
            uid = memory.get('user_id', 'unknown')
            user_counts[uid] = user_counts.get(uid, 0) + 1
        
        return {
            "status": "success",
            "total_memories": total_count,
            "users": user_counts
        }


# 全局单例记忆服务实例
_memory_service: Optional[MemoryService] = None


def get_memory() -> MemoryService:
    """
    获取全局记忆服务实例
    
    Returns:
        MemoryService: 记忆服务实例
    """
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service
```

**函数/方法详细说明：**

1. **MemoryService.__init__(self)**
   - **功能**：初始化记忆服务
   - **参数**：无
   - **使用场景**：创建记忆服务实例，准备存储用户记忆

2. **MemoryService.add_memory(self, content: str, user_id: str)**
   - **功能**：添加新的记忆
   - **参数**：
     - `content`：记忆内容
     - `user_id`：用户ID，默认为"default"
   - **返回值**：`Dict` - 添加结果
   - **使用场景**：为用户添加新的记忆项

3. **MemoryService.get_memories(self, user_id: str, limit: int)**
   - **功能**：获取用户的记忆列表
   - **参数**：
     - `user_id`：用户ID，默认为"default"
     - `limit`：返回数量限制，默认为10
   - **返回值**：`List[Dict]` - 记忆列表
   - **使用场景**：查看用户的记忆历史

4. **MemoryService.delete_memory(self, memory_id: str)**
   - **功能**：删除指定的记忆
   - **参数**：
     - `memory_id`：记忆ID
   - **返回值**：`Dict` - 删除结果
   - **使用场景**：移除不需要的记忆项

5. **MemoryService.recall_memories(self, query: str, user_id: str, top_k: int)**
   - **功能**：根据查询文本回忆相关记忆
   - **参数**：
     - `query`：查询文本
     - `user_id`：用户ID，默认为"default"
     - `top_k`：返回结果数量，默认为3
   - **返回值**：`List[Dict]` - 相关记忆列表
   - **使用场景**：基于用户的查询找到相关的记忆内容

6. **MemoryService.get_stats(self)**
   - **功能**：获取记忆服务的统计信息
   - **参数**：无
   - **返回值**：`Dict` - 统计信息
   - **使用场景**：查看记忆服务的状态和统计数据

7. **get_memory()**
   - **功能**：获取全局记忆服务实例
   - **参数**：无
   - **返回值**：`MemoryService` - 记忆服务实例
   - **使用场景**：在应用的不同部分获取共享的记忆服务实例

### 11. 智能代理服务 (agent.py)

```python
"""
智能代理服务
功能：提供基于工具的智能代理功能
"""
from typing import Dict, Any, List, Optional
import time

from services.tool_registry import get_tool_registry
from services.memory import get_memory
from config import OLLAMA_BASE_URL, OLLAMA_MODEL


class AgentConfig:
    """智能代理配置"""
    def __init__(self):
        self.model = OLLAMA_MODEL
        self.base_url = OLLAMA_BASE_URL
        self.temperature = 0.7
        self.max_tokens = 1000


class Agent:
    """智能代理类"""
    
    def __init__(self, config: AgentConfig):
        """
        初始化智能代理
        
        Args:
            config: 代理配置
        """
        self.config = config
        self.tool_registry = get_tool_registry()
        self.memory = get_memory()
    
    def process_message(self, message: str, user_id: str = "default") -> Dict[str, Any]:
        """
        处理用户消息
        
        Args:
            message: 用户消息
            user_id: 用户ID，默认为"default"
        
        Returns:
            Dict[str, Any]: 处理结果
        """
        # 添加到记忆
        self.memory.add_memory(f"用户: {message}", user_id)
        
        # 这里应该调用LLM模型，现在返回模拟响应
        response = f"智能代理回答: {message}"
        
        # 添加到记忆
        self.memory.add_memory(f"代理: {response}", user_id)
        
        return {
            "response": response,
            "tool_calls": []
        }
    
    def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工具
        
        Args:
            tool_name: 工具名称
            tool_input: 工具输入
        
        Returns:
            Dict[str, Any]: 工具执行结果
        """
        try:
            result = self.tool_registry.execute_tool(tool_name, tool_input)
            return {
                "status": "success",
                "result": result
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


# 全局单例智能代理实例
_agent: Optional[Agent] = None


def get_agent() -> Agent:
    """
    获取全局智能代理实例
    
    Returns:
        Agent: 智能代理实例
    """
    global _agent
    if _agent is None:
        config = AgentConfig()
        _agent = Agent(config)
    return _agent
```

**函数/方法详细说明：**

1. **AgentConfig.__init__(self)**
   - **功能**：初始化智能代理配置
   - **参数**：无
   - **使用场景**：创建智能代理的配置对象

2. **Agent.__init__(self, config: AgentConfig)**
   - **功能**：初始化智能代理
   - **参数**：
     - `config`：代理配置
   - **使用场景**：创建智能代理实例，集成工具注册表和记忆服务

3. **Agent.process_message(self, message: str, user_id: str)**
   - **功能**：处理用户消息
   - **参数**：
     - `message`：用户消息
     - `user_id`：用户ID，默认为"default"
   - **返回值**：`Dict[str, Any]` - 处理结果
   - **使用场景**：处理用户的消息，可能调用工具并生成响应

4. **Agent.execute_tool(self, tool_name: str, tool_input: Dict[str, Any])**
   - **功能**：执行指定的工具
   - **参数**：
     - `tool_name`：工具名称
     - `tool_input`：工具输入
   - **返回值**：`Dict[str, Any]` - 工具执行结果
   - **使用场景**：调用智能代理的工具来执行特定任务

5. **get_agent()**
   - **功能**：获取全局智能代理实例
   - **参数**：无
   - **返回值**：`Agent` - 智能代理实例
   - **使用场景**：在应用的不同部分获取共享的智能代理实例

### 12. 工具注册表服务 (tool_registry.py)

```python
"""
工具注册表服务
功能：管理智能代理可用的工具
"""
from typing import Dict, Any, List, Optional


class ToolRegistry:
    """工具注册表类"""
    
    def __init__(self):
        """
        初始化工具注册表
        """
        self.tools = {
            "search_documents": {
                "name": "search_documents",
                "description": "搜索文档内容",
                "parameters": {
                    "query": "查询文本",
                    "top_k": "返回结果数量"
                }
            },
            "get_weather": {
                "name": "get_weather",
                "description": "获取天气信息",
                "parameters": {
                    "location": "城市名称"
                }
            },
            "calculate": {
                "name": "calculate",
                "description": "执行数学计算",
                "parameters": {
                    "expression": "数学表达式"
                }
            }
        }
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """
        获取所有工具
        
        Returns:
            List[Dict[str, Any]]: 工具列表
        """
        return list(self.tools.values())
    
    def get_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        获取指定工具
        
        Args:
            tool_name: 工具名称
        
        Returns:
            Optional[Dict[str, Any]]: 工具信息
        """
        return self.tools.get(tool_name)
    
    def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """
        执行工具
        
        Args:
            tool_name: 工具名称
            tool_input: 工具输入
        
        Returns:
            Any: 工具执行结果
        """
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"工具不存在: {tool_name}")
        
        # 这里应该实现实际的工具执行逻辑
        # 现在返回模拟结果
        if tool_name == "search_documents":
            return f"搜索结果: {tool_input.get('query', '')}"
        elif tool_name == "get_weather":
            return f"天气信息: {tool_input.get('location', '')}，晴天"
        elif tool_name == "calculate":
            return f"计算结果: {tool_input.get('expression', '')} = 42"
        else:
            return f"工具执行: {tool_name}"


# 全局单例工具注册表实例
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """
    获取全局工具注册表实例
    
    Returns:
        ToolRegistry: 工具注册表实例
    """
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
```

**函数/方法详细说明：**

1. **ToolRegistry.__init__(self)**
   - **功能**：初始化工具注册表
   - **参数**：无
   - **使用场景**：创建工具注册表实例，注册可用的工具

2. **ToolRegistry.get_tools(self)**
   - **功能**：获取所有可用工具
   - **参数**：无
   - **返回值**：`List[Dict[str, Any]]` - 工具列表
   - **使用场景**：查看智能代理可以使用的所有工具

3. **ToolRegistry.get_tool(self, tool_name: str)**
   - **功能**：获取指定的工具
   - **参数**：
     - `tool_name`：工具名称
   - **返回值**：`Optional[Dict[str, Any]]` - 工具信息
   - **使用场景**：获取特定工具的详细信息

4. **ToolRegistry.execute_tool(self, tool_name: str, tool_input: Dict[str, Any])**
   - **功能**：执行指定的工具
   - **参数**：
     - `tool_name`：工具名称
     - `tool_input`：工具输入
   - **返回值**：`Any` - 工具执行结果
   - **使用场景**：调用工具执行特定任务

5. **get_tool_registry()**
   - **功能**：获取全局工具注册表实例
   - **参数**：无
   - **返回值**：`ToolRegistry` - 工具注册表实例
   - **使用场景**：在应用的不同部分获取共享的工具注册表实例

## 前端模块详细分析

### 1. 主应用 (App.jsx)

```jsx
import { useState } from 'react'
import ChatWindow from './components/ChatWindow'
import RAGPanel from './components/RAGPanel'

export default function App() {
  const [activeTab, setActiveTab] = useState('chat')

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-gray-800 mb-2">
            ChainMind
          </h1>
          <p className="text-gray-600">本地AI知识库问答系统</p>
        </div>
        
        <div className="bg-white rounded-xl shadow-lg overflow-hidden">
          <div className="tabs">
            <button 
              onClick={() => setActiveTab('chat')}
              className={`tab ${activeTab === 'chat' ? 'active' : 'inactive'}`}
            >
              💬 聊天
            </button>
            <button 
              onClick={() => setActiveTab('rag')}
              className={`tab ${activeTab === 'rag' ? 'active' : 'inactive'}`}
            >
              📚 RAG
            </button>
          </div>
          
          <div className="p-4 md:p-6">
            {activeTab === 'chat' && <ChatWindow />}
            {activeTab === 'rag' && <RAGPanel />}
          </div>
        </div>
        
        <div className="mt-6 text-center text-sm text-gray-500">
          <p>Powered by FastAPI + Ollama + LangChain</p>
        </div>
      </div>
    </div>
  )
}
```

**函数/方法详细说明：**

1. **App()**
   - **功能**：主应用组件，管理标签页切换和整体布局
   - **状态**：
     - `activeTab`：当前活动的标签页，默认为'chat'
   - **使用场景**：应用的主入口，控制不同功能面板的显示

### 2. 上传面板 (UploadPanel.jsx)

```jsx
import { useState } from 'react'

export default function UploadPanel() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [dragOver, setDragOver] = useState(false)

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      setResult(null)
    }
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setDragOver(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    setDragOver(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile) {
      setFile(droppedFile)
      setResult(null)
    }
  }

  const handleUpload = async () => {
    if (!file) return

    setUploading(true)
    setResult(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 30000) // 30秒超时
      
      const response = await fetch('/api/upload/file', {
        method: 'POST',
        body: formData,
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`上传失败: ${response.status} ${errorText}`)
      }

      const data = await response.json()
      console.log('上传成功:', data)
      setResult({
        success: true,
        data
      })
      setFile(null)
    } catch (error) {
      console.error('上传错误:', error)
      setResult({
        success: false,
        error: error.message
      })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className={`border-2 border-dashed rounded-xl p-6 mb-6 ${dragOver ? 'bg-blue-50 border-blue-300' : 'bg-white border-gray-300'}`}>
      <h3 className="text-xl font-semibold mb-4">📤 文档上传</h3>
      
      {/* 拖拽区域 */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-8 text-center mb-4 cursor-pointer bg-gray-50 transition-colors ${dragOver ? 'border-primary bg-blue-50' : 'border-gray-300'}`}
        onClick={() => document.getElementById('file-input').click()}
      >
        <input
          id="file-input"
          type="file"
          accept=".txt,.md,.pdf"
          onChange={handleFileChange}
          className="hidden"
        />
        <div className="text-5xl mb-3">📁</div>
        <div className="text-gray-700">
          拖拽文件到此处，或 <span className="text-primary font-medium">点击选择</span>
        </div>
        <div className="text-xs text-gray-500 mt-2">
          支持 .txt, .md, .pdf 文件（最大 10MB）
        </div>
      </div>

      {/* 已选文件 */}
      {file && (
        <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg mb-4">
          <span className="text-gray-700">📄 {file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
          <button
            onClick={() => setFile(null)}
            className="text-gray-400 hover:text-gray-600 text-lg"
          >
            ✕
          </button>
        </div>
      )}

      {/* 上传按钮 */}
      <button
        onClick={() => {
          if (!file && !uploading) {
            // 如果还没有选择文件，打开文件选择对话框
            const el = document.getElementById('file-input')
            if (el) el.click()
            return
          }
          handleUpload()
        }}
        disabled={uploading}
        className={`btn btn-primary w-full py-3 ${uploading ? 'bg-gray-400 cursor-not-allowed' : (file ? 'bg-green-600 hover:bg-green-700' : 'bg-yellow-500 hover:bg-yellow-600')}`}
      >
        {uploading ? (
          <div className="flex items-center justify-center space-x-2">
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            <span>上传中...</span>
          </div>
        ) : (file ? '上传并处理' : '选择文件并上传')}
      </button>

      {/* 结果显示 */}
      {result && (
        <div className={`mt-4 p-4 rounded-lg ${result.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
          {result.success ? (
            <>
              <strong className="font-semibold">✅ 上传成功！</strong>
              <div className="mt-2 text-sm space-y-1">
                <div>📄 文件名：{result.data.file_name}</div>
                <div>📊 文件大小：{(result.data.file_size / 1024).toFixed(1)} KB</div>
                <div>📑 切分块数：{result.data.total_chunks}</div>
                <div>🗃️ 已存入向量库：{result.data.vector_stored ? '是' : '否'}</div>
              </div>
            </>
          ) : (
            <>
              <strong className="font-semibold">❌ 上传失败</strong>
              <div>{result.error}</div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
```

**函数/方法详细说明：**

1. **UploadPanel()**
   - **功能**：文档上传面板组件，支持文件选择和拖拽上传
   - **状态**：
     - `file`：当前选择的文件
     - `uploading`：是否正在上传
     - `result`：上传结果
     - `dragOver`：是否有文件拖拽到区域
   - **使用场景**：用于用户上传文档到系统

2. **handleFileChange(e)**
   - **功能**：处理文件选择事件
   - **参数**：
     - `e`：事件对象
   - **使用场景**：当用户通过文件选择对话框选择文件时触发

3. **handleDragOver(e)**
   - **功能**：处理文件拖拽进入事件
   - **参数**：
     - `e`：事件对象
   - **使用场景**：当用户拖拽文件到上传区域时触发

4. **handleDragLeave(e)**
   - **功能**：处理文件拖拽离开事件
   - **参数**：
     - `e`：事件对象
   - **使用场景**：当用户拖拽文件离开上传区域时触发

5. **handleDrop(e)**
   - **功能**：处理文件拖拽释放事件
   - **参数**：
     - `e`：事件对象
   - **使用场景**：当用户在上传区域释放文件时触发

6. **handleUpload()**
   - **功能**：处理文件上传逻辑
   - **使用场景**：当用户点击上传按钮时触发，发送文件到后端处理

### 3. RAG面板 (RAGPanel.jsx)

```jsx
import { useState } from 'react'
import UploadPanel from './UploadPanel'

export default function RAGPanel() {
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(5)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [showUpload, setShowUpload] = useState(false)

  const handleSearch = async () => {
    if (!query.trim() || loading) return

    setLoading(true)
    setResult(null)

    try {
      const response = await fetch('/api/rag/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query,
          top_k: topK
        })
      })

      const data = await response.json()
      setResult(data)
    } catch (error) {
      setResult({
        answer: '搜索失败：' + error.message,
        sources: []
      })
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSearch()
    }
  }

  return (
    <div className="space-y-4">
      {/* 上传按钮 */}
      <div className="flex items-center space-x-3">
        <button 
          onClick={() => {
            // 切换显示并在展开时自动打开文件选择对话框
            setShowUpload((prev) => {
              const next = !prev
              if (!prev && next) {
                // 等待面板渲染后触发文件选择
                setTimeout(() => {
                  const el = document.getElementById('file-input')
                  if (el) el.click()
                }, 80)
              }
              return next
            })
          }}
          className="btn btn-primary bg-green-600 hover:bg-green-700"
        >
          📤 {showUpload ? '收起上传' : '上传文档到知识库'}
        </button>
        <span className="text-sm text-gray-600">
          上传文档后，可以基于文档内容进行问答
        </span>
      </div>

      {/* 上传面板 */}
      {showUpload && <UploadPanel />}

      {/* 搜索框 */}
      <div className="space-y-3">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="输入搜索问题..."
          disabled={loading}
          className="input-field h-20 resize-none"
        />
        <div className="flex items-center space-x-4">
          <label className="flex items-center space-x-2">
            <span className="text-gray-700">检索数量：</span>
            <select 
              value={topK} 
              onChange={(e) => setTopK(Number(e.target.value))}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value={3}>3</option>
              <option value={5}>5</option>
              <option value={10}>10</option>
            </select>
          </label>
          {/* 搜索按钮 */}
          <button
            onClick={handleSearch}
            disabled={loading || !query.trim()}
            className="btn bg-primary text-white px-6 py-2 rounded-md font-medium hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? '搜索中...' : '🔍 RAG 搜索'}
          </button>
        </div>
      </div>

      {/* 结果显示 */}
      {result && (
        <div className="space-y-4">
          {/* AI 回答 */}
          <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
            <div className="font-bold mb-2 text-primary">
              🤖 AI 回答
            </div>
            <pre className="whitespace-pre-wrap font-sans m-0">
              {result.answer}
            </pre>
          </div>

          {/* 参考来源 */}
          {result.sources && result.sources.length > 0 && (
            <div>
              <div className="font-bold mb-3 text-gray-600">
                📚 参考来源 ({result.sources.length} 条)
              </div>
              <div className="space-y-3">
                {result.sources.map((source, index) => (
                  <div key={index} className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                    <div className="font-bold mb-2 text-green-600">
                      📄 {source.filename}
                      {source.distance !== null && (
                        <span className="font-normal text-gray-500 text-sm ml-2">
                          相似度: {(1 - source.distance).toFixed(2)}
                        </span>
                      )}
                    </div>
                    <div className="text-sm text-gray-700">
                      {source.content}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(!result.sources || result.sources.length === 0) && (
            <div className="p-6 text-center text-gray-400 bg-gray-50 rounded-lg">
              未找到相关文档，请先上传文档到知识库
            </div>
          )}
        </div>
      )}
    </div>
  )
}
```

**函数/方法详细说明：**

1. **RAGPanel()**
   - **功能**：RAG搜索面板组件，用于基于文档内容进行搜索
   - **状态**：
     - `query`：搜索查询文本
     - `topK`：返回结果数量
     - `loading`：是否正在搜索
     - `result`：搜索结果
     - `showUpload`：是否显示上传面板
   - **使用场景**：用于用户基于上传的文档进行RAG搜索

2. **handleSearch()**
   - **功能**：处理搜索请求
   - **使用场景**：当用户点击搜索按钮时触发，发送查询到后端

3. **handleKeyPress(e)**
   - **功能**：处理键盘回车事件
   - **参数**：
     - `e`：事件对象
   - **使用场景**：当用户在搜索框中按下回车键时触发搜索

### 4. 聊天窗口 (ChatWindow.jsx)

```jsx
import { useState } from 'react'
import UploadPanel from './UploadPanel'

export default function ChatWindow() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId] = useState(() => 'session_' + Math.random().toString(36).substr(2, 9))
  const [useRag, setUseRag] = useState(true)
  const [showUpload, setShowUpload] = useState(false)

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    setLoading(true)

    // 添加用户消息
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])

    try {
      const response = await fetch('/api/chat/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: userMessage,
          session_id: sessionId,
          use_rag: useRag,
          top_k: 3
        })
      })

      const data = await response.json()
      
      // 添加助手消息
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: data.answer,
        sources: data.sources || []
      }])
    } catch (error) {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: '抱歉，发生了错误：' + error.message 
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="space-y-4">
      {/* 上传按钮 */}
      <div className="flex items-center space-x-4">
        <button 
          onClick={() => setShowUpload(!showUpload)}
          className="btn btn-primary bg-green-600 hover:bg-green-700"
        >
          📤 {showUpload ? '收起上传' : '上传文档'}
        </button>
        <label className="flex items-center space-x-2 cursor-pointer">
          <input 
            type="checkbox" 
            checked={useRag} 
            onChange={(e) => setUseRag(e.target.checked)}
            className="rounded text-primary focus:ring-primary"
          />
          <span className="text-gray-700">启用 RAG 增强</span>
        </label>
      </div>

      {/* 上传面板 */}
      {showUpload && <UploadPanel />}

      {/* 消息列表 */}
      <div className="border border-gray-200 rounded-lg p-4 h-[400px] overflow-y-auto bg-gray-50">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-gray-400">
            <p className="text-center">开始对话吧！上传文档可以启用 RAG 增强</p>
          </div>
        )}
        
        {messages.map((msg, index) => (
          <div key={index} className="mb-4">
            <div className="font-bold mb-1">
              <span className={msg.role === 'user' ? 'text-primary' : 'text-green-600'}>
                {msg.role === 'user' ? '👤 你' : '🤖 助手'}
              </span>
            </div>
            <div className={`p-3 rounded-lg ${msg.role === 'user' ? 'bg-blue-50 border border-blue-200' : 'bg-white border border-gray-200'}`}>
              <pre className="whitespace-pre-wrap font-sans m-0">{msg.content}</pre>
            </div>
            {msg.sources && msg.sources.length > 0 && (
              <div className="mt-2 text-sm text-gray-600">
                <strong>参考来源：</strong>
                <div className="mt-1 space-y-2">
                  {msg.sources.map((s, i) => (
                    <div key={i} className="p-2 bg-gray-100 rounded-md">
                      📄 {s.filename}: {s.content.substring(0, 100)}...
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
        
        {loading && (
          <div className="flex items-center justify-center py-4">
            <div className="flex space-x-2">
              <div className="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
              <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
            </div>
          </div>
        )}
      </div>

      {/* 输入框 */}
      <div className="flex space-x-3">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="输入你的问题..."
          disabled={loading}
          className="flex-1 input-field h-16 resize-none"
        />
        <button
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          className={`btn btn-primary h-16 px-6 ${loading || !input.trim() ? 'bg-gray-400 cursor-not-allowed' : 'bg-primary hover:bg-blue-600'}`}
        >
          {loading ? '发送中...' : '发送'}
        </button>
      </div>
    </div>
  )
}
```

**函数/方法详细说明：**

1. **ChatWindow()**
   - **功能**：聊天窗口组件，用于与AI进行对话
   - **状态**：
     - `messages`：聊天消息列表
     - `input`：输入框内容
     - `loading`：是否正在发送消息
     - `sessionId`：会话ID
     - `useRag`：是否启用RAG增强
     - `showUpload`：是否显示上传面板
   - **使用场景**：用于用户与AI进行对话，支持RAG增强

2. **sendMessage()**
   - **功能**：发送消息到后端
   - **使用场景**：当用户点击发送按钮或按下回车键时触发

3. **handleKeyPress(e)**
   - **功能**：处理键盘回车事件
   - **参数**：
     - `e`：事件对象
   - **使用场景**：当用户在输入框中按下回车键时触发发送消息

### 5. 聊天消息 (ChatMessage.jsx)

```jsx
export default function ChatMessage({ message, isUser }) {
    return (
        <div style={{
            display: 'flex',
            justifyContent: isUser ? 'flex-end' : 'flex-start',
            animation: 'fadeIn 0.3s ease'
        }}>
            {!isUser && (
                <div style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '14px',
                    marginRight: '10px',
                    flexShrink: 0
                }}>
                    🤖
                </div>
            )}
            
            <div style={{
                maxWidth: '70%',
                padding: '14px 18px',
                borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                background: isUser 
                    ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' 
                    : 'rgba(255, 255, 255, 0.08)',
                color: isUser ? '#fff' : 'rgba(255, 255, 255, 0.9)',
                fontSize: '14px',
                lineHeight: '1.5',
                boxShadow: isUser ? 'none' : '0 2px 8px rgba(0, 0, 0, 0.2)',
                wordBreak: 'break-word',
                whiteSpace: 'pre-wrap'
            }}>
                {message}
            </div>
            
            {isUser && (
                <div style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '14px',
                    marginLeft: '10px',
                    flexShrink: 0
                }}>
                    👤
                </div>
            )}
            
            <style>{`
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    );
}
```

**函数/方法详细说明：**

1. **ChatMessage({ message, isUser })**
   - **功能**：聊天消息组件，用于显示单个聊天消息
   - **参数**：
     - `message`：消息内容
     - `isUser`：是否为用户消息
   - **使用场景**：在聊天窗口中显示用户和助手的消息

## 项目运行与部署

### 后端运行

1. 进入后端目录
2. 安装依赖：`pip install -r requirements.txt`
3. 启动服务：`uvicorn main:app --host 0.0.0.0 --port 8000 --reload`

### 前端运行

1. 进入前端目录
2. 安装依赖：`npm install`
3. 启动服务：`npm run dev`

### 访问地址

- 前端：http://localhost:3000
- 后端API：http://localhost:8000

## 项目优化建议

1. **性能优化**
   - 实现文档上传的分片上传，支持大文件
   - 优化向量存储，使用更高效的向量数据库
   - 前端添加缓存机制，减少重复请求

2. **功能扩展**
   - 添加用户认证系统
   - 支持更多文件格式
   - 实现文档管理功能（分类、标签等）
   - 添加多语言支持

3. **安全性**
   - 实现文件类型验证和病毒扫描
   - 添加API访问控制
   - 实现数据加密存储

4. **用户体验**
   - 添加文件上传进度条
   - 实现聊天消息的历史记录
   - 添加深色模式
   - 优化移动端适配

## 总结

ChainMind是一个基于RAG技术的智能知识库系统，它提供了以下核心功能：

- 文档上传和处理（支持.txt、.md、.pdf格式）
- 基于文档内容的智能问答
- RAG检索增强功能
- 多轮对话和记忆功能
- 现代化的Web界面

项目采用前后端分离架构，后端使用FastAPI构建，前端使用React + Tailwind CSS开发。通过本技术文档，您可以了解项目的整体架构、模块功能及代码实现细节，为后续的开发和维护提供参考。