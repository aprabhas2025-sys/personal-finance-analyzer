import { useMemo, useState } from 'react'
import { ArrowDownToLine, ArrowUpRight, Search, SlidersHorizontal } from 'lucide-react'

type Status = 'Paid' | 'Claimed' | 'Pending'
type Transaction = { category: string; detail: string; amount: number; status: Status; initials: string; tone: string; date: string }
const records: Transaction[] = [
  { category: 'Consultation', detail: 'Northstar Clinic', amount: 120, status: 'Paid', initials: 'NC', tone: 'mint-avatar', date: 'Today, 10:42 AM' },
  { category: 'Pharmacy', detail: 'Wellness Pharmacy', amount: 265, status: 'Claimed', initials: 'WP', tone: 'violet-avatar', date: 'Yesterday' },
  { category: 'Insurance', detail: 'Horizon Health', amount: 1000, status: 'Pending', initials: 'HH', tone: 'gold-avatar', date: 'Oct 24, 2026' },
  { category: 'Lab test', detail: 'Clearview Labs', amount: 500, status: 'Paid', initials: 'CL', tone: 'blue-avatar', date: 'Oct 22, 2026' },
]
const filters = ['All records', 'Pending', 'Completed'] as const
type Filter = typeof filters[number]
export default function TransactionsTable() {
  const [filter, setFilter] = useState<Filter>('All records')
  const [query, setQuery] = useState('')
  const list = useMemo(() => records.filter(row => {
    const matchesFilter = filter === 'All records' || (filter === 'Pending' ? row.status === 'Pending' : row.status !== 'Pending')
    return matchesFilter && `${row.category} ${row.detail} ${row.status}`.toLowerCase().includes(query.toLowerCase())
  }), [filter, query])
  return <section className="panel transactions-card">
    <div className="panel-heading"><div><div className="eyebrow">Activity <span className="count-pill">04</span></div><div className="chart-title">Recent transactions</div></div><button className="icon-button subtle-menu" aria-label="Filter transactions"><SlidersHorizontal size={15}/></button></div>
    <div className="transaction-tools"><div className="table-search"><Search size={13}/><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search records" aria-label="Search transactions"/></div><button className="icon-button export-button" aria-label="Export records"><ArrowDownToLine size={15}/></button></div>
    <div className="filter-tabs" role="tablist" aria-label="Transaction status">{filters.map(tab => <button role="tab" aria-selected={filter === tab} key={tab} className={filter === tab ? 'filter-tab filter-active' : 'filter-tab'} onClick={() => setFilter(tab)}>{tab}</button>)}</div>
    <div className="table-wrap"><table><thead><tr><th>Category</th><th>Value</th><th>Status</th></tr></thead><tbody>{list.map(row => <tr key={row.detail}><td><div className="transaction-name"><span className={`transaction-avatar ${row.tone}`}>{row.initials}</span><span><b>{row.category}</b><small>{row.detail}</small></span></div></td><td><b className="amount-cell">${row.amount.toLocaleString()}.00</b></td><td><span className={`status-pill status-${row.status.toLowerCase()}`}><i/>{row.status}</span></td></tr>)}{list.length === 0 && <tr><td className="empty-row" colSpan={3}>No transactions match that search.</td></tr>}</tbody></table></div>
    <button className="view-all">View all transactions <ArrowUpRight size={13}/></button>
  </section>
}
