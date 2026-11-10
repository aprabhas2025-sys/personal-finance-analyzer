import { Activity, AlertTriangle, ArrowLeftRight, Bot, CircleDollarSign, LayoutDashboard, Repeat2, TrendingUp, WalletCards, BarChart3 } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

type Group = { title?: string; items: { label: string; icon: LucideIcon }[] }

const nav: Group[] = [
  { items: [{ label: 'Overview', icon: LayoutDashboard }] },
  { title: 'Browse', items: [
    { label: 'Transactions', icon: ArrowLeftRight },
    { label: 'By category', icon: CircleDollarSign },
    { label: 'Monthly spend', icon: BarChart3 },
  ] },
  { title: 'Insights', items: [
    { label: 'Anomalies', icon: AlertTriangle },
    { label: 'Subscriptions', icon: Repeat2 },
    { label: 'Forecast', icon: TrendingUp },
  ] },
  { title: 'Plan', items: [
    { label: 'Budgets', icon: WalletCards },
    { label: 'Ask', icon: Bot },
  ] },
]

type Props = { active: string; onSelect: (x: string) => void; collapsed: boolean; mobileOpen: boolean; onClose: () => void; email: string; onClear: () => void }

export default function Sidebar({ active, onSelect, collapsed, mobileOpen, onClose, email, onClear }: Props) {
  const initial = (email.trim()[0] || 'F').toUpperCase()
  return (
    <>
      {mobileOpen && <button aria-label="Close navigation" className="sidebar-scrim" onClick={onClose} />}
      <aside className={`sidebar ${collapsed ? 'sidebar-collapsed' : ''} ${mobileOpen ? 'sidebar-mobile-open' : ''}`}>
        <div className="brand-row">
          <div className="brand-mark"><Activity size={20} /></div>
          <span className="brand-name">Finora<span className="brand-dot">.</span></span>
          <button className="sidebar-close" onClick={onClose} aria-label="Close navigation">×</button>
        </div>
        <nav className="nav-scroll" aria-label="Main">
          {nav.map((group, i) => (
            <section className="nav-section" key={group.title ?? i}>
              {group.title && <div className="nav-caption">{group.title}</div>}
              {group.items.map(({ label, icon: Icon }) => (
                <button
                  key={label}
                  title={collapsed ? label : undefined}
                  aria-current={active === label ? 'page' : undefined}
                  className={`nav-link ${active === label ? 'nav-link-active' : ''}`}
                  onClick={() => { onSelect(label); onClose() }}
                >
                  <Icon size={20} strokeWidth={1.8} />
                  <span>{label}</span>
                </button>
              ))}
            </section>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="sidebar-user">
            <div className="avatar">{initial}</div>
            <div className="sidebar-foot-copy" style={{ minWidth: 0 }}>
              <b title={email}>{email || 'Your workspace'}</b>
              <small>Data stays on this device</small>
            </div>
          </div>
          <button className="link-button sidebar-foot-copy" onClick={onClear}>Clear my data</button>
        </div>
      </aside>
    </>
  )
}
