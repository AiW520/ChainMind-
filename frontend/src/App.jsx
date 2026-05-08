import { useState } from 'react'
import ChatWindow from './components/ChatWindow'
import RAGPanel from './components/RAGPanel'
import AgentFlow from './components/AgentFlow'

export default function App() {
  const [activeTab, setActiveTab] = useState('chat')

  return (
    <div className="min-h-screen grid-bg">
      <div className="max-w-7xl mx-auto p-4 md:p-6">
        <header className="mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                <span className="text-2xl">🧠</span>
              </div>
              <div>
                <h1 className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
                  ChainMind
                </h1>
                <p className="text-sm text-gray-500">企业级RAG智能知识库系统</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="hidden md:flex items-center gap-2 px-4 py-2 rounded-lg bg-dark-3 border border-gray-700">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                <span className="text-sm text-gray-400">系统运行中</span>
              </div>
            </div>
          </div>
        </header>

        <main className="glass-card p-2">
          <div className="tabs mb-4">
            <button
              onClick={() => setActiveTab('chat')}
              className={`tab flex items-center gap-2 ${activeTab === 'chat' ? 'active' : ''}`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              智能问答
            </button>
            <button
              onClick={() => setActiveTab('rag')}
              className={`tab flex items-center gap-2 ${activeTab === 'rag' ? 'active' : ''}`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              RAG检索
            </button>
            <button
              onClick={() => setActiveTab('agent')}
              className={`tab flex items-center gap-2 ${activeTab === 'agent' ? 'active' : ''}`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              Agent流程
            </button>
          </div>

          <div className="p-4 md:p-6">
            {activeTab === 'chat' && <ChatWindow />}
            {activeTab === 'rag' && <RAGPanel />}
            {activeTab === 'agent' && <AgentFlow />}
          </div>
        </main>

        <footer className="mt-6 text-center">
          <p className="text-sm text-gray-500">
            Powered by FastAPI + Ollama + LangChain | v2.0 Enterprise Edition
          </p>
        </footer>
      </div>
    </div>
  )
}
