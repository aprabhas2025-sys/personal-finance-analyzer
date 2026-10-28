import { useMemo, useState } from 'react'
import { ArrowDownToLine, ArrowUpDown, Info, Search } from 'lucide-react'
import { CATEGORIES, type Category, type Transaction } from '../types'
import { money } from '../lib/finance'

type Props = { transactions: Transaction[]; onCategory?: (id: string, category: Category) => void; anomalies?: boolean }
const PAGE = 25
const fmtDate = (d: string) => new Date(`${d}T12:00:00`).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })

export default function TransactionsTable({ transactions, onCategory, anomalies = false }: Props) {
  const [filter, setFilter] = useState('All')
  const [search, setSearch] = useState('')
  const [newestFirst, setNewestFirst] = useState(true)
  const [shown, setShown] = useState(PAGE)

  const rows = useMemo(() => {
    const q = search.toLowerCase()
    return transactions
      .filter(t => filter === 'All' || (filter === 'Spending' ? t.type === 'debit' : t.type === 'credit'))
      .filter(t => `${t.description} ${t.category}`.toLowerCase().includes(q))
      .sort((a, b) => (newestFirst ? b.date.localeCompare(a.date) : a.date.localeCompare(b.date)))
  }, [transactions, filter, search, newestFirst])
  const visible = rows.slice(0, shown)

  return (
    <section className="card">
      {anomalies && <p className="note" style={{ marginBottom: 20 }}><Info size={18} /><span>Flags are prompts to review duplicates or unusually large amounts. They don’t prove a charge is wrong.</span></p>}
      <div className="toolbar">
        <label className="search-box"><Search size={18} /><input value={search} onChange={e => { setSearch(e.target.value); setShown(PAGE) }} placeholder="Search by description or category" aria-label="Search transactions" /></label>
        {!anomalies && (
          <div className="segmented" role="tablist" aria-label="Transaction type">
            {['All', 'Spending', 'Income'].map(t => <button key={t} role="tab" aria-selected={filter === t} onClick={() => { setFilter(t); setShown(PAGE) }}>{t}</button>)}
          </div>
        )}
        <button className="btn" onClick={() => setNewestFirst(v => !v)}><ArrowUpDown size={16} />{newestFirst ? 'Newest first' : 'Oldest first'}</button>
        <button className="btn" onClick={() => download(rows)} title="Download as CSV"><ArrowDownToLine size={16} />Export</button>
      </div>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Transaction</th><th>Category</th><th>Amount</th></tr></thead>
          <tbody>
            {visible.map(row => (
              <tr key={row.id}>
                <td><div className="tx-name"><span className={`tx-icon ${row.type === 'credit' ? 'tx-in' : 'tx-out'}`}>{row.type === 'credit' ? '↑' : '↓'}</span><span><b>{row.description}</b><small>{fmtDate(row.date)}</small></span></div></td>
                <td>{onCategory
                  ? <select className="category-select" value={row.category} onChange={e => onCategory(row.id, e.target.value as Category)} aria-label={`Change category for ${row.description}`}>{CATEGORIES.map(c => <option key={c}>{c}</option>)}</select>
                  : row.category}</td>
                <td><span className={row.type === 'credit' ? 'amount-in' : 'amount-out'}>{row.type === 'credit' ? '+' : '−'}{money(row.amount, 2)}</span></td>
              </tr>
            ))}
            {!visible.length && <tr><td colSpan={3} className="empty-row">No transactions match these filters.</td></tr>}
          </tbody>
        </table>
      </div>
      <div className="table-foot">
        <span>Showing {visible.length} of {rows.length.toLocaleString()}</span>
        {visible.length < rows.length && <button className="btn" onClick={() => setShown(s => s + PAGE * 2)}>Show more</button>}
      </div>
    </section>
  )
}

function download(rows: Transaction[]) {
  const header = 'date,description,amount,type,category,status'
  const body = rows.map(t => [t.date, `"${t.description.replaceAll('"', '""')}"`, t.amount, t.type, t.category, t.status].join(','))
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([[header, ...body].join('\n')], { type: 'text/csv' }))
  a.download = 'finance-transactions.csv'
  a.click()
  URL.revokeObjectURL(a.href)
}
