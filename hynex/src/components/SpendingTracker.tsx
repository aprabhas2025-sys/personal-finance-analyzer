import { CheckCircle2, CircleHelp, Sparkles, Tags } from 'lucide-react'
import StatCard from './StatCard'

const groups = [
  { label: 'Hospitals', amount: 40, color: 'bar-mint' }, { label: 'Lab tests', amount: 25, color: 'bar-lime' },
  { label: 'Medication', amount: 35, color: 'bar-yellow' }, { label: 'Other', amount: 20, color: 'bar-gray' },
]
export default function SpendingTracker() {
  return <StatCard eyebrow="Healthcare financial tracking" title="$1,390" className="spending-card">
    <div className="spending-target"><span>of $2,000 monthly plan</span><b>69.5%</b></div>
    <div className="progress-track">{groups.map(group => <i key={group.label} className={group.color} style={{ width: `${(group.amount / 120) * 100}%` }} title={`${group.label} ${group.amount}%`}/>)}</div>
    <div className="legend-compact">{groups.map(group => <span key={group.label}><i className={group.color}/>{group.label} <b>{group.amount}%</b></span>)}</div>
    <div className="tracker-divider" />
    <div className="insight-row"><div className="insight-icon mint-icon"><Sparkles size={14}/></div><div><span>Care mix</span><b>70% care <em>·</em> 30% prevention</b></div><span className="tag insight-tag">Insight</span></div>
    <div className="insight-row"><div className="insight-icon lime-icon"><Tags size={14}/></div><div><span>Coverage mix</span><b>60% insurance <em>·</em> 40% out-of-pocket</b></div><span className="tag verify-tag"><CheckCircle2 size={11}/> Verify</span></div>
    <div className="spending-foot"><CircleHelp size={12}/> Personal plan refreshes each month</div>
  </StatCard>
}

