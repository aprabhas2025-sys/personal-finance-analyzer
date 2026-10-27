import { lazy, Suspense, useState } from 'react'
import { Activity, ArrowUpRight, CalendarDays, ChevronDown, HeartPulse, Leaf } from 'lucide-react'
import Sidebar from './components/Sidebar'
import Topbar from './components/Topbar'
import BalanceCard from './components/BalanceCard'
import HealthMetrics from './components/HealthMetrics'
const SmartHealthFinance = lazy(() => import('./components/SmartHealthFinance'))
import SpendingTracker from './components/SpendingTracker'
import TransactionsTable from './components/TransactionsTable'
import AIChat from './components/AIChat'

function Greeting() {
  return <div className="page-heading"><div><div className="page-kicker"><span className="kicker-pulse"/> WEDNESDAY, OCTOBER 28, 2026</div><h1>Your health, <span>in balance.</span></h1><p>A calmer view of your care and the money behind it.</p></div><button className="period-button"><CalendarDays size={14}/> Last 30 days <ChevronDown size={13}/></button></div>
}
function WellnessStrip() {
  return <div className="wellness-strip"><div className="wellness-icon"><HeartPulse size={16}/></div><span><b>Looking good, Jordan.</b> Your care spending is tracking 8.4% below last year.</span><div className="wellness-detail"><span><Leaf size={13}/> Preventive care on track</span><ArrowUpRight size={14}/></div></div>
}
export default function App() {
  const [active, setActive] = useState('Overview')
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  return <div className="app-shell">
    <Sidebar active={active} onSelect={setActive} collapsed={collapsed} mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
    <main className={`workspace ${collapsed ? 'workspace-expanded' : ''}`}>
      <Topbar active={active} onMenu={() => { if (window.innerWidth < 820) setMobileOpen(true); else setCollapsed(value => !value) }}/>
      <div className="main-content">
        <Greeting />
        <WellnessStrip />
        <div className="dashboard-grid">
          <BalanceCard />
          <HealthMetrics />
          <Suspense fallback={<section className="panel smart-card chart-loading">Preparing your health trends…</section>}><SmartHealthFinance /></Suspense>
          <SpendingTracker />
          <TransactionsTable />
          <AIChat />
        </div>
        <footer className="page-footer"><span>Hynex <span className="footer-dot">·</span> A clearer kind of care</span><span><Activity size={12}/> Your data stays yours</span></footer>
      </div>
    </main>
  </div>
}


