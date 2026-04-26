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
      const timeoutId = setTimeout(() => controller.abort(), 30000) // 30秒超时
      
      const response = await fetch('/api/upload/file', {
        method: 'POST',
        body: formData,
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`上传失败: ${response.status} ${errorText}`)
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
    <div className={`border-2 border-dashed rounded-xl p-6 mb-6 ${dragOver ? 'bg-blue-50 border-blue-300' : 'bg-white border-gray-300'}`}>
      <h3 className="text-xl font-semibold mb-4">📤 文档上传</h3>
      
      {/* 拖拽区域 */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-8 text-center mb-4 cursor-pointer bg-gray-50 transition-colors ${dragOver ? 'border-primary bg-blue-50' : 'border-gray-300'}`}
        onClick={() => document.getElementById('file-input').click()}
      >
        <input
          id="file-input"
          type="file"
          accept=".txt,.md,.pdf"
          onChange={handleFileChange}
          className="hidden"
        />
        <div className="text-5xl mb-3">📁</div>
        <div className="text-gray-700">
          拖拽文件到此处，或 <span className="text-primary font-medium">点击选择</span>
        </div>
        <div className="text-xs text-gray-500 mt-2">
          支持 .txt, .md, .pdf 文件（最大 10MB）
        </div>
      </div>

      {/* 已选文件 */}
      {file && (
        <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg mb-4">
          <span className="text-gray-700">📄 {file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
          <button
            onClick={() => setFile(null)}
            className="text-gray-400 hover:text-gray-600 text-lg"
          >
            ✕
          </button>
        </div>
      )}

      {/* 上传按钮 */}
      <button
        onClick={() => {
          if (!file && !uploading) {
            // 如果还没有选择文件，打开文件选择对话框
            const el = document.getElementById('file-input')
            if (el) el.click()
            return
          }
          handleUpload()
        }}
        disabled={uploading}
        className={`btn btn-primary w-full py-3 ${uploading ? 'bg-gray-400 cursor-not-allowed' : (file ? 'bg-green-600 hover:bg-green-700' : 'bg-yellow-500 hover:bg-yellow-600')}`}
      >
        {uploading ? (
          <div className="flex items-center justify-center space-x-2">
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            <span>上传中...</span>
          </div>
        ) : (file ? '上传并处理' : '选择文件并上传')}
      </button>

      {/* 结果显示 */}
      {result && (
        <div className={`mt-4 p-4 rounded-lg ${result.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
          {result.success ? (
            <>
              <strong className="font-semibold">✅ 上传成功！</strong>
              <div className="mt-2 text-sm space-y-1">
                <div>📄 文件名：{result.data.file_name}</div>
                <div>📊 文件大小：{(result.data.file_size / 1024).toFixed(1)} KB</div>
                <div>📑 切分块数：{result.data.total_chunks}</div>
                <div>🗃️ 已存入向量库：{result.data.vector_stored ? '是' : '否'}</div>
              </div>
            </>
          ) : (
            <>
              <strong className="font-semibold">❌ 上传失败</strong>
              <div>{result.error}</div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
