import { useEffect, useMemo, useRef, useState } from 'react'
import { AlertTriangle, ArrowRight, CheckCircle2, CircleAlert, FileUp, LoaderCircle, RefreshCw, Sparkles, TrendingUp } from 'lucide-react'
import sampleStatement from './data/sample-statement.csv?raw'
import Sidebar from './components/Sidebar'
import Topbar from './components/Topbar'
import TransactionsTable from './components/TransactionsTable'
import BudgetsPanel from './components/BudgetsPanel'
import AssistantPanel from './components/AssistantPanel'
import { CashFlowChart, CategoryChart, PALETTE, TrendChart } from './components/FinanceCharts'
import { categorySummary, findAnomalies, getPeriodStart, money, monthlySummary, parseBankCsv, recurringPayments } from './lib/finance'
import { type Category, type Period, type Transaction } from './types'

const TITLES: Record<string, string> = { Overview: 'Overview', Transactions: 'Transactions', Anomalies: 'Unusual activity', Subscriptions: 'Recurring payments', Forecast: 'Spending forecast', 'By category': 'Spending by category', 'Monthly spend': 'Monthly spending', Budgets: 'Budgets', Ask: 'Ask about your money' }
const SUBS: Record<string, string> = {
  Overview: 'A quick look at your money. Use the menu on the left for the details.',
  Transactions: 'Search, filter and correct the categories of your transactions.',
  Anomalies: 'Possible duplicate charges and unusually large amounts.',
  Subscriptions: 'Payments that repeat regularly, and what they add up to.',
  Forecast: 'A simple estimate of next month, based on recent spending.',
  'By category': 'See which categories take the biggest share of your spending.',
  'Monthly spend': 'How your spending and income change from month to month.',
  Budgets: 'Set a monthly limit for the categories that matter to you.',
  Ask: 'Ask a question in plain English about the statement you loaded.',
}
const fmtDate = (d: string) => new Date(`${d}T12:00:00`).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })

function Kpi({ label, value, note, color }: { label: string; value: string; note: string; color: string }) {
  return (
    <section className="card kpi">
      <span className="kpi-label"><i className="kpi-dot" style={{ background: color }} />{label}</span>
      <b className="kpi-value">{value}</b>
      <span className="kpi-note">{note}</span>
    </section>
  )
}

function Highlight({ label, value, go, onClick, icon }: { label: string; value: string; go: string; onClick: () => void; icon: React.ReactNode }) {
  return (
    <button className="card highlight" onClick={onClick}>
      <span className="highlight-label">{icon} {label}</span>
      <b className="highlight-value">{value}</b>
      <span className="highlight-go">{go} <ArrowRight size={16} /></span>
    </button>
  )
}

function EmptyState({ onUpload, onSample }: { onUpload: () => void; onSample: () => void }) {
  return (
    <section className="card empty-state">
      <div className="empty-icon"><FileUp size={26} /></div>
      <h2>Start with a statement</h2>
      <p>Import a bank or UPI statement (CSV). It is processed in this browser, and you can remove it any time.</p>
      <div className="empty-actions">
        <button className="btn btn-primary" onClick={onUpload}><FileUp size={17} />Choose CSV</button>
        <button className="btn" onClick={onSample}><Sparkles size={17} />Load sample data</button>
      </div>
      <small>CSV files only · Sample data is synthetic</small>
    </section>
  )
}

function App() {
  const root = document.getElementById('root')
  const userScope = root?.getAttribute('data-user-id') || 'local'
  const email = root?.getAttribute('data-user-email') || ''
  const transactionStorageKey = `finance-ui-transactions-${userScope}`
  const budgetStorageKey = `finance-ui-budgets-${userScope}`

  const [active, setActive] = useState('Overview')
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [period, setPeriod] = useState<Period>('All data')
  const [budgets, setBudgets] = useState<Record<string, number>>({})
  const [theme, setTheme] = useState<'dark' | 'light'>(() => (localStorage.getItem('finance-ui-theme') === 'dark' ? 'dark' : 'light'))
  const [loading, setLoading] = useState(true)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const fileInput = useRef<HTMLInputElement>(null)
  const workspace = useRef<HTMLElement>(null)

  useEffect(() => {
    try {
      const saved = localStorage.getItem(transactionStorageKey)
      if (saved) { setTransactions(JSON.parse(saved) as Transaction[]); setLoading(false) } else void loadSample()
    } catch { void loadSample() }
    const b = localStorage.getItem(budgetStorageKey)
    if (b) try { setBudgets(JSON.parse(b) as Record<string, number>) } catch { /* ignore invalid local preferences */ }
  }, [])
  useEffect(() => { if (transactions.length) localStorage.setItem(transactionStorageKey, JSON.stringify(transactions)) }, [transactions])
  useEffect(() => { localStorage.setItem(budgetStorageKey, JSON.stringify(budgets)) }, [budgets])
  useEffect(() => { localStorage.setItem('finance-ui-theme', theme) }, [theme])
  useEffect(() => { workspace.current?.scrollTo({ top: 0 }) }, [active])
  useEffect(() => { if (!notice) return; const t = setTimeout(() => setNotice(''), 7000); return () => clearTimeout(t) }, [notice])

  async function loadSample() {
    setLoading(true); setError('')
    try { const rows = parseBankCsv(sampleStatement); setTransactions(rows); setNotice(`Loaded ${rows.length.toLocaleString()} sample transactions (synthetic data).`) }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not load sample data.') }
    finally { setLoading(false) }
  }
  async function onFile(file?: File) {
    if (!file) return
    setLoading(true); setError('')
    try {
      const rows = parseBankCsv(await file.text())
      setTransactions(rows); setPeriod('All data'); setNotice(`${rows.length.toLocaleString()} transactions imported from ${file.name}.`); setActive('Overview')
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not read this CSV.') }
    finally { setLoading(false); if (fileInput.current) fileInput.current.value = '' }
  }
  function clearData() {
    setTransactions([]); localStorage.removeItem(transactionStorageKey); setActive('Overview'); setNotice('Your statement was removed from this browser.')
  }

  const periodStart = getPeriodStart(transactions, period)
  const filtered = useMemo(() => transactions.filter(t => !periodStart || t.date >= periodStart), [transactions, periodStart])
  const debits = filtered.filter(t => t.type === 'debit')
  const credits = filtered.filter(t => t.type === 'credit')
  const spent = debits.reduce((a, b) => a + b.amount, 0)
  const received = credits.reduce((a, b) => a + b.amount, 0)
  const net = received - spent
  const rate = received ? net / received : 0
  const anomalies = useMemo(() => findAnomalies(filtered), [filtered])
  const recurring = useMemo(() => recurringPayments(filtered), [filtered])
  const months = useMemo(() => monthlySummary(filtered), [filtered])
  const categories = useMemo(() => categorySummary(filtered), [filtered])
  const last3 = months.slice(-3)
  const nextMonth = last3.reduce((a, b) => a + b.spend, 0) / Math.max(1, last3.length)

  function updateCategory(id: string, category: Category) {
    setTransactions(rows => rows.map(t => (t.id === id ? { ...t, category, confidence: 1 } : t)))
  }
  function suggestBudgets() {
    const n = Math.max(1, new Set(transactions.map(t => t.date.slice(0, 7))).size)
    const next: Record<string, number> = { ...budgets }
    categorySummary(transactions).forEach(x => { next[x.name] = Math.ceil((x.value / n * 1.2) / 500) * 500 })
    setBudgets(next); setNotice('Suggested monthly limits from your average spending, plus a 20% cushion.')
  }

  const dateLine = filtered.length ? `${fmtDate(filtered[0].date)} to ${fmtDate(filtered[filtered.length - 1].date)} · ${filtered.length.toLocaleString()} transactions` : 'Load a statement to begin.'
  const summary = !received ? 'Add income transactions to see your savings.' : net >= 0
    ? `You spent ${money(spent)} and received ${money(received)}, so you kept ${(rate * 100).toFixed(1)}% of your income.`
    : `You spent ${money(spent)} but received ${money(received)}, so spending was higher than income in this period.`

  return (
    <div className={`app-shell ${theme === 'dark' ? 'theme-dark' : ''}`}>
      <Sidebar active={active} onSelect={setActive} collapsed={collapsed} mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} email={email} onClear={clearData} />
      <main className="workspace" ref={workspace}>
        <Topbar onMenu={() => { if (window.innerWidth < 900) setMobileOpen(true); else setCollapsed(v => !v) }} period={period} onPeriod={setPeriod} onUpload={() => fileInput.current?.click()} theme={theme} onTheme={() => setTheme(v => (v === 'dark' ? 'light' : 'dark'))} />
        <input ref={fileInput} className="file-input-hidden" type="file" accept=".csv,.txt,text/csv,text/plain,application/vnd.ms-excel" onChange={e => void onFile(e.target.files?.[0])} />
        <div className="page">
          <div className="page-heading">
            <h1>{TITLES[active] || 'Overview'}</h1>
            <p>{SUBS[active] || SUBS.Overview}</p>
            {transactions.length > 0 && <p className="page-meta">{dateLine}</p>}
          </div>

          {error && <div className="notice notice-error"><CircleAlert size={18} />{error}<button onClick={() => setError('')}>Dismiss</button></div>}
          {notice && <div className="notice"><CheckCircle2 size={18} />{notice}<button onClick={() => setNotice('')}>Dismiss</button></div>}
          {loading && <div className="loading-strip"><LoaderCircle size={18} /> Loading statement data…</div>}

          {!transactions.length && !loading ? <EmptyState onUpload={() => fileInput.current?.click()} onSample={() => void loadSample()} /> : <>

            {active === 'Overview' && <>
              <div className="summary-line"><Sparkles size={20} />{summary}</div>
              <div className="kpis">
                <Kpi label="Money in" value={money(received)} note="Income received" color="var(--income)" />
                <Kpi label="Money out" value={money(spent)} note="Total spending" color="var(--spend)" />
                <Kpi label="Net savings" value={`${net < 0 ? '−' : ''}${money(Math.abs(net))}`} note="Money in minus money out" color={PALETTE[1]} />
                <Kpi label="Savings rate" value={received ? `${(rate * 100).toFixed(1)}%` : 'n/a'} note="Share of income you kept" color={PALETTE[0]} />
              </div>
              <div className="overview-charts"><CashFlowChart transactions={filtered} /><CategoryChart transactions={filtered} /></div>
              <div className="highlights">
                <Highlight icon={<AlertTriangle size={18} />} label="Unusual charges" value={anomalies.length ? `${anomalies.length} to review` : 'All clear'} go="Review them" onClick={() => setActive('Anomalies')} />
                <Highlight icon={<RefreshCw size={18} />} label="Recurring payments" value={`${recurring.length} found`} go="See subscriptions" onClick={() => setActive('Subscriptions')} />
                <Highlight icon={<TrendingUp size={18} />} label="Estimated next month" value={money(nextMonth)} go="Open forecast" onClick={() => setActive('Forecast')} />
              </div>
            </>}

            {active === 'Transactions' && <TransactionsTable transactions={filtered} onCategory={updateCategory} />}

            {active === 'Anomalies' && <div className="stack">
              <div className="stats-3">
                <section className="card stat"><span>Flagged transactions</span><b>{anomalies.length}</b></section>
                <section className="card stat"><span>Total amount to review</span><b>{money(anomalies.reduce((a, b) => a + b.amount, 0))}</b></section>
                <section className="card stat"><span>How flags work</span><p>Repeated charges and amounts far above their category average are flagged.</p></section>
              </div>
              <TransactionsTable transactions={anomalies} anomalies />
            </div>}

            {active === 'Subscriptions' && <div className="stack">
              <div className="stats-3">
                <section className="card stat"><span>Recurring patterns</span><b>{recurring.length}</b></section>
                <section className="card stat"><span>Needs</span><p>At least three similar charges from one merchant before we suggest a pattern.</p></section>
              </div>
              <div className="recurring-grid">
                {recurring.map(r => (
                  <section className="card recurring-card" key={r.merchant}>
                    <span className="eyebrow">{r.count} charges seen</span>
                    <h3>{r.merchant}</h3>
                    <b>{money(r.amount)}<small> average per charge</small></b>
                    <p>Last seen {fmtDate(r.last)}</p>
                  </section>
                ))}
                {!recurring.length && <div className="card empty-row" style={{ gridColumn: '1 / -1' }}>No recurring charges found yet. More history may reveal regular payments.</div>}
              </div>
            </div>}

            {active === 'Forecast' && <div className="stack">
              <div className="stats-3">
                <section className="card stat"><span>Estimated next month</span><b>{money(nextMonth)}</b><small>Average of the latest {Math.min(3, months.length)} months</small></section>
                <section className="card stat"><span>History available</span><b>{months.length} months</b><small>{months.length < 6 ? 'Short history, so treat this as a rough guide.' : 'More history gives context, not certainty.'}</small></section>
                <section className="card stat"><span>Good to know</span><p>This is a planning aid based on recent averages. It is not a promise.</p></section>
              </div>
              <TrendChart transactions={filtered} forecast />
            </div>}

            {active === 'By category' && <div className="two-col">
              <CategoryChart transactions={filtered} />
              <section className="card">
                <div className="card-head"><div><h2 className="card-title">All categories</h2><p className="card-sub">Highest spending first</p></div></div>
                {categories.map((c, i) => (
                  <div className="cat-row" key={c.name}><i style={{ background: PALETTE[i % PALETTE.length] }} /><span>{c.name}</span><b>{money(c.value)}</b><small>{spent ? `${Math.round(c.value / spent * 100)}%` : ''}</small></div>
                ))}
              </section>
            </div>}

            {active === 'Monthly spend' && <div className="stack"><TrendChart transactions={filtered} /><CashFlowChart transactions={filtered} /></div>}

            {active === 'Budgets' && <BudgetsPanel transactions={transactions} budgets={budgets} onBudget={(c, v) => setBudgets(x => ({ ...x, [c]: v }))} onSuggest={suggestBudgets} />}

            {active === 'Ask' && <AssistantPanel transactions={filtered} />}
          </>}

          <footer className="page-footer">Finance Analyzer · Your statement stays on this device · Not financial advice</footer>
        </div>
      </main>
    </div>
  )
}
export default App
