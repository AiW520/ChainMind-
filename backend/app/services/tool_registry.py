"""
工具注册器
管理所有可用的工具，支持动态注册和调用
"""
from typing import Dict, Callable, Any, Optional
from datetime import datetime
import math
import re


class ToolRegistry:
    """工具注册表管理器"""
    
    def __init__(self):
        """初始化工具注册表"""
        self._tools: Dict[str, Callable] = {}
        self._tool_schemas: Dict[str, dict] = {}
        self._register_builtin_tools()
    
    def _register_builtin_tools(self):
        """注册内置工具"""
        # 时间工具
        self.register(
            name="get_current_time",
            func=self._get_current_time,
            description="获取当前时间",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
        
        # 计算器工具
        self.register(
            name="calculator",
            func=self._calculator,
            description="执行数学计算，支持加减乘除和常见数学函数",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式，如 '2+3*4' 或 'sqrt(16)'"
                    }
                },
                "required": ["expression"]
            }
        )
        
        # 搜索工具（模拟）
        self.register(
            name="search",
            func=self._search,
            description="搜索互联网信息",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词"
                    }
                },
                "required": ["query"]
            }
        )
    
    def register(
        self,
        name: str,
        func: Callable,
        description: str,
        parameters: dict
    ) -> None:
        """
        注册工具
        
        Args:
            name: 工具名称
            func: 工具函数
            description: 工具描述
            parameters: 工具参数schema
        """
        self._tools[name] = func
        self._tool_schemas[name] = {
            "name": name,
            "description": description,
            "parameters": parameters
        }
    
    def get_tool(self, name: str) -> Optional[Callable]:
        """
        获取工具函数
        
        Args:
            name: 工具名称
        
        Returns:
            工具函数或None
        """
        return self._tools.get(name)
    
    def list_tools(self) -> list:
        """
        列出所有可用工具
        
        Returns:
            工具列表
        """
        return list(self._tools.keys())
    
    def get_tool_schemas(self) -> list:
        """
        获取所有工具的schema定义
        
        Returns:
            工具schema列表
        """
        return list(self._tool_schemas.values())
    
    def call_tool(self, name: str, **kwargs) -> Any:
        """
        调用工具
        
        Args:
            name: 工具名称
            **kwargs: 工具参数
        
        Returns:
            工具执行结果
        """
        tool = self.get_tool(name)
        if tool is None:
            return {"error": f"Tool '{name}' not found"}
        
        try:
            result = tool(**kwargs)
            return result
        except Exception as e:
            return {"error": str(e)}
    
    # ============== 内置工具实现 ==============
    
    def _get_current_time(self) -> dict:
        """获取当前时间"""
        now = datetime.now()
        return {
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "weekday": now.strftime("%A")
        }
    
    def _calculator(self, expression: str) -> dict:
        """
        数学计算器
        
        Args:
            expression: 数学表达式
        """
        try:
            # 安全检查：只允许数字和数学运算符
            safe_expr = re.sub(r'[^0-9+\-*/().sqrtlogsinco^tanpi\s]', '', expression)
            
            # 替换常见数学函数
            safe_expr = safe_expr.replace('^', '**')
            safe_expr = safe_expr.replace('sqrt', 'math.sqrt')
            safe_expr = safe_expr.replace('log', 'math.log')
            safe_expr = safe_expr.replace('sin', 'math.sin')
            safe_expr = safe_expr.replace('cos', 'math.cos')
            safe_expr = safe_expr.replace('tan', 'math.tan')
            safe_expr = safe_expr.replace('pi', 'math.pi')
            
            result = eval(safe_expr, {"__builtins__": {"math": math}, "math": math})
            return {
                "expression": expression,
                "result": result,
                "formatted": f"{expression} = {result}"
            }
        except Exception as e:
            return {
                "expression": expression,
                "error": f"计算错误: {str(e)}"
            }
    
    def _search(self, query: str) -> dict:
        """
        模拟搜索功能
        
        注意：这是模拟实现，实际生产中应接入真实搜索API
        """
        return {
            "query": query,
            "result": f"[模拟搜索结果] 关于 '{query}' 的信息，请访问搜索引擎获取最新内容",
            "note": "这是模拟搜索结果，实际使用时需要接入真实搜索API"
        }


# 全局工具注册表
_registry = None

def get_tool_registry() -> ToolRegistry:
    """获取工具注册表实例"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
