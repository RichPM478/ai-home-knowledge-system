import { useState, useEffect } from 'react'
import { Send, MessageCircle, Settings, Plus, Database, Zap, Trash2, CheckCircle, XCircle, Clock, Search, BarChart3, Brain } from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function Home() {
  const [currentView, setCurrentView] = useState('chat')
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState([])
  const [systemStatus, setSystemStatus] = useState('checking...')
  const [isLoading, setIsLoading] = useState(false)
  
  // Connector state
  const [connectors, setConnectors] = useState([])
  const [showAddConnector, setShowAddConnector] = useState(false)
  const [syncProgress, setSyncProgress] = useState({})
  const [systemStats, setSystemStats] = useState(null)
  const [newConnector, setNewConnector] = useState({
    type: 'bt_internet',
    name: '',
    username: '',
    password: ''
  })

  useEffect(() => {
    checkHealth()
    if (currentView === 'connectors') {
      loadConnectors()
      loadSystemStats()
    }
  }, [currentView])

  // Poll sync progress for active syncs
  useEffect(() => {
    const interval = setInterval(async () => {
      for (const connector of connectors) {
        if (syncProgress[connector.id]?.is_syncing) {
          await checkSyncProgress(connector.id)
        }
      }
    }, 2000) // Check every 2 seconds

    return () => clearInterval(interval)
  }, [connectors, syncProgress])

  const checkHealth = async () => {
    try {
      const response = await fetch(`${API_BASE}/health/`)
      if (response.ok) {
        setSystemStatus('online')
      } else {
        setSystemStatus('offline')
      }
    } catch (error) {
      setSystemStatus('offline')
    }
  }

  const loadConnectors = async () => {
    try {
      const response = await fetch(`${API_BASE}/connectors/`)
      if (response.ok) {
        const data = await response.json()
        setConnectors(data)
      }
    } catch (error) {
      console.error('Failed to load connectors:', error)
    }
  }

  const loadSystemStats = async () => {
    try {
      const response = await fetch(`${API_BASE}/stats/`)
      if (response.ok) {
        const data = await response.json()
        setSystemStats(data)
      }
    } catch (error) {
      console.error('Failed to load stats:', error)
    }
  }

  const checkSyncProgress = async (connectorId) => {
    try {
      const response = await fetch(`${API_BASE}/connectors/${connectorId}/sync-status`)
      if (response.ok) {
        const data = await response.json()
        setSyncProgress(prev => ({
          ...prev,
          [connectorId]: data
        }))
        
        // Refresh connectors if sync completed
        if (!data.is_syncing && prev[connectorId]?.is_syncing) {
          loadConnectors()
          loadSystemStats()
        }
      }
    } catch (error) {
      console.error('Failed to check sync progress:', error)
    }
  }

  const createConnector = async () => {
    try {
      const response = await fetch(`${API_BASE}/connectors/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: newConnector.type,
          name: newConnector.name,
          config: {
            username: newConnector.username,
            password: newConnector.password
          },
          enabled: true
        })
      })

      if (response.ok) {
        setShowAddConnector(false)
        setNewConnector({ type: 'bt_internet', name: '', username: '', password: '' })
        loadConnectors()
      } else {
        const error = await response.json()
        alert(`Failed to create connector: ${error.detail}`)
      }
    } catch (error) {
      alert(`Error: ${error.message}`)
    }
  }

  const connectConnector = async (connectorId) => {
    try {
      const response = await fetch(`${API_BASE}/connectors/${connectorId}/connect`, {
        method: 'POST'
      })
      if (response.ok) {
        loadConnectors()
      } else {
        const error = await response.json()
        alert(`Connection failed: ${error.detail}`)
      }
    } catch (error) {
      alert(`Error: ${error.message}`)
    }
  }

  const syncConnector = async (connectorId) => {
    try {
      const response = await fetch(`${API_BASE}/connectors/${connectorId}/sync`, {
        method: 'POST'
      })
      if (response.ok) {
        // Start polling for this connector
        setSyncProgress(prev => ({
          ...prev,
          [connectorId]: { is_syncing: true, progress: 0, status_message: 'Starting sync...' }
        }))
        
        const syncMessage = {
          role: 'assistant',
          content: `🚀 Started enhanced sync with vector embeddings for your emails! Watch the progress in the Connectors tab. Once complete, I'll be able to provide much more intelligent answers based on semantic understanding of your email content.`
        }
        setMessages(prev => [...prev, syncMessage])
        setCurrentView('chat')
      }
    } catch (error) {
      alert(`Sync failed: ${error.message}`)
    }
  }

  const deleteConnector = async (connectorId) => {
    if (!confirm('Are you sure you want to delete this connector?')) return
    
    try {
      const response = await fetch(`${API_BASE}/connectors/${connectorId}`, {
        method: 'DELETE'
      })
      if (response.ok) {
        loadConnectors()
        loadSystemStats()
      }
    } catch (error) {
      alert(`Delete failed: ${error.message}`)
    }
  }

  const sendMessage = async () => {
    if (!message.trim() || isLoading) return

    const userMessage = { role: 'user', content: message }
    setMessages(prev => [...prev, userMessage])
    setMessage('')
    setIsLoading(true)

    try {
      const response = await fetch(`${API_BASE}/chat/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message })
      })

      if (response.ok) {
        const result = await response.json()
        const aiMessage = { 
          role: 'assistant', 
          content: result.response,
          sources: result.sources,
          processing_time: result.processing_time
        }
        setMessages(prev => [...prev, aiMessage])
      } else {
        throw new Error('Failed to get response')
      }
    } catch (error) {
      const errorMessage = { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'connected': return <CheckCircle className="w-4 h-4 text-green-600" />
      case 'connecting': return <Clock className="w-4 h-4 text-yellow-600 animate-spin" />
      case 'error': return <XCircle className="w-4 h-4 text-red-600" />
      default: return <Database className="w-4 h-4 text-gray-400" />
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'connected': return 'bg-green-100 text-green-800'
      case 'connecting': return 'bg-yellow-100 text-yellow-800'
      case 'error': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getSyncProgressColor = (progress) => {
    if (progress === 100) return 'bg-green-500'
    if (progress > 50) return 'bg-blue-500'
    if (progress > 0) return 'bg-yellow-500'
    return 'bg-gray-300'
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <div className="bg-white shadow-sm border-b p-4">
        <div className="flex items-center justify-between max-w-6xl mx-auto">
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2">
              <Brain className="w-8 h-8 text-purple-600" />
              <MessageCircle className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">AI Home Knowledge System</h1>
              <p className="text-gray-600">Enhanced with vector search & semantic understanding</p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            {systemStats && (
              <div className="text-sm text-gray-600">
                <span className="font-medium">{systemStats.vector_database.total_emails}</span> emails indexed
              </div>
            )}
            <div className={`px-3 py-1 rounded-full text-sm font-medium ${
              systemStatus === 'online' 
                ? 'bg-green-100 text-green-800' 
                : 'bg-red-100 text-red-800'
            }`}>
              System {systemStatus}
            </div>
          </div>
        </div>
      </div>

      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-6xl mx-auto px-4">
          <div className="flex space-x-8">
            <button
              onClick={() => setCurrentView('chat')}
              className={`px-3 py-3 text-sm font-medium transition-colors border-b-2 flex items-center space-x-2 ${
                currentView === 'chat' 
                  ? 'border-blue-600 text-blue-600' 
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              <MessageCircle className="w-4 h-4" />
              <span>Smart Chat</span>
            </button>
            <button
              onClick={() => setCurrentView('connectors')}
              className={`px-3 py-3 text-sm font-medium transition-colors border-b-2 flex items-center space-x-2 ${
                currentView === 'connectors' 
                  ? 'border-blue-600 text-blue-600' 
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              <Database className="w-4 h-4" />
              <span>Connectors</span>
              {connectors.length > 0 && (
                <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs">
                  {connectors.length}
                </span>
              )}
            </button>
          </div>
        </div>
      </nav>

      <div className="flex-1 overflow-hidden">
        {currentView === 'chat' && (
          <div className="flex-1 flex flex-col max-w-4xl mx-auto w-full">
            {messages.length === 0 ? (
              <div className="flex-1 flex items-center justify-center p-8">
                <div className="max-w-2xl text-center">
                  <div className="flex items-center justify-center space-x-3 mb-6">
                    <Brain className="w-12 h-12 text-purple-600" />
                    <MessageCircle className="w-10 h-10 text-blue-600" />
                  </div>
                  <h2 className="text-3xl font-bold text-gray-900 mb-4">
                    Enhanced AI Knowledge System
                  </h2>
                  <p className="text-gray-600 mb-8">
                    Now with vector embeddings and semantic search for intelligent understanding of your family communications!
                  </p>
                  
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm mb-8">
                    <div className="bg-purple-50 p-4 rounded-lg">
                      <div className="flex items-center space-x-2 mb-2">
                        <Brain className="w-4 h-4 text-purple-600" />
                        <h4 className="font-medium text-purple-900">Semantic Understanding</h4>
                      </div>
                      <p className="text-purple-700">"What events do we have coming up?" understands context</p>
                    </div>
                    <div className="bg-blue-50 p-4 rounded-lg">
                      <div className="flex items-center space-x-2 mb-2">
                        <Search className="w-4 h-4 text-blue-600" />
                        <h4 className="font-medium text-blue-900">Smart Search</h4>
                      </div>
                      <p className="text-blue-700">Finds relevant info even with different wording</p>
                    </div>
                    <div className="bg-green-50 p-4 rounded-lg">
                      <div className="flex items-center space-x-2 mb-2">
                        <Zap className="w-4 h-4 text-green-600" />
                        <h4 className="font-medium text-green-900">Real-time Sync</h4>
                      </div>
                      <p className="text-green-700">Live progress tracking with vector embeddings</p>
                    </div>
                  </div>

                  <div className="bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg p-6">
                    <h3 className="font-semibold text-purple-900 mb-3">🚀 Enhanced Features</h3>
                    <div className="text-left space-y-2 text-sm text-purple-800">
                      <div className="flex items-center space-x-2">
                        <CheckCircle className="w-4 h-4 text-green-600" />
                        <span>Vector embeddings for semantic similarity</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <CheckCircle className="w-4 h-4 text-green-600" />
                        <span>Real-time sync progress with status updates</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <CheckCircle className="w-4 h-4 text-green-600" />
                        <span>Intelligent context-aware responses</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <CheckCircle className="w-4 h-4 text-green-600" />
                        <span>Multi-source email connector support</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((msg, index) => (
                  <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-3xl rounded-lg px-4 py-3 ${
                      msg.role === 'user' 
                        ? 'bg-blue-600 text-white' 
                        : 'bg-white border border-gray-200 text-gray-900 shadow-sm'
                    }`}>
                      <div className="whitespace-pre-wrap">{msg.content}</div>
                      
                      {msg.sources && msg.sources.length > 0 && (
                        <div className="mt-4 pt-3 border-t border-gray-200">
                          <div className="flex items-center space-x-2 mb-2">
                            <Search className="w-4 h-4 text-gray-500" />
                            <p className="text-xs font-medium text-gray-600">Sources found via semantic search:</p>
                          </div>
                          {msg.sources.slice(0, 2).map((source, idx) => (
                            <div key={idx} className="text-xs text-gray-600 mb-2 bg-gray-50 p-2 rounded">
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-medium">
                                  {source.metadata.subject || 'Email'} - {source.metadata.sender || 'System'}
                                </span>
                                {source.score && (
                                  <span className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs">
                                    {Math.round(source.score * 100)}% match
                                  </span>
                                )}
                              </div>
                              <div className="text-xs text-gray-500 truncate">{source.content}</div>
                            </div>
                          ))}
                        </div>
                      )}
                      
                      {msg.processing_time && (
                        <div className="mt-2 text-xs text-gray-500">
                          Processed in {msg.processing_time}s with vector search
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-white border border-gray-200 rounded-lg px-4 py-3 shadow-sm">
                      <div className="flex items-center space-x-2">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-purple-600"></div>
                        <Brain className="w-4 h-4 text-purple-600" />
                        <span className="text-gray-600">Analyzing with semantic search...</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            <div className="border-t bg-white p-4">
              <div className="flex space-x-3">
                <input
                  type="text"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                  placeholder="Ask about your family plans with enhanced AI understanding..."
                  className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  disabled={isLoading}
                />
                <button
                  onClick={sendMessage}
                  disabled={isLoading || !message.trim()}
                  className="bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg px-4 py-2 hover:from-purple-700 hover:to-blue-700 disabled:opacity-50 flex items-center space-x-2"
                >
                  <Send className="w-4 h-4" />
                  <Brain className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        )}

        {currentView === 'connectors' && (
          <div className="max-w-6xl mx-auto p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Enhanced Email Connectors</h2>
                <p className="text-gray-600">Connect your email accounts with vector embedding processing</p>
              </div>
              <div className="flex items-center space-x-4">
                {systemStats && (
                  <div className="text-right text-sm text-gray-600">
                    <div className="flex items-center space-x-2">
                      <BarChart3 className="w-4 h-4" />
                      <span>{systemStats.vector_database.total_emails} emails in vector DB</span>
                    </div>
                    <div className="text-xs text-gray-500">
                      {systemStats.connectors.connected_connectors} of {systemStats.connectors.total_connectors} connected
                    </div>
                  </div>
                )}
                <button
                  onClick={() => setShowAddConnector(true)}
                  className="bg-gradient-to-r from-purple-600 to-blue-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 hover:from-purple-700 hover:to-blue-700"
                >
                  <Plus className="w-4 h-4" />
                  <span>Add Connector</span>
                </button>
              </div>
            </div>

            <div className="grid gap-4">
              {connectors.map((connector) => (
                <div key={connector.id} className="bg-white border rounded-lg p-4 shadow-sm">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-3">
                      {getStatusIcon(connector.status)}
                      <div>
                        <h3 className="font-medium text-gray-900">{connector.name}</h3>
                        <p className="text-sm text-gray-500">
                          {connector.type === 'bt_internet' ? 'BT Internet Email' : 'Gmail'} • {connector.id}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-3">
                      <div className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(connector.status)}`}>
                        {connector.status}
                      </div>
                      <div className="flex space-x-2">
                        {connector.status === 'disconnected' && (
                          <button
                            onClick={() => connectConnector(connector.id)}
                            className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                          >
                            Connect
                          </button>
                        )}
                        {connector.status === 'connected' && (
                          <button
                            onClick={() => syncConnector(connector.id)}
                            className="text-green-600 hover:text-green-800 text-sm font-medium flex items-center space-x-1"
                            disabled={syncProgress[connector.id]?.is_syncing}
                          >
                            <Brain className="w-3 h-3" />
                            <span>{syncProgress[connector.id]?.is_syncing ? 'Syncing...' : 'Sync with AI'}</span>
                          </button>
                        )}
                        <button
                          onClick={() => deleteConnector(connector.id)}
                          className="text-red-600 hover:text-red-800 text-sm font-medium"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Sync Progress Bar */}
                  {syncProgress[connector.id]?.is_syncing && (
                    <div className="mb-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-gray-700">
                          {syncProgress[connector.id].status_message}
                        </span>
                        <span className="text-sm text-gray-500">
                          {syncProgress[connector.id].progress}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className={`h-2 rounded-full transition-all duration-300 ${getSyncProgressColor(syncProgress[connector.id].progress)}`}
                          style={{ width: `${syncProgress[connector.id].progress}%` }}
                        ></div>
                      </div>
                      {syncProgress[connector.id].messages_processed > 0 && (
                        <div className="text-xs text-gray-500 mt-1">
                          {syncProgress[connector.id].messages_processed} emails processed with vector embeddings
                        </div>
                      )}
                    </div>
                  )}

                  {/* Sync Stats */}
                  {connector.last_sync && (
                    <div className="text-xs text-gray-500 bg-gray-50 p-2 rounded">
                      Last sync: {new Date(connector.last_sync).toLocaleString()} • 
                      {connector.message_count} emails • 
                      {syncProgress[connector.id]?.sync_duration && 
                        ` ${syncProgress[connector.id].sync_duration}s processing time`}
                    </div>
                  )}

                  {connector.error_message && (
                    <div className="mt-2 text-sm text-red-600 bg-red-50 p-2 rounded">
                      Error: {connector.error_message}
                    </div>
                  )}
                </div>
              ))}

              {connectors.length === 0 && (
                <div className="text-center py-12 bg-gradient-to-br from-purple-50 to-blue-50 rounded-lg">
                  <div className="flex items-center justify-center space-x-2 mb-4">
                    <Brain className="w-12 h-12 text-purple-500" />
                    <Database className="w-10 h-10 text-blue-500" />
                  </div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No connectors configured</h3>
                  <p className="text-gray-600 mb-4">Add your first email account to start building your AI knowledge base</p>
                  <button
                    onClick={() => setShowAddConnector(true)}
                    className="bg-gradient-to-r from-purple-600 to-blue-600 text-white px-4 py-2 rounded-lg hover:from-purple-700 hover:to-blue-700"
                  >
                    Add Your First Connector
                  </button>
                </div>
              )}
            </div>

            {/* Add Connector Modal */}
            {showAddConnector && (
              <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
                  <div className="flex items-center space-x-2 mb-4">
                    <Brain className="w-5 h-5 text-purple-600" />
                    <h3 className="text-lg font-semibold">Add Enhanced Email Connector</h3>
                  </div>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Email Provider</label>
                      <select
                        value={newConnector.type}
                        onChange={(e) => setNewConnector({...newConnector, type: e.target.value})}
                        className="w-full border rounded-lg px-3 py-2"
                      >
                        <option value="bt_internet">BT Internet (Real IMAP)</option>
                        <option value="gmail">Gmail (Demo Mode)</option>
                      </select>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Display Name</label>
                      <input
                        type="text"
                        value={newConnector.name}
                        onChange={(e) => setNewConnector({...newConnector, name: e.target.value})}
                        placeholder="My BT Email Account"
                        className="w-full border rounded-lg px-3 py-2"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Email Address</label>
                      <input
                        type="email"
                        value={newConnector.username}
                        onChange={(e) => setNewConnector({...newConnector, username: e.target.value})}
                        placeholder="your.email@btinternet.com"
                        className="w-full border rounded-lg px-3 py-2"
                      />
                    </div>
                    
                    {newConnector.type === 'bt_internet' && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                        <input
                          type="password"
                          value={newConnector.password}
                          onChange={(e) => setNewConnector({...newConnector, password: e.target.value})}
                          className="w-full border rounded-lg px-3 py-2"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          Your credentials are stored securely and only used for IMAP connection
                        </p>
                      </div>
                    )}

                    <div className="bg-purple-50 p-3 rounded border border-purple-200">
                      <div className="flex items-center space-x-2 mb-2">
                        <Brain className="w-4 h-4 text-purple-600" />
                        <p className="font-medium text-purple-900 text-sm">AI Enhancement Features:</p>
                      </div>
                      <ul className="text-xs text-purple-800 space-y-1">
                        <li>• Automatic vector embeddings for semantic similarity</li>
                        <li>• Real-time sync progress with status updates</li>
                        <li>• Intelligent context-aware chat responses</li>
                        <li>• Privacy-first local processing</li>
                      </ul>
                    </div>
                  </div>
                  
                  <div className="flex space-x-3 mt-6">
                    <button
                      onClick={() => setShowAddConnector(false)}
                      className="flex-1 border border-gray-300 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={createConnector}
                      className="flex-1 bg-gradient-to-r from-purple-600 to-blue-600 text-white py-2 px-4 rounded-lg hover:from-purple-700 hover:to-blue-700 flex items-center justify-center space-x-2"
                      disabled={!newConnector.name || !newConnector.username}
                    >
                      <Brain className="w-4 h-4" />
                      <span>Create Enhanced Connector</span>
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}