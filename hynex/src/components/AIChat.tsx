import { useRef, useState } from 'react'
import { ArrowUpRight, Bot, ChevronDown, Copy, Maximize2, Mic, Paperclip, Send, Sparkles, UserRound } from 'lucide-react'

type Message = { who: 'you' | 'ai'; text: string; tag?: string }
const replies = [
  'Start with the plan that protects your biggest recurring needs. Compare annual limits, network access, and the deductible together—not just the monthly premium.',
  'A simple place to begin is separating planned care from unexpected care. Keep a small buffer for co-pays, then review your plan limits once a month.',
  'Your recent activity is steady. I’d check whether each claim is marked in-network before the next renewal date.',
]
export default function AIChat() {
  const [messages, setMessages] = useState<Message[]>([
    { who: 'you', text: 'What are the best ways to prioritize my insurance?' },
    { who: 'ai', tag: 'Insurance focus', text: 'Start with your most-used care. Check network access, annual limits, and deductibles together so your cover fits the way you actually live.' },
  ])
  const [value, setValue] = useState('')
  const [active, setActive] = useState('AI Hub')
  const [thinking, setThinking] = useState(false)
  const bottom = useRef<HTMLDivElement>(null)
  function send(text = value) {
    const clean = text.trim(); if (!clean || thinking) return
    setMessages(items => [...items, { who: 'you', text: clean }]); setValue(''); setThinking(true)
    window.setTimeout(() => { setMessages(items => [...items, { who: 'ai', tag: 'Hynex insight', text: replies[Math.floor(Math.random() * replies.length)] }]); setThinking(false); bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }) }, 650)
  }
  return <section className="panel chat-card">
    <div className="panel-heading"><div><div className="eyebrow"><span className="ai-live-dot"/> AI assistant</div><div className="chart-title">Your care companion</div></div><div className="chat-actions"><button className="icon-button subtle-menu" aria-label="Copy conversation" onClick={() => void navigator.clipboard?.writeText(messages.map(m => `${m.who}: ${m.text}`).join('\n'))}><Copy size={14}/></button><button className="icon-button subtle-menu" aria-label="Expand chat"><Maximize2 size={14}/></button></div></div>
    <div className="chat-thread">{messages.map((message, index) => <div key={`${message.who}-${index}`} className={`message-row ${message.who === 'you' ? 'message-you' : ''}`}>
      <div className={`message-avatar ${message.who === 'ai' ? 'bot-avatar' : 'user-message-avatar'}`}>{message.who === 'ai' ? <Bot size={13}/> : <UserRound size={13}/>}</div>
      <div className="message-content">{message.tag && <span className="message-tag"><Sparkles size={10}/>{message.tag}</span>}<div className="message-bubble">{message.text}</div></div>
    </div>)}{thinking && <div className="typing-dots"><i/><i/><i/></div>}<div ref={bottom}/></div>
    <div className="quick-prompts">{['AI Hub', 'Health finance', 'Plan review'].map(tab => <button key={tab} className={active === tab ? 'quick-prompt quick-active' : 'quick-prompt'} onClick={() => { setActive(tab); if (tab !== 'AI Hub') send(tab === 'Plan review' ? 'Help me review my health plan.' : 'How can I make my health finances easier to manage?') }}>{tab}</button>)}</div>
    <form className="chat-composer" onSubmit={e => { e.preventDefault(); send() }}><button type="button" className="composer-icon" aria-label="Attach a file"><Paperclip size={14}/></button><input value={value} onChange={e => setValue(e.target.value)} placeholder="Ask Hynex anything..." aria-label="Message Hynex"/><button type="button" className="composer-icon mic-button" aria-label="Voice input"><Mic size={14}/></button><button type="submit" className="send-button" aria-label="Send message"><Send size={14}/></button></form>
    <div className="chat-foot"><span>AI can make mistakes. Verify important details.</span><button>Details <ChevronDown size={11}/></button><ArrowUpRight size={12}/></div>
  </section>
}
