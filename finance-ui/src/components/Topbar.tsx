import { CalendarDays, Files, Menu, Moon, Plus, Sun, Upload } from 'lucide-react'
import type { Period } from '../types'

type Props = { onMenu: () => void; period: Period; onPeriod: (p: Period) => void; onUpload: () => void; onAddStatements: () => void; onAdd: () => void; theme: 'dark' | 'light'; onTheme: () => void }

export default function Topbar({ onMenu, period, onPeriod, onUpload, onAddStatements, onAdd, theme, onTheme }: Props) {
  return (
    <header className="topbar">
      <div className="topbar-start">
        <button className="icon-button mobile-menu" aria-label="Open navigation" onClick={onMenu}><Menu size={22} /></button>
        <label className="select-chip">
          <CalendarDays size={18} />
          <span>Showing</span>
          <select value={period} onChange={e => onPeriod(e.target.value as Period)} aria-label="Date range">
            <option>All data</option><option>30 days</option><option>3 months</option><option>6 months</option>
          </select>
        </label>
      </div>
      <div className="topbar-end">
        <button className="btn btn-primary" onClick={onAdd}><Plus size={18} /><span>Add cash</span></button>
        <button className="btn" onClick={onUpload} title="Replace loaded statements" aria-label="Replace loaded statements"><Upload size={18} /><span>Replace statements</span></button>
        <button className="btn" onClick={onAddStatements} title="Add more statements to the loaded data" aria-label="Add more statements"><Files size={18} /><span>Add statements</span></button>
        <button className="icon-button" onClick={onTheme} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}>
          {theme === 'dark' ? <Sun size={19} /> : <Moon size={19} />}
        </button>
      </div>
    </header>
  )
}
