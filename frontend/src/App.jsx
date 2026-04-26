import { useState } from 'react'
import ChatWindow from './components/ChatWindow'
import RAGPanel from './components/RAGPanel'

export default function App() {
  const [activeTab, setActiveTab] = useState('chat')

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-gray-800 mb-2">
            ChainMind
          </h1>
          <p className="text-gray-600">本地AI知识库问答系统</p>
        </div>
        
        <div className="bg-white rounded-xl shadow-lg overflow-hidden">
          <div className="tabs">
            <button 
              onClick={() => setActiveTab('chat')}
              className={`tab ${activeTab === 'chat' ? 'active' : 'inactive'}`}
            >
              💬 聊天
            </button>
            <button 
              onClick={() => setActiveTab('rag')}
              className={`tab ${activeTab === 'rag' ? 'active' : 'inactive'}`}
            >
              📚 RAG
            </button>
          </div>
          
          <div className="p-4 md:p-6">
            {activeTab === 'chat' && <ChatWindow />}
            {activeTab === 'rag' && <RAGPanel />}
          </div>
        </div>
        
        <div className="mt-6 text-center text-sm text-gray-500">
          <p>Powered by FastAPI + Ollama + LangChain</p>
        </div>
      </div>
    </div>
  )
}
