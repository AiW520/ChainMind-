"""
Memory 路由
提供会话历史管理接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from ..services.memory import get_memory

router = APIRouter(prefix="/memory", tags=["记忆管理"])


class MessageItem(BaseModel):
    """消息项"""
    role: str
    content: str
    timestamp: Optional[str] = None


class HistoryResponse(BaseModel):
    """历史记录响应"""
    session_id: str
    messages: List[MessageItem]
    count: int


class SessionSummary(BaseModel):
    """会话摘要"""
    session_id: str
    message_count: int
    first_message: Optional[MessageItem] = None
    last_message: Optional[MessageItem] = None


@router.get("/{session_id}", response_model=HistoryResponse)
async def get_chat_history(session_id: str, limit: Optional[int] = None):
    """
    获取会话历史
    
    - **session_id**: 会话ID
    - **limit**: 限制返回的消息数量（可选）
    """
    memory = get_memory()
    messages = memory.get_history(session_id, limit=limit)
    
    return HistoryResponse(
        session_id=session_id,
        messages=[MessageItem(**msg) for msg in messages],
        count=len(messages)
    )


@router.delete("/{session_id}")
async def clear_chat_history(session_id: str):
    """
    清除会话历史
    
    - **session_id**: 会话ID
    """
    memory = get_memory()
    success = memory.clear_history(session_id)
    
    if success:
        return {"status": "success", "message": f"会话 {session_id} 已清除"}
    else:
        return {"status": "success", "message": f"会话 {session_id} 不存在或已清除"}


@router.get("/")
async def list_sessions():
    """
    列出所有会话
    """
    memory = get_memory()
    sessions = memory.get_all_sessions()
    
    summaries = []
    for session_id in sessions:
        summary = memory.get_conversation_summary(session_id)
        summaries.append(SessionSummary(
            session_id=session_id,
            message_count=summary["message_count"],
            first_message=MessageItem(**summary["first_message"]) if summary["first_message"] else None,
            last_message=MessageItem(**summary["last_message"]) if summary["last_message"] else None
        ))
    
    return {
        "sessions": summaries,
        "total": len(sessions)
    }


@router.post("/{session_id}/add")
async def add_message(session_id: str, role: str, content: str):
    """
    添加消息到会话历史
    
    - **session_id**: 会话ID
    - **role**: 角色 (user/assistant)
    - **content**: 消息内容
    """
    if role not in ["user", "assistant"]:
        raise HTTPException(status_code=400, detail="role 必须是 'user' 或 'assistant'")
    
    memory = get_memory()
    memory.add_message(session_id, role, content)
    
    return {"status": "success", "message": "消息已添加"}
