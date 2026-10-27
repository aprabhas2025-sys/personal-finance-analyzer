import {
  Activity, ArrowLeftRight, Bot, CircleHelp, CreditCard, HeartPulse, LayoutDashboard,
  Settings, ShieldCheck, Sparkles, X, Infinity as InfinityIcon, ChevronRight,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

const sections: { title: string; links: { label: string; icon: LucideIcon }[] }[] = [
  { title: 'Main', links: [
    { label: 'Overview', icon: LayoutDashboard }, { label: 'Health Wallet', icon: HeartPulse },
    { label: 'Transactions', icon: ArrowLeftRight }, { label: 'Insurance', icon: ShieldCheck },
    { label: 'Payment', icon: CreditCard },
  ] },
  { title: 'Features', links: [{ label: 'AI Insights', icon: Sparkles }, { label: 'AI Assistant', icon: Bot }] },
  { title: 'Tools', links: [{ label: 'Settings', icon: Settings }, { label: 'Help Center', icon: CircleHelp }] },
]

type Props = { active: string; onSelect: (label: string) => void; collapsed: boolean; mobileOpen: boolean; onClose: () => void }
export default function Sidebar({ active, onSelect, collapsed, mobileOpen, onClose }: Props) {
  return <>
    {mobileOpen && <button aria-label="Close navigation" className="sidebar-scrim" onClick={onClose} />}
    <aside className={`sidebar ${collapsed ? 'sidebar-collapsed' : ''} ${mobileOpen ? 'sidebar-mobile-open' : ''}`}>
      <div className="brand-row">
        <div className="brand-mark"><InfinityIcon size={22} strokeWidth={2.2} /></div>
        {!collapsed && <span className="brand-name">Hynex<span className="brand-dot">.</span></span>}
        <button className="icon-button sidebar-close" onClick={onClose} aria-label="Close sidebar"><X size={17}/></button>
      </div>
      <div className="nav-scroll">
        {sections.map(section => <section className="nav-section" key={section.title}>
          {!collapsed && <div className="nav-caption">{section.title}</div>}
          {section.links.map(({ label, icon: Icon }) => <button
            key={label} title={collapsed ? label : undefined}
            className={`nav-link ${active === label ? 'nav-link-active' : ''}`}
            onClick={() => { onSelect(label); onClose() }}>
            <Icon size={17} strokeWidth={1.8} /><span>{label}</span>
            {active === label && !collapsed && <ChevronRight className="nav-chevron" size={14} />}
          </button>)}
        </section>)}
      </div>
      {!collapsed && <div className="upgrade-card">
        <div className="upgrade-icon"><Sparkles size={16}/></div>
        <div className="upgrade-heading">Make more room for better care</div>
        <p>More insights, one calmer view of your health.</p>
        <button className="upgrade-button">Upgrade <ChevronRight size={14}/></button>
        <button className="learn-link">Learn more</button>
      </div>}
      <div className="sidebar-bottom"><div className="avatar-mini">JM</div>{!collapsed && <div className="profile-copy"><b>Jordan Miller</b><span>Personal account</span></div>}<Activity className="presence" size={14}/></div>
    </aside>
  </>
}

