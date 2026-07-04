import { useState, useRef, useEffect } from 'react'
import { sendChatMessage } from '../utils/api'

export function useChat(initialMessages?: {role: string; content: string}[]) {
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

  const sendMessage = async () => {
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

  return {
    chatMessages,
    setChatMessages,
    chatInput,
    setChatInput,
    chatLoading,
    chatEndRef,
    sendMessage,
  }
}