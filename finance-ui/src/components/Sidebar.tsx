import { AlertTriangle, ArrowLeftRight, Bot, CircleDollarSign, LayoutDashboard, Repeat2, TrendingUp, WalletCards, BarChart3 } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

/** Original Finora mark: three rising bars and a spark, drawn as inline SVG so it can animate. */
function FinoraMark() {
  return (
    <svg className="mark-svg" viewBox="0 0 24 24" width="21" height="21" fill="none" aria-hidden="true">
      <rect className="mark-bar mark-bar-1" x="4.2" y="13.2" width="3.4" height="6.6" rx="1.7" fill="currentColor" opacity=".78" />
      <rect className="mark-bar mark-bar-2" x="10.3" y="9.6" width="3.4" height="10.2" rx="1.7" fill="currentColor" opacity=".9" />
      <rect className="mark-bar mark-bar-3" x="16.4" y="5.6" width="3.4" height="14.2" rx="1.7" fill="currentColor" />
      <circle className="mark-spark" cx="18.1" cy="2.7" r="1.5" fill="#fde68a" />
    </svg>
  )
}

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
          <div className="brand-mark"><FinoraMark /></div>
          <span className="brand-name">Finora<span className="brand-dot">.</span></span>
          <button className="sidebar-close" onClick={onClose} aria-label="Close navigation">×</button>
        </div>
        <nav className="nav-scroll" aria-label="Main">
          {nav.map((group, i) => (
            <section className="nav-section" key={group.title ?? i} style={{ ['--g' as string]: i }}>
              {group.title && <div className="nav-caption">{group.title}</div>}
              {group.items.map(({ label, icon: Icon }, j) => (
                <button
                  key={label}
                  style={{ ['--i' as string]: i * 3 + j }}
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
