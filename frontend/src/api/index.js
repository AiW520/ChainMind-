/**
 * API 请求模块
 * 封装所有与后端的交互
 */

const API_BASE = '/api'

// 通用请求函数
async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`
  
  const config = {
    ...options,
    headers: {
      ...options.headers,
    }
  }

  // 如果是 FormData，不需要设置 Content-Type
  if (!(options.body instanceof FormData)) {
    config.headers['Content-Type'] = 'application/json'
  }

  try {
    const response = await fetch(url, config)
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    return await response.json()
  } catch (error) {
    console.error('API request failed:', error)
    throw error
  }
}

// ==================== 上传 API ====================

export const uploadAPI = {
  // 上传单个文件
  uploadFile: async (file) => {
    const formData = new FormData()
    formData.append('file', file)
    
    return request('/upload/file', {
      method: 'POST',
      body: formData
    })
  },

  // 批量上传文件
  uploadMultiple: async (files) => {
    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })
    
    return request('/upload/files', {
      method: 'POST',
      body: formData
    })
  }
}

// ==================== 聊天 API ====================

export const chatAPI = {
  // 发送消息
  sendMessage: async (params) => {
    return request('/chat/', {
      method: 'POST',
      body: JSON.stringify({
        question: params.question,
        session_id: params.session_id || 'default',
        use_rag: params.use_rag !== false,
        top_k: params.top_k || 3
      })
    })
  }
}

// ==================== RAG API ====================

export const ragAPI = {
  // RAG 查询
  query: async (params) => {
    return request('/rag/query', {
      method: 'POST',
      body: JSON.stringify({
        query: params.query,
        top_k: params.top_k || 5
      })
    })
  },

  // 添加文本块
  addChunks: async (params) => {
    return request('/rag/add', {
      method: 'POST',
      body: JSON.stringify({
        chunks: params.chunks,
        filename: params.filename
      })
    })
  }
}

// ==================== Memory API ====================

export const memoryAPI = {
  // 获取历史
  getHistory: async (sessionId, limit) => {
    const endpoint = limit 
      ? `/memory/${sessionId}?limit=${limit}`
      : `/memory/${sessionId}`
    return request(endpoint)
  },

  // 清除历史
  clearHistory: async (sessionId) => {
    return request(`/memory/${sessionId}`, {
      method: 'DELETE'
    })
  },

  // 列出所有会话
  listSessions: async () => {
    return request('/memory/')
  },

  // 添加消息
  addMessage: async (sessionId, role, content) => {
    return request(`/memory/${sessionId}/add`, {
      method: 'POST',
      body: JSON.stringify({ role, content })
    })
  }
}

// ==================== Agent API ====================

export const agentAPI = {
  // Agent 对话
  chat: async (params) => {
    return request('/agent/chat', {
      method: 'POST',
      body: JSON.stringify({
        query: params.query,
        session_id: params.session_id || 'default',
        model: params.model,
        max_iterations: params.max_iterations || 5,
        verbose: params.verbose || false
      })
    })
  },

  // 获取可用工具
  listTools: async () => {
    return request('/agent/tools')
  },

  // 调用工具
  callTool: async (toolName, params) => {
    return request(`/agent/tools/${toolName}/call`, {
      method: 'POST',
      body: JSON.stringify(params)
    })
  }
}

export default {
  upload: uploadAPI,
  chat: chatAPI,
  rag: ragAPI,
  memory: memoryAPI,
  agent: agentAPI
}
