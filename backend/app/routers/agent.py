"""
Agent 路由
提供智能代理对话接口
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from ..services.agent import Agent, AgentConfig, get_agent
from ..services.tool_registry import get_tool_registry

router = APIRouter(prefix="/agent", tags=["智能代理"])


class AgentChatRequest(BaseModel):
    """Agent对话请求"""
    query: str
    session_id: str = "default"
    model: Optional[str] = None
    max_iterations: int = 5
    verbose: bool = False


class ThoughtItem(BaseModel):
    """思考步骤"""
    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None


class AgentChatResponse(BaseModel):
    """Agent对话响应"""
    answer: str
    thoughts: List[ThoughtItem]
    iterations: int
    used_tools: List[str]


class ToolInfo(BaseModel):
    """工具信息"""
    name: str
    description: str
    parameters: dict


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(request: AgentChatRequest):
    """
    Agent智能对话
    
    - 支持ReAct模式的推理和工具调用
    - 可以自动使用内置工具（计算器、时间查询等）
    - 自动记忆对话历史
    
    - **query**: 用户问题
    - **session_id**: 会话ID（用于记忆上下文）
    - **model**: LLM模型名称（可选，默认使用配置）
    - **max_iterations**: 最大迭代次数（默认5）
    - **verbose**: 是否输出详细推理过程
    """
    # 构建配置
    config = AgentConfig(
        max_iterations=request.max_iterations,
        verbose=request.verbose
    )
    if request.model:
        config.model = request.model
    
    # 创建Agent并运行
    agent = get_agent(config)
    result = await agent.run(request.query, request.session_id)
    
    return AgentChatResponse(
        answer=result["answer"],
        thoughts=[ThoughtItem(**t) for t in result["thoughts"]],
        iterations=result["iterations"],
        used_tools=result["used_tools"]
    )


@router.get("/tools")
async def list_tools():
    """
    列出所有可用的工具
    """
    registry = get_tool_registry()
    tools = registry.get_tool_schemas()
    
    return {
        "tools": tools,
        "count": len(tools)
    }


@router.post("/tools/{tool_name}/call")
async def call_tool(tool_name: str, **kwargs):
    """
    直接调用指定工具
    
    - **tool_name**: 工具名称
    - **kwargs**: 工具参数
    """
    registry = get_tool_registry()
    result = registry.call_tool(tool_name, **kwargs)
    
    return {
        "tool": tool_name,
        "input": kwargs,
        "output": result
    }
