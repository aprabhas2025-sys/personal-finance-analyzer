import { useMemo } from 'react'
import { WandSparkles } from 'lucide-react'
import { categorySummary, money, monthlySummary } from '../lib/finance'
import type { Transaction } from '../types'

type Props = { transactions: Transaction[]; budgets: Record<string, number>; onBudget: (category: string, value: number) => void; onSuggest: () => void }

export default function BudgetsPanel({ transactions, budgets, onBudget, onSuggest }: Props) {
  const spend = useMemo(() => categorySummary(transactions), [transactions])
  const month = monthlySummary(transactions).slice(-1)[0]?.month
  const current = month ? transactions.filter(t => t.date.startsWith(month) && t.type === 'debit') : transactions.filter(t => t.type === 'debit')
  const currentBy = new Map<string, number>()
  current.forEach(t => currentBy.set(t.category, (currentBy.get(t.category) || 0) + t.amount))
  const categories = [...new Set([...spend.map(x => x.name), ...Object.keys(budgets)])].slice(0, 10)
  const monthLabel = month ? new Date(`${month}-15T12:00:00`).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' }) : 'Month to date'
  const monthTotal = [...currentBy.values()].reduce((a, b) => a + b, 0)

  return (
    <div className="stack">
      <div className="feature-head">
        <p className="card-sub" style={{ fontSize: 16 }}>{monthLabel} · <b style={{ color: 'var(--text)' }}>{money(monthTotal)}</b> spent so far</p>
        <button className="btn btn-primary" onClick={onSuggest}><WandSparkles size={17} />Suggest limits</button>
      </div>
      {!categories.length ? <div className="card empty-row">Load transactions to set a budget.</div> : (
        <div className="budget-grid">
          {categories.map(category => {
            const used = currentBy.get(category) || 0
            const limit = budgets[category] || 0
            const pct = limit ? used / limit : 0
            const state = !limit ? '' : pct >= 1 ? 'over' : pct >= .8 ? 'warn' : 'ok'
            return (
              <section className="card" key={category}>
                <div className="budget-head"><h3>{category}</h3><span><b>{money(used)}</b>{limit ? ` of ${money(limit)}` : ' · no limit set'}</span></div>
                <div className="progress" aria-hidden="true"><i className={state === 'over' ? 'over' : state === 'warn' ? 'warn' : ''} style={{ width: `${Math.min(100, pct * 100)}%` }} /></div>
                <div className="budget-foot">
                  <input aria-label={`${category} monthly limit`} type="number" min="0" step="500" value={budgets[category] ?? ''} placeholder="Set limit (₹)" onChange={e => onBudget(category, Number(e.target.value))} />
                  <span className={`budget-status ${state}`}>{!limit ? 'No limit yet' : state === 'over' ? 'Over limit' : state === 'warn' ? 'Near limit' : 'On track'}</span>
                </div>
              </section>
            )
          })}
        </div>
      )}
    </div>
  )
}
