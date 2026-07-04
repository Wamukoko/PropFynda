import { useState, useRef, useEffect } from 'react'
import { sendChatMessage } from '../utils/api'

interface ChatPanelProps {
  open: boolean
  onClose: () => void
  initialMessages?: {role: string; content: string}[]
}

export default function ChatPanel({ open, onClose, initialMessages }: ChatPanelProps) {
  const [chatMessages, setChatMessages] = useState<{role: string; content: string}[]>([
    {role: 'assistant', content: 'Hi! I\'m Agent Eve. I can help you find the perfect property in Kenya. Tell me what you\'re looking for!'},
    ...(initialMessages || [])
  ])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  const handleChatSend = async () => {
    const text = chatInput.trim()
    if (!text || chatLoading) return
    setChatInput('')
    const userMsg = { role: 'user', content: text }
    const updated = [...chatMessages, userMsg]
    setChatMessages(updated)
    setChatLoading(true)
    try {
      const data = await sendChatMessage(updated)
      setChatMessages(prev => [...prev, { role: 'assistant', content: data.reply }])
    } catch {
      setChatMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I\'m having trouble connecting right now.' }])
    }
    setChatLoading(false)
  }

  if (!open) return null

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <span className="chat-header-name">Agent Eve</span>
        <span className="chat-header-sub">Property Assistant</span>
      </div>
      <div className="chat-body">
        {chatMessages.map((m, i) => (
          <div key={i} className={`chat-msg chat-msg-${m.role}`}>
            {m.content}
          </div>
        ))}
        {chatLoading && <div className="chat-msg chat-msg-assistant chat-msg-typing">...</div>}
        <div ref={chatEndRef} />
      </div>
      <div className="chat-footer">
        <input
          type="text"
          placeholder="Ask me about properties..."
          value={chatInput}
          onChange={e => setChatInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleChatSend()}
          disabled={chatLoading}
        />
        <button className="btn btn-primary" onClick={handleChatSend} disabled={chatLoading || !chatInput.trim()}>
          Send
        </button>
      </div>
    </div>
  )
}