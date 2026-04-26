"""
Memory 服务
提供会话历史管理功能
"""
from typing import Dict, List, Optional
from datetime import datetime

"""
注意：避免在模块导入阶段引入 routers.chat，以免产生循环依赖。
在需要同步时在函数内部再导入。
"""


class ConversationBufferMemory:
    """
    对话缓冲记忆
    管理会话历史，支持 session_id 隔离
    """
    
    def __init__(self):
        """初始化记忆管理器"""
        self.sessions: Dict[str, List[dict]] = {}
    
    def add_message(self, session_id: str, role: str, content: str) -> None:
        """
        添加消息到会话历史
        
        Args:
            session_id: 会话ID
            role: 角色 (user/assistant)
            content: 消息内容
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        
        self.sessions[session_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_history(self, session_id: str, limit: Optional[int] = None) -> List[dict]:
        """
        获取会话历史
        
        Args:
            session_id: 会话ID
            limit: 限制返回的消息数量（最近N条）
        
        Returns:
            消息历史列表
        """
        history = self.sessions.get(session_id, [])
        if limit is not None:
            return history[-limit:]
        return history
    
    def clear_history(self, session_id: str) -> bool:
        """
        清除会话历史
        
        Args:
            session_id: 会话ID
        
        Returns:
            是否成功清除
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def get_all_sessions(self) -> List[str]:
        """
        获取所有会话ID
        
        Returns:
            会话ID列表
        """
        return list(self.sessions.keys())
    
    def get_conversation_summary(self, session_id: str) -> dict:
        """
        获取会话摘要
        
        Args:
            session_id: 会话ID
        
        Returns:
            包含消息数量等摘要信息
        """
        history = self.get_history(session_id)
        return {
            "session_id": session_id,
            "message_count": len(history),
            "first_message": history[0] if history else None,
            "last_message": history[-1] if history else None
        }


# 全局记忆实例
memory = ConversationBufferMemory()


def get_memory() -> ConversationBufferMemory:
    """获取记忆实例"""
    return memory


def sync_chat_history_to_memory():
    """
    将 chat.py 中的 chat_history 同步到 memory
    保持与现有聊天功能的兼容性
    """
    # 延迟导入以避免循环导入问题
    try:
        from ..routers.chat import chat_history
    except Exception:
        return

    for session_id, messages in chat_history.items():
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                memory.add_message(session_id, "user", content)
            else:
                memory.add_message(session_id, "assistant", content)
