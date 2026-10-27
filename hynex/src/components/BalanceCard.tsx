import { useState } from 'react'
import { ArrowUpRight, Sparkles } from 'lucide-react'
import StatCard from './StatCard'

function Crystal() {
  return <svg viewBox="0 0 280 160" className="crystal-art" role="img" aria-label="Abstract glowing teal crystal illustration">
    <defs><linearGradient id="facetA" x1="0" x2="1" y1="0" y2="1"><stop stopColor="#2dd4bf"/><stop offset="1" stopColor="#047c79"/></linearGradient><linearGradient id="facetB" x1="0" x2="1" y1="1" y2="0"><stop stopColor="#0b5d60"/><stop offset="1" stopColor="#40f5d0"/></linearGradient><filter id="glow"><feGaussianBlur stdDeviation="11"/></filter></defs>
    <ellipse cx="144" cy="136" rx="100" ry="13" fill="#2dd4bf" opacity=".22" filter="url(#glow)"/>
    <path d="M30 106 72 60l36 29-38 45z" fill="#097b78"/><path d="m72 60 36 29-6-61z" fill="#2dd4bf"/><path d="m108 89 50-73 10 86-64 32z" fill="url(#facetB)"/><path d="m158 16 40 47-30 39z" fill="#6effd9"/><path d="m198 63 43 31-73 8z" fill="#118d85"/><path d="m108 89 50-73-30 92-58 26z" fill="url(#facetA)"/><path d="m158 16 60-6-20 53z" fill="#4be6c9" opacity=".85"/><path d="m218 10 23 84-43-31z" fill="#0a6867"/><path d="m70 134 58-26 40 13-70 23z" fill="#063f45"/><path d="m128 108 42 13 71-27-83 35z" fill="#22b8a7"/>
  </svg>
}
export default function BalanceCard() {
  const [show, setShow] = useState(false)
  return <StatCard eyebrow="Your health wallet" title="$18,540.00" className="balance-card" change="8.4%">
    <div className="balance-meta"><span>Yearly average</span><b>$15,200.00</b><button onClick={() => setShow(v => !v)}>How is it working? <ArrowUpRight size={13}/></button></div>
    {show && <div className="balance-explainer">Your wallet combines health savings, insurance cover, and out-of-pocket care in one view.</div>}
    <div className="assistant-banner"><div className="assistant-banner-copy"><span className="ai-label"><Sparkles size={12}/> AI assistant</span><b>Care, made clearer.</b><span>Analyzing your health spending</span></div><Crystal/><div className="banner-orb orb-one"/><div className="banner-orb orb-two"/></div>
  </StatCard>
}
