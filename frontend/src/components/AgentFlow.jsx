import { useState } from 'react'

const initialAgents = [
  { id: 1, name: 'Query重写Agent', icon: '🔄', status: 'idle', description: '理解用户意图，优化查询' },
  { id: 2, name: '检索Agent', icon: '🔍', status: 'idle', description: '执行混合向量检索' },
  { id: 3, name: '答案生成Agent', icon: '✨', status: 'idle', description: '基于上下文生成回答' },
  { id: 4, name: '校验Agent', icon: '✅', status: 'idle', description: '验证答案准确性' },
]

export default function AgentFlow() {
  const [agents, setAgents] = useState(initialAgents)
  const [isRunning, setIsRunning] = useState(false)
  const [logs, setLogs] = useState([])
  const [query, setQuery] = useState('')

  const addLog = (message, type = 'info') => {
    const timestamp = new Date().toLocaleTimeString()
    setLogs(prev => [...prev, { message, type, timestamp }])
  }

  const runAgentFlow = async () => {
    if (!query.trim() || isRunning) return

    setIsRunning(true)
    setLogs([])
    setAgents(prev => prev.map(a => ({ ...a, status: 'idle' })))

    try {
      setAgents(prev => prev.map(a =>
        a.id === 1 ? { ...a, status: 'active' } : a
      ))
      addLog('🔄 启动 Query重写Agent...', 'info')
      await new Promise(r => setTimeout(r, 800))
      addLog('✅ Query重写完成，识别意图：知识库问答', 'success')
      setAgents(prev => prev.map(a =>
        a.id === 1 ? { ...a, status: 'completed' } :
        a.id === 2 ? { ...a, status: 'active' } : a
      ))

      addLog('🔍 启动 检索Agent，执行混合检索...', 'info')
      await new Promise(r => setTimeout(r, 1200))
      addLog('📄 检索到 5 个相关文档块', 'success')
      addLog('📊 向量检索: 3个 | BM25: 2个 | Rerank后: 5个', 'info')
      setAgents(prev => prev.map(a =>
        a.id === 2 ? { ...a, status: 'completed' } :
        a.id === 3 ? { ...a, status: 'active' } : a
      ))

      addLog('✨ 启动 答案生成Agent...', 'info')
      await new Promise(r => setTimeout(r, 1500))
      addLog('🤖 正在流式生成回答...', 'info')
      await new Promise(r => setTimeout(r, 1000))
      addLog('📝 回答生成完成 (约 200 字)', 'success')
      setAgents(prev => prev.map(a =>
        a.id === 3 ? { ...a, status: 'completed' } :
        a.id === 4 ? { ...a, status: 'active' } : a
      ))

      addLog('✅ 启动 校验Agent，验证答案准确性...', 'info')
      await new Promise(r => setTimeout(r, 1000))
      addLog('🛡️ 准确性检查通过，幻觉率: 2.3%', 'success')
      addLog('✅ 答案质量评估: 优秀', 'success')
      setAgents(prev => prev.map(a =>
        a.id === 4 ? { ...a, status: 'completed' } : a
      ))

      addLog('🎉 多Agent协作流程执行完成！', 'success')
    } catch (error) {
      addLog(`❌ 错误: ${error.message}`, 'error')
      setAgents(prev => prev.map(a => ({ ...a, status: 'error' })))
    } finally {
      setIsRunning(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-white">多Agent协作流程</h2>
          <p className="text-sm text-gray-400 mt-1">可视化展示Query重写 → 检索 → 生成 → 校验流程</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="card p-6">
            <h3 className="text-lg font-medium text-white mb-4">🔄 Agent执行流程</h3>
            <div className="relative">
              <div className="flex flex-wrap justify-between gap-4">
                {agents.map((agent, index) => (
                  <div key={agent.id} className="flex-1 min-w-[140px]">
                    <div
                      className={`agent-node ${
                        agent.status === 'active' ? 'active animate-pulse' : ''
                      } ${agent.status === 'completed' ? 'completed border-emerald-500' : ''} ${
                        agent.status === 'error' ? 'border-red-500' : ''
                      }`}
                    >
                      <div className="text-3xl mb-2">{agent.icon}</div>
                      <div className="font-medium text-white text-sm">{agent.name}</div>
                      <div className="text-xs text-gray-400 mt-1">{agent.description}</div>
                      <div className="mt-2">
                        {agent.status === 'idle' && (
                          <span className="badge badge-warning">等待</span>
                        )}
                        {agent.status === 'active' && (
                          <span className="badge badge-primary animate-pulse">执行中</span>
                        )}
                        {agent.status === 'completed' && (
                          <span className="badge badge-success">完成</span>
                        )}
                        {agent.status === 'error' && (
                          <span className="badge badge-error">错误</span>
                        )}
                      </div>
                    </div>
                    {index < agents.length - 1 && (
                      <div className="hidden lg:block absolute right-0 top-1/2 transform translate-x-1/2 -translate-y-1/2">
                        <svg className="w-8 h-8 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                        </svg>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="card p-6">
            <h3 className="text-lg font-medium text-white mb-4">💬 测试输入</h3>
            <div className="flex gap-3">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="输入测试问题..."
                className="input-field flex-1"
                disabled={isRunning}
              />
              <button
                onClick={runAgentFlow}
                disabled={isRunning || !query.trim()}
                className="btn btn-primary"
              >
                {isRunning ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin">⏳</span>
                    执行中
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <span>▶</span>
                    启动流程
                  </span>
                )}
              </button>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <h3 className="text-lg font-medium text-white mb-4">📋 执行日志</h3>
          <div className="h-[400px] overflow-y-auto scrollbar-thin space-y-2">
            {logs.length === 0 ? (
              <p className="text-gray-500 text-sm">点击"启动流程"开始执行...</p>
            ) : (
              logs.map((log, index) => (
                <div
                  key={index}
                  className={`text-sm p-2 rounded-lg ${
                    log.type === 'success' ? 'bg-emerald-500/10 text-emerald-400' :
                    log.type === 'error' ? 'bg-red-500/10 text-red-400' :
                    log.type === 'info' ? 'bg-indigo-500/10 text-indigo-400' :
                    'bg-gray-500/10 text-gray-400'
                  }`}
                >
                  <span className="text-xs text-gray-500 mr-2">[{log.timestamp}]</span>
                  {log.message}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="card p-6">
        <h3 className="text-lg font-medium text-white mb-4">🎯 Agent协作说明</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-lg bg-dark-3 border border-gray-700">
            <div className="text-2xl mb-2">🔄</div>
            <div className="font-medium text-white">Query重写Agent</div>
            <div className="text-sm text-gray-400 mt-1">
              理解用户意图，扩展同义词，消除歧义，生成多个查询变体
            </div>
          </div>
          <div className="p-4 rounded-lg bg-dark-3 border border-gray-700">
            <div className="text-2xl mb-2">🔍</div>
            <div className="font-medium text-white">检索Agent</div>
            <div className="text-sm text-gray-400 mt-1">
              执行向量检索+BM25混合检索，使用Rerank模型优化排序
            </div>
          </div>
          <div className="p-4 rounded-lg bg-dark-3 border border-gray-700">
            <div className="text-2xl mb-2">✨</div>
            <div className="font-medium text-white">答案生成Agent</div>
            <div className="text-sm text-gray-400 mt-1">
              基于检索到的上下文，使用Prompt工程生成准确回答
            </div>
          </div>
          <div className="p-4 rounded-lg bg-dark-3 border border-gray-700">
            <div className="text-2xl mb-2">✅</div>
            <div className="font-medium text-white">校验Agent</div>
            <div className="text-sm text-gray-400 mt-1">
              验证答案准确性，检测幻觉，确保引用正确
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
