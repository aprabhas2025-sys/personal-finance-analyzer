import { useMemo } from 'react'
import { CheckCircle2, CircleHelp, WandSparkles } from 'lucide-react'
import { categorySummary, money, monthlySummary } from '../lib/finance'
import type { Transaction } from '../types'

type Props = { transactions: Transaction[]; budgets: Record<string, number>; onBudget: (category: string, value: number) => void; onSuggest: () => void }
export default function BudgetsPanel({ transactions, budgets, onBudget, onSuggest }: Props) {
  const spend = useMemo(() => categorySummary(transactions), [transactions])
  const month = monthlySummary(transactions).slice(-1)[0]?.month
  const current = month ? transactions.filter(t => t.date.startsWith(month) && t.type === 'debit') : transactions.filter(t => t.type === 'debit')
  const currentBy = new Map<string, number>()
  current.forEach(t => currentBy.set(t.category, (currentBy.get(t.category) || 0) + t.amount))
  const categories = [...new Set([...spend.map(x => x.name), ...Object.keys(budgets)])].slice(0, 8)
  const monthLabel = month ? new Date(month + '-15T12:00:00').toLocaleDateString('en-IN', { month: 'long', year: 'numeric' }) : 'Month to date'
  const monthTotal = [...currentBy.values()].reduce((a, b) => a + b, 0)
  return <section className="panel budgets-card">
    <div className="panel-heading"><div><div className="eyebrow">Plan ahead <CircleHelp size={13}/></div><div className="chart-title">Monthly category budgets</div></div><button className="suggest-button" onClick={onSuggest}><WandSparkles size={13}/> Suggest</button></div>
    <p className="budget-description">Set a monthly limit, then compare your latest statement month with it.</p>
    {!categories.length ? <div className="empty-budget">Load transactions to set a budget.</div> : <div className="budget-list">{categories.map(category => {
      const used = currentBy.get(category) || 0, limit = budgets[category] || 0, pct = limit ? used / limit : 0
      return <div className="budget-row" key={category}>
        <div className="budget-row-head"><span>{category}</span><div><b>{money(used)}</b><em>{limit ? ` / ${money(limit)}` : ' / no limit'}</em></div></div>
        <div className="budget-progress"><i className={pct >= 1 ? 'over-budget' : ''} style={{ width: `${Math.min(100, pct * 100)}%` }}/></div>
        <div className="budget-row-foot"><input aria-label={`${category} monthly budget`} type="number" min="0" step="500" value={budgets[category] ?? ''} placeholder="Set limit" onChange={e => onBudget(category, Number(e.target.value))}/><span>{limit ? (pct >= 1 ? 'Over limit' : pct >= .8 ? 'Near limit' : 'On track') : 'Add a limit'}</span>{pct < .8 && limit > 0 && <CheckCircle2 size={12}/>}</div>
      </div>
    })}</div>}
    <div className="budget-total"><span>{monthLabel}</span><b>{money(monthTotal)} spent</b></div>
  </section>
}
