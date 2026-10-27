import { Bell, CalendarDays, ChevronDown, Menu, Search, SlidersHorizontal } from 'lucide-react'

type Props = { onMenu: () => void; active: string }
export default function Topbar({ onMenu, active }: Props) {
  return <header className="topbar">
    <div className="topbar-start">
      <button className="icon-button mobile-menu" aria-label="Open navigation" onClick={onMenu}><Menu size={19}/></button>
      <button className="report-button"><SlidersHorizontal size={15}/><span>Reports</span></button>
      <div className="date-chip"><CalendarDays size={14}/><span>12:37 PM, Wed</span><ChevronDown size={13}/></div>
    </div>
    <div className="topbar-search"><Search size={16}/><input aria-label="Search health metrics" placeholder={`Search ${active === 'Overview' ? 'for any health metrics' : active.toLowerCase()}...`} /><kbd>⌘ K</kbd></div>
    <div className="topbar-end">
      <button className="icon-button notification-button" aria-label="Notifications"><Bell size={17}/><i /></button>
      <button className="user-avatar" aria-label="Open profile">JM</button>
    </div>
  </header>
}
