import type { ReactNode } from 'react'
import { ArrowDownRight, ArrowUpRight, Ellipsis } from 'lucide-react'

type Props = { eyebrow: string; title: string; change?: string; icon?: ReactNode; children?: ReactNode; className?: string }
export default function StatCard({ eyebrow, title, change, icon, children, className = '' }: Props) {
  return <section className={`panel stat-card ${className}`}>
    <div className="panel-heading"><div><div className="eyebrow">{icon}{eyebrow}</div><div className="stat-value">{title}</div></div><button className="icon-button subtle-menu" aria-label={`${eyebrow} options`}><Ellipsis size={17}/></button></div>
    {change && <div className="stat-change"><span className="change-pill"><ArrowUpRight size={13}/>{change}</span><span className="muted-inline">Compared to last year</span><ArrowDownRight className="tiny-trend" size={14}/></div>}
    {children}
  </section>
}
