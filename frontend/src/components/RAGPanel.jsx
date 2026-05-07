import { useState, useRef, useEffect } from 'react'
import UploadPanel from './UploadPanel'

export default function RAGPanel() {
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(5)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [showUpload, setShowUpload] = useState(false)
  const [streamingAnswer, setStreamingAnswer] = useState('')
  const abortControllerRef = useRef(null)

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [])

  const handleSearch = async () => {
    if (!query.trim() || loading) return

    setLoading(true)
    setResult(null)
    setStreamingAnswer('')

    abortControllerRef.current = new AbortController()

    try {
      console.log('Starting RAG search:', query)
      
      const url = `${window.location.origin}/api/rag/query/stream`
      console.log('Fetch URL:', url)

      const response = await fetch(url, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream'
        },
        body: JSON.stringify({
          query: query,
          top_k: topK
        }),
        signal: abortControllerRef.current.signal
      })

      console.log('Response status:', response.status)

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`HTTP error: ${response.status} - ${errorText}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let fullAnswer = ''
      let sources = []
      let buffer = ''

      console.log('Starting stream reading...')

      while (true) {
        const { value, done } = await reader.read()
        
        if (done) {
          console.log('Stream completed')
          break
        }

        if (value) {
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n\n')
          
          for (let i = 0; i < lines.length - 1; i++) {
            const line = lines[i]
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                if (data.error) {
                  throw new Error(data.token || 'Stream error')
                }
                if (!data.done) {
                  fullAnswer += data.token
                  setStreamingAnswer(fullAnswer)
                } else {
                  if (data.sources) {
                    sources = data.sources
                  }
                }
              } catch (e) {
                console.error('Parse error:', e)
              }
            }
          }
          
          buffer = lines[lines.length - 1]
        }
      }

      setResult({
        answer: fullAnswer,
        sources: sources
      })
      setStreamingAnswer('')
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.error('Search error:', error)
        setResult({
          answer: '搜索失败：' + error.message,
          sources: []
        })
      } else {
        console.log('Request aborted')
      }
    } finally {
      setLoading(false)
      abortControllerRef.current = null
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSearch()
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={() => setShowUpload(!showUpload)}
          className="btn btn-secondary flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          {showUpload ? '收起上传' : '上传文档到知识库'}
        </button>
        <span className="text-sm text-gray-400">
          上传文档后，可以基于文档内容进行问答
        </span>
      </div>

      {showUpload && <UploadPanel />}

      <div className="card p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">搜索问题</label>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="输入你想查询的问题..."
            disabled={loading}
            className="input-field h-24 resize-none"
          />
        </div>
        
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2">
              <span className="text-sm text-gray-400">检索数量：</span>
              <select
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="px-3 py-2 rounded-lg bg-dark-3 border border-gray-600 text-white focus:outline-none focus:border-primary"
              >
                <option value={3}>3</option>
                <option value={5}>5</option>
                <option value={10}>10</option>
              </select>
            </label>
          </div>
          
          <button
            onClick={handleSearch}
            disabled={loading || !query.trim()}
            className="btn btn-primary flex items-center gap-2"
          >
            {loading ? (
              <>
                <div className="typing-indicator flex gap-1">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                <span>搜索中...</span>
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <span>RAG 搜索</span>
              </>
            )}
          </button>
        </div>
      </div>

      {streamingAnswer && !result && (
        <div className="card p-6">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
              <span className="text-sm">🤖</span>
            </div>
            <span className="font-medium text-white">AI 回答</span>
            <span className="text-xs text-gray-500">生成中...</span>
          </div>
          <div className="text-gray-200 whitespace-pre-wrap leading-relaxed">
            {streamingAnswer}
            <span className="streaming-cursor"></span>
          </div>
        </div>
      )}

      {result && (
        <div className="space-y-4">
          <div className="card p-6">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                <span className="text-sm">🤖</span>
              </div>
              <span className="font-medium text-white">AI 回答</span>
            </div>
            <div className="text-gray-200 whitespace-pre-wrap leading-relaxed">
              {result.answer}
            </div>
          </div>

          {result.sources && result.sources.length > 0 && (
            <div className="card p-6">
              <div className="flex items-center gap-2 mb-4">
                <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
                <span className="font-medium text-white">参考来源</span>
                <span className="badge badge-primary">{result.sources.length} 条</span>
              </div>
              <div className="space-y-3">
                {result.sources.map((source, index) => (
                  <div key={index} className="p-4 rounded-lg bg-dark-3 border border-gray-700">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-emerald-400 font-medium flex items-center gap-2">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        {source.filename}
                      </span>
                      {source.distance !== null && source.distance !== undefined && (
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-400">相似度</span>
                          <div className="w-20 h-2 rounded-full bg-dark-2 overflow-hidden">
                            <div 
                              className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
                              style={{ width: `${Math.max(0, Math.min(100, (1 - source.distance) * 100))}%` }}
                            ></div>
                          </div>
                          <span className="text-xs text-primary">{((1 - source.distance) * 100).toFixed(0)}%</span>
                        </div>
                      )}
                    </div>
                    <div className="text-sm text-gray-300 leading-relaxed">
                      {source.content.length > 300 ? source.content.substring(0, 300) + '...' : source.content}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(!result.sources || result.sources.length === 0) && (
            <div className="card p-8 text-center">
              <div className="text-4xl mb-3">📭</div>
              <p className="text-gray-400">未找到相关文档</p>
              <p className="text-sm text-gray-500 mt-1">请先上传文档到知识库</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
