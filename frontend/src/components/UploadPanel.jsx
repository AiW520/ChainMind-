import { useState } from 'react'

export default function UploadPanel() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [dragOver, setDragOver] = useState(false)

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      setResult(null)
    }
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setDragOver(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    setDragOver(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile) {
      setFile(droppedFile)
      setResult(null)
    }
  }

  const handleUpload = async () => {
    if (!file) return

    setUploading(true)
    setResult(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 30000)
      
      const response = await fetch('/api/upload/file', {
        method: 'POST',
        body: formData,
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`上传失败: ${response.status}`)
      }

      const data = await response.json()
      console.log('上传成功:', data)
      setResult({
        success: true,
        data
      })
      setFile(null)
    } catch (error) {
      console.error('上传错误:', error)
      setResult({
        success: false,
        error: error.message
      })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className={`border border-dashed rounded-xl p-6 mb-6 transition-all ${
      dragOver ? 'border-primary bg-primary/10' : 'border-gray-700 bg-dark-3'
    }`}>
      <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
        </svg>
        文档上传
      </h3>
      
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-8 text-center mb-4 cursor-pointer transition-all ${
          dragOver ? 'border-primary bg-primary/5' : 'border-gray-600 bg-dark-2 hover:border-gray-500'
        }`}
        onClick={() => document.getElementById('file-input').click()}
      >
        <input
          id="file-input"
          type="file"
          accept=".txt,.md,.pdf"
          onChange={handleFileChange}
          className="hidden"
        />
        <div className="text-4xl mb-3">📁</div>
        <div className="text-gray-300">
          拖拽文件到此处，或 <span className="text-primary font-medium">点击选择</span>
        </div>
        <div className="text-xs text-gray-500 mt-2">
          支持 .txt, .md, .pdf 文件（最大 10MB）
        </div>
      </div>

      {file && (
        <div className="flex items-center justify-between p-3 bg-dark-2 rounded-lg mb-4">
          <span className="text-gray-300">📄 {file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
          <button
            onClick={() => setFile(null)}
            className="text-gray-400 hover:text-red-400 text-lg transition-colors"
          >
            ✕
          </button>
        </div>
      )}

      <button
        onClick={() => {
          if (!file && !uploading) {
            const el = document.getElementById('file-input')
            if (el) el.click()
            return
          }
          handleUpload()
        }}
        disabled={uploading}
        className={`btn w-full py-3 ${
          uploading 
            ? 'btn-secondary cursor-not-allowed' 
            : file 
              ? 'btn-primary' 
              : 'btn-secondary hover:bg-dark-4'
        }`}
      >
        {uploading ? (
          <div className="flex items-center justify-center gap-2">
            <div className="typing-indicator flex gap-1">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <span>上传中...</span>
          </div>
        ) : (file ? '上传并处理' : '选择文件并上传')}
      </button>

      {result && (
        <div className={`mt-4 p-4 rounded-lg ${
          result.success 
            ? 'bg-emerald-500/10 border border-emerald-500/30' 
            : 'bg-red-500/10 border border-red-500/30'
        }`}>
          {result.success ? (
            <>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-emerald-400">✓</span>
                <strong className="font-semibold text-emerald-400">上传成功！</strong>
              </div>
              <div className="text-sm text-gray-300 space-y-1">
                <div>📄 文件名：{result.data.file_name}</div>
                <div>💬 状态：{result.data.status}</div>
              </div>
            </>
          ) : (
            <>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-red-400">✕</span>
                <strong className="font-semibold text-red-400">上传失败</strong>
              </div>
              <div className="text-sm text-gray-400">{result.error}</div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
