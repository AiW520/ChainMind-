"""
Agent 服务
基于 ReAct 模式的智能代理
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
import httpx

from .tool_registry import get_tool_registry
from .memory import get_memory
from ..config import OLLAMA_BASE_URL, OLLAMA_MODEL


class AgentConfig(BaseModel):
    """Agent配置"""
    model: str = OLLAMA_MODEL
    base_url: str = OLLAMA_BASE_URL
    max_iterations: int = 5
    verbose: bool = False


class AgentThought(BaseModel):
    """Agent思考步骤"""
    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None


class Agent:
    """
    智能代理基类
    基于 ReAct (Reasoning + Acting) 模式
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        """
        初始化Agent
        
        Args:
            config: Agent配置
        """
        self.config = config or AgentConfig()
        self.tool_registry = get_tool_registry()
        self.memory = get_memory()
        self._init_tools()
    
    def _init_tools(self):
        """初始化可用工具"""
        self.available_tools = self.tool_registry.get_tool_schemas()
    
    def _build_system_prompt(self) -> str:
        """
        构建系统提示词
        
        Returns:
            系统提示词
        """
        tools_json = self._format_tools_for_prompt()
        
        return f"""你是一个智能助手，可以通过工具来完成任务。

## 可用工具
{tools_json}

## 工作模式
1. 分析用户问题，决定是否需要使用工具
2. 如果需要使用工具，按以下格式输出：
   Thought: 你需要做什么
   Action: 工具名称
   Action Input: {{"参数名": "参数值"}}
3. 等待观察结果(由系统提供)
4. 重复步骤2-3直到完成任务
5. 最终输出你的回答

## 输出格式
- 使用工具时：
  Thought: xxx
  Action: xxx
  Action Input: {{xxx}}

- 最终回答时：
  Final Answer: xxx
"""
    
    def _format_tools_for_prompt(self) -> str:
        """
        格式化工具信息供提示词使用
        
        Returns:
            工具描述字符串
        """
        lines = []
        for tool in self.available_tools:
            name = tool["name"]
            desc = tool["description"]
            params = tool.get("parameters", {})
            required = params.get("required", [])
            
            lines.append(f"- {name}: {desc}")
            if required:
                lines.append(f"  必填参数: {', '.join(required)}")
        
        return "\n".join(lines)
    
    async def _call_llm(self, prompt: str) -> str:
        """
        调用LLM生成回答
        
        Args:
            prompt: 提示词
        
        Returns:
            LLM输出
        """
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.config.base_url}/api/generate",
                    json={
                        "model": self.config.model,
                        "prompt": prompt,
                        "stream": False
                    }
                )
                result = response.json()
                return result.get("response", "")
        except Exception as e:
            return f"LLM调用失败: {str(e)}"
    
    def _parse_llm_output(self, output: str) -> Optional[Dict[str, Any]]:
        """
        解析LLM输出，提取Thought/Action等信息
        
        Args:
            output: LLM原始输出
        
        Returns:
            解析后的字典
        """
        result = {
            "thought": "",
            "action": None,
            "action_input": None,
            "is_final": False
        }
        
        lines = output.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("Thought:"):
                result["thought"] = line[8:].strip()
            elif line.startswith("Action:"):
                result["action"] = line[7:].strip()
            elif line.startswith("Action Input:"):
                # 尝试解析JSON
                json_str = line[13:].strip()
                try:
                    result["action_input"] = eval(json_str)
                except:
                    result["action_input"] = {"raw": json_str}
            elif line.startswith("Final Answer:"):
                result["is_final"] = True
                result["final_answer"] = line[13:].strip()
        
        return result
    
    async def run(self, query: str, session_id: str = "default") -> Dict[str, Any]:
        """
        运行Agent处理查询
        
        Args:
            query: 用户查询
            session_id: 会话ID
        
        Returns:
            处理结果
        """
        # 添加用户消息到记忆
        self.memory.add_message(session_id, "user", query)
        
        # 构建初始提示词
        system_prompt = self._build_system_prompt()
        
        # 获取对话历史
        history = self.memory.get_history(session_id, limit=10)
        history_context = self._format_history(history)
        
        full_prompt = f"{system_prompt}\n\n{history_context}\n\n用户问题: {query}"
        
        # ReAct循环
        thoughts = []
        iteration = 0
        final_answer = None
        
        while iteration < self.config.max_iterations:
            iteration += 1
            
            # 调用LLM
            llm_output = await self._call_llm(full_prompt)
            
            if self.config.verbose:
                print(f"[Iteration {iteration}] LLM Output:\n{llm_output}\n")
            
            # 解析输出
            parsed = self._parse_llm_output(llm_output)
            
            if parsed.get("is_final"):
                final_answer = parsed.get("final_answer", llm_output)
                break
            
            # 执行工具调用
            if parsed.get("action"):
                tool_name = parsed["action"]
                tool_input = parsed.get("action_input", {})
                
                # 记录思考过程
                thought = AgentThought(
                    thought=parsed.get("thought", ""),
                    action=tool_name,
                    action_input=tool_input
                )
                
                # 调用工具
                tool_result = self.tool_registry.call_tool(tool_name, **tool_input)
                thought.observation = str(tool_result)
                thoughts.append(thought)
                
                # 将工具结果添加到上下文
                full_prompt += f"\n\n{llm_output}\n观察结果: {tool_result}"
            else:
                # 没有解析到action，直接作为最终回答
                final_answer = llm_output
                break
        
        if final_answer is None:
            final_answer = "抱歉，我无法完成这个任务。"
        
        # 添加助手回复到记忆
        self.memory.add_message(session_id, "assistant", final_answer)
        
        return {
            "answer": final_answer,
            "thoughts": [t.dict() for t in thoughts],
            "iterations": iteration,
            "used_tools": [t.action for t in thoughts if t.action]
        }
    
    def _format_history(self, history: List[dict]) -> str:
        """
        格式化对话历史
        
        Args:
            history: 历史消息列表
        
        Returns:
            格式化后的历史字符串
        """
        if not history:
            return ""
        
        lines = ["\n## 对话历史"]
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            lines.append(f"{role.upper()}: {content}")
        
        return "\n".join(lines)


def get_agent(config: Optional[AgentConfig] = None) -> Agent:
    """
    获取Agent实例
    
    Args:
        config: Agent配置
    
    Returns:
        Agent实例
    """
    return Agent(config)
