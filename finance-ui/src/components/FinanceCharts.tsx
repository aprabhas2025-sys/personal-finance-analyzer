import { useMemo } from 'react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { categorySummary, monthlySummary, money, shortMonth } from '../lib/finance'
import type { Transaction } from '../types'

export const PALETTE = ['#14b8a6', '#6366f1', '#f59e0b', '#ec4899', '#38bdf8', '#84cc16', '#f97316', '#94a3b8']
const axis = { fill: 'var(--muted)', fontSize: 13 }
const kfmt = (v: number) => (v >= 100000 ? `₹${(v / 100000).toFixed(v % 100000 ? 1 : 0)}L` : `₹${Math.round(v / 1000)}k`)

function FinanceTooltip({ active, payload, label }: { active?: boolean; payload?: { name?: string; value?: number; color?: string }[]; label?: string }) {
  if (!active || !payload?.length) return null
  return (
    <div className="finance-tooltip">
      <span>{label}</span>
      {payload.map((p, i) => <div key={`${p.name}-${i}`} style={{ color: p.color }}><span>{p.name}</span><b>{money(p.value || 0)}</b></div>)}
    </div>
  )
}

export function CashFlowChart({ transactions }: { transactions: Transaction[] }) {
  const data = useMemo(() => monthlySummary(transactions).slice(-12).map(x => ({ ...x, month: shortMonth(x.month) })), [transactions])
  return (
    <section className="card">
      <div className="card-head">
        <div><h2 className="card-title">Income vs. spending</h2><p className="card-sub">Month by month, last 12 months</p></div>
      </div>
      <div className="chart-area">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 4, bottom: 0, left: 0 }} barGap={4}>
            <CartesianGrid vertical={false} stroke="var(--grid)" />
            <XAxis dataKey="month" tickLine={false} axisLine={false} tick={axis} tickMargin={10} interval="preserveStartEnd" />
            <YAxis width={58} tickLine={false} axisLine={false} tick={axis} tickFormatter={kfmt} />
            <Tooltip content={<FinanceTooltip />} cursor={{ fill: 'var(--surface-2)' }} />
            <Bar dataKey="income" name="Income" fill="var(--income)" radius={[5, 5, 0, 0]} maxBarSize={22} />
            <Bar dataKey="spend" name="Spending" fill="var(--spend)" radius={[5, 5, 0, 0]} maxBarSize={22} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="chart-legend"><span><i style={{ background: 'var(--income)' }} />Income</span><span><i style={{ background: 'var(--spend)' }} />Spending</span></div>
    </section>
  )
}

export function CategoryChart({ transactions, rows = 5 }: { transactions: Transaction[]; rows?: number }) {
  const all = useMemo(() => categorySummary(transactions), [transactions])
  const total = all.reduce((s, x) => s + x.value, 0)
  const top = all.slice(0, rows)
  const rest = all.slice(rows).reduce((s, x) => s + x.value, 0)
  const data = rest > 0 ? [...top, { name: 'Everything else', value: rest }] : top
  return (
    <section className="card">
      <div className="card-head"><div><h2 className="card-title">Where your money goes</h2><p className="card-sub">Share of total spending</p></div></div>
      <div className="donut-wrap">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius="68%" outerRadius="100%" paddingAngle={2} stroke="none">
              {data.map((x, i) => <Cell key={x.name} fill={PALETTE[i % PALETTE.length]} />)}
            </Pie>
            <Tooltip formatter={v => money(Number(v))} />
          </PieChart>
        </ResponsiveContainer>
        <div className="donut-center"><span>Total spent</span><b>{money(total)}</b></div>
      </div>
      <div className="legend-list">
        {data.map((x, i) => (
          <div className="legend-row" key={x.name}>
            <i style={{ background: PALETTE[i % PALETTE.length] }} /><span>{x.name}</span><b>{money(x.value)}</b><small>{total ? `${Math.round((x.value / total) * 100)}%` : ''}</small>
          </div>
        ))}
      </div>
    </section>
  )
}

export function TrendChart({ transactions, forecast = false }: { transactions: Transaction[]; forecast?: boolean }) {
  const data = useMemo(() => {
    const months = monthlySummary(transactions)
    const avg = months.slice(-3).reduce((a, b) => a + b.spend, 0) / Math.max(1, months.slice(-3).length)
    return months.slice(-12).map((x, i, a) => ({ ...x, month: shortMonth(x.month), projection: forecast && i === a.length - 1 ? avg : undefined }))
  }, [transactions, forecast])
  return (
    <section className="card">
      <div className="card-head"><div><h2 className="card-title">{forecast ? 'Monthly spending and estimate' : 'Monthly spending trend'}</h2><p className="card-sub">Last 12 months</p></div></div>
      <div className="chart-area">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <defs><linearGradient id="spendFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#f97316" stopOpacity={.25} /><stop offset="100%" stopColor="#f97316" stopOpacity={0} /></linearGradient></defs>
            <CartesianGrid vertical={false} stroke="var(--grid)" />
            <XAxis dataKey="month" tickLine={false} axisLine={false} tick={axis} tickMargin={10} interval="preserveStartEnd" />
            <YAxis width={58} tickLine={false} axisLine={false} tick={axis} tickFormatter={kfmt} />
            <Tooltip content={<FinanceTooltip />} />
            <Area type="monotone" dataKey="spend" name="Spending" stroke="#f97316" strokeWidth={2.5} fill="url(#spendFill)" dot={false} activeDot={{ r: 5 }} />
            {forecast && <Area type="monotone" dataKey="projection" name="Estimate" stroke="#6366f1" strokeWidth={2.5} strokeDasharray="6 5" fill="none" dot={{ r: 5, fill: '#6366f1' }} />}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
