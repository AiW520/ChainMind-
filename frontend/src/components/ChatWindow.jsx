import { useState, useRef, useEffect } from 'react'
import UploadPanel from './UploadPanel'

export default function ChatWindow() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId] = useState(() => 'session_' + Math.random().toString(36).substr(2, 9))
  const [useRag, setUseRag] = useState(true)
  const [showUpload, setShowUpload] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    setLoading(true)

    setMessages(prev => [...prev, { role: 'user', content: userMessage, sources: [] }])

    let assistantMessageId = messages.length + 1

    setMessages(prev => [...prev, {
      role: 'assistant',
      content: '',
      streaming: true,
      sources: []
    }])

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: userMessage,
          session_id: sessionId,
          use_rag: useRag,
          top_k: 3
        })
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let done = false
      let fullResponse = ''
      let sources = []

      while (!done) {
        const { value, done: doneReading } = await reader.read()
        done = doneReading
        if (value) {
          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                if (!data.done) {
                  fullResponse += data.token
                  setMessages(prev => {
                    const newMessages = [...prev]
                    if (newMessages[assistantMessageId]) {
                      newMessages[assistantMessageId] = {
                        ...newMessages[assistantMessageId],
                        content: fullResponse
                      }
                    }
                    return newMessages
                  })
                } else if (data.sources) {
                  sources = data.sources
                }
              } catch (e) {
                console.error('Parse error:', e)
              }
            }
          }
        }
      }

      setMessages(prev => {
        const newMessages = [...prev]
        if (newMessages[assistantMessageId]) {
          newMessages[assistantMessageId] = {
            role: 'assistant',
            content: fullResponse,
            streaming: false,
            sources: sources
          }
        }
        return newMessages
      })
    } catch (error) {
      setMessages(prev => {
        const newMessages = [...prev]
        if (newMessages[assistantMessageId]) {
          newMessages[assistantMessageId] = {
            role: 'assistant',
            content: '抱歉，发生了错误：' + error.message,
            streaming: false,
            sources: []
          }
        }
        return newMessages
      })
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
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setShowUpload(!showUpload)}
            className="btn btn-secondary flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            {showUpload ? '收起上传' : '上传文档'}
          </button>
          <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-400">
            <input
              type="checkbox"
              checked={useRag}
              onChange={(e) => setUseRag(e.target.checked)}
              className="w-4 h-4 rounded border-gray-600 bg-dark-3 text-indigo-500 focus:ring-indigo-500 focus:ring-offset-0"
            />
            <span>RAG增强</span>
          </label>
        </div>
        <div className="text-sm text-gray-500">
          {messages.length} 条消息
        </div>
      </div>

      {showUpload && <UploadPanel />}

      <div className="card overflow-hidden">
        <div className="h-[450px] overflow-y-auto scrollbar-thin p-4 space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mb-4 shadow-lg shadow-indigo-500/30">
                <span className="text-3xl">🤖</span>
              </div>
              <p className="text-lg font-medium text-gray-400 mb-2">开始对话吧</p>
              <p className="text-sm">上传文档可以启用 RAG 增强，获得更准确的回答</p>
            </div>
          )}

          {messages.map((msg, index) => (
            <div key={index} className="animate-fadeInUp">
              <div className={`chat-bubble ${msg.role === 'user' ? 'user' : 'assistant'}`}>
                <div className="flex items-start gap-3">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                    msg.role === 'user'
                      ? 'bg-gradient-to-br from-emerald-500 to-teal-600'
                      : 'bg-gradient-to-br from-indigo-500 to-purple-600'
                  }`}>
                    <span className="text-sm">{msg.role === 'user' ? '👤' : '🤖'}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-xs text-gray-400 mb-1">
                      {msg.role === 'user' ? '你' : 'AI 助手'}
                    </div>
                    <div className="text-sm leading-relaxed whitespace-pre-wrap">
                      {msg.content}
                      {msg.streaming && <span className="streaming-cursor"></span>}
                    </div>
                  </div>
                </div>
              </div>
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-2 ml-11">
                  <div className="flex flex-wrap gap-2">
                    <span className="text-xs text-gray-500">参考来源：</span>
                    {msg.sources.map((s, i) => (
                      <span key={i} className="badge badge-primary">
                        📄 {s.filename}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 border-t border-gray-800">
          <div className="flex gap-3">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="输入你的问题..."
              disabled={loading}
              className="input-field flex-1 h-14 resize-none"
              rows={1}
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              className="btn btn-primary h-14 px-6"
            >
              {loading ? (
                <div className="flex items-center gap-2">
                  <div className="typing-indicator flex gap-1">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              )}
            </button>
          </div>
          <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
            <span>按 Enter 发送，Shift + Enter 换行</span>
            <span>使用 llama3:8b 模型</span>
          </div>
        </div>
      </div>
    </div>
  )
}
