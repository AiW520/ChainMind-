import { useState } from 'react'
import UploadPanel from './UploadPanel'

export default function RAGPanel() {
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(5)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [showUpload, setShowUpload] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [streamingAnswer, setStreamingAnswer] = useState('')

  const handleSearch = async () => {
    if (!query.trim() || loading) return

    setLoading(true)
    setResult(null)
    setStreaming(true)
    setStreamingAnswer('')

    try {
      const response = await fetch('/api/rag/query/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query,
          top_k: topK
        })
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let done = false
      let fullAnswer = ''
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
                  fullAnswer += data.token
                  setStreamingAnswer(fullAnswer)
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

      setResult({
        answer: fullAnswer,
        sources: sources
      })
    } catch (error) {
      setResult({
        answer: '搜索失败：' + error.message,
        sources: []
      })
    } finally {
      setLoading(false)
      setStreaming(false)
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
      <div className="flex items-center space-x-3">
        <button
          onClick={() => {
            setShowUpload((prev) => {
              const next = !prev
              if (!prev && next) {
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

      {showUpload && <UploadPanel />}

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
          <button
            onClick={handleSearch}
            disabled={loading || !query.trim()}
            className="btn bg-primary text-white px-6 py-2 rounded-md font-medium hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? '搜索中...' : '🔍 RAG 搜索'}
          </button>
        </div>
      </div>

      {result && (
        <div className="space-y-4">
          <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
            <div className="font-bold mb-2 text-primary">
              🤖 AI 回答
            </div>
            <pre className="whitespace-pre-wrap font-sans m-0">
              {result.answer}
            </pre>
            {streaming && (
              <span className="animate-pulse">▊</span>
            )}
          </div>

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
