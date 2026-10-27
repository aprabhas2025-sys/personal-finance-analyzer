import { ArrowUpRight, Heart, Plus, ShieldCheck, Users, X } from 'lucide-react'
import { useState } from 'react'
import StatCard from './StatCard'

const people = [
  { initials: 'JM', color: 'mint-avatar' }, { initials: 'AM', color: 'violet-avatar' },
  { initials: 'EM', color: 'gold-avatar' }, { initials: '＋', color: 'dark-avatar' },
]
export default function HealthMetrics() {
  const [covered, setCovered] = useState(12240)
  return <StatCard eyebrow="Insurance & health metrics" title={`$${covered.toLocaleString()}.00`} className="metrics-card">
    <div className="coverage-line"><div><span className="sub-label">Annual plan use</span><span className="coverage-amount">Active coverage</span></div><span className="coverage-pill"><ShieldCheck size={12}/>19%</span></div>
    <div className="mini-stat-grid"><div><span className="sub-label">Co-pay balance</span><b>$265</b></div><div><span className="sub-label">Health savings</span><b>$8,000</b></div></div>
    <div className="metrics-footer"><div className="family-group" aria-label="Family members">{people.map((person, i) => <div key={person.initials} className={`family-avatar ${person.color}`} style={{ zIndex: people.length - i }}>{person.initials}</div>)}<span className="family-label"><Users size={12}/> Family</span></div>
      <div className="coverage-controls"><button aria-label="Decrease coverage" onClick={() => setCovered(v => Math.max(0, v - 250))}><X size={13}/></button><button aria-label="Add coverage" onClick={() => setCovered(v => v + 250)}><Plus size={14}/></button></div></div>
    <div className="coverage-foot"><Heart size={12}/><span>Coverage ready for the moments that matter</span><ArrowUpRight size={13}/></div>
  </StatCard>
}

