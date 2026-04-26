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

    setMessages(prev => [...prev, { role: 'user', content: userMessage }])

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
                    newMessages[assistantMessageId] = {
                      ...newMessages[assistantMessageId],
                      content: fullResponse
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
        newMessages[assistantMessageId] = {
          role: 'assistant',
          content: fullResponse,
          streaming: false,
          sources: sources
        }
        return newMessages
      })
    } catch (error) {
      setMessages(prev => {
        const newMessages = [...prev]
        newMessages[assistantMessageId] = {
          role: 'assistant',
          content: '抱歉，发生了错误：' + error.message,
          streaming: false,
          sources: []
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

      {showUpload && <UploadPanel />}

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
              {msg.streaming && (
                <span className="animate-pulse">▊</span>
              )}
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
