import { useMemo } from 'react'
import { Area, AreaChart, CartesianGrid, PolarAngleAxis, RadialBar, RadialBarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { categorySummary, monthlySummary, money, shortMonth } from '../lib/finance'
import type { Transaction } from '../types'

export const PALETTE = ['#2dd4bf', '#818cf8', '#f472b6', '#fbbf24', '#38bdf8', '#a3e635', '#fb923c', '#94a3b8']
const REST = '#64748b'
const axis = { fill: 'var(--muted)', fontSize: 10 }
const kfmt = (v: number) => (v >= 100000 ? `₹${(v / 100000).toFixed(v % 100000 ? 1 : 0)}L` : `₹${Math.round(v / 1000)}k`)

/** Glowing "live" marker on the newest data point. */
const liveDot = (color: string, last: number) => (p: { cx?: number; cy?: number; index?: number }) => {
  if (p.index !== last || p.cx == null || p.cy == null) return <g key={p.index} />
  return (
    <g key={p.index}>
      <circle className="pulse-ring" cx={p.cx} cy={p.cy} r={7} fill={color} opacity={0.45} />
      <circle cx={p.cx} cy={p.cy} r={4} fill={color} stroke="var(--surface)" strokeWidth={2} />
    </g>
  )
}

type TipItem = { name?: string; value?: number; color?: string; payload?: { net?: number; income?: number; spend?: number } }
function FinanceTooltip({ active, payload, label }: { active?: boolean; payload?: TipItem[]; label?: string }) {
  if (!active || !payload?.length) return null
  const row = payload[0].payload
  const both = row?.income != null && row?.spend != null && payload.some(p => p.name === 'Income') // only where income is plotted
  return (
    <div className="finance-tooltip">
      <span>{label}</span>
      {payload.map((p, i) => <div key={`${p.name}-${i}`}><em><i style={{ background: p.color }} />{p.name}</em><b>{money(p.value || 0)}</b></div>)}
      {both && <div className="tip-net"><em>Saved</em><b>{(row!.income! - row!.spend! < 0 ? '−' : '') + money(Math.abs(row!.income! - row!.spend!))}</b></div>}
    </div>
  )
}

const grid = <CartesianGrid vertical={false} stroke="var(--grid)" strokeDasharray="2 6" />
/** Keep tooltips above everything (incl. the ring's centre label), off the cursor line and out of the way. */
const tipProps = { wrapperStyle: { zIndex: 50, pointerEvents: 'none' as const, outline: 'none' }, offset: 28, isAnimationActive: false }
const cursor = { stroke: 'var(--muted)', strokeWidth: 1, strokeDasharray: '4 5' }

export function CashFlowChart({ transactions }: { transactions: Transaction[] }) {
  const data = useMemo(() => monthlySummary(transactions).slice(-12).map(x => ({ ...x, month: shortMonth(x.month) })), [transactions])
  const last = data.length - 1
  return (
    <section className="card chart-card">
      <div className="card-head">
        <div><h2 className="card-title">Income vs. spending</h2><p className="card-sub">Month by month, last 12 months</p></div>
        <div className="chart-legend chip-legend"><span><i style={{ background: 'var(--income)' }} />Income</span><span><i style={{ background: 'var(--spend)' }} />Spending</span></div>
      </div>
      <div className="chart-area">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 12, right: 20, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="gIncome" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#10b981" stopOpacity={0.38} /><stop offset="100%" stopColor="#10b981" stopOpacity={0} /></linearGradient>
              <linearGradient id="gSpend" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#f97316" stopOpacity={0.34} /><stop offset="100%" stopColor="#f97316" stopOpacity={0} /></linearGradient>
            </defs>
            {grid}
            <XAxis dataKey="month" tickLine={false} axisLine={false} tick={axis} tickMargin={12} interval="preserveStartEnd" />
            <YAxis width={44} tickLine={false} axisLine={false} tick={axis} tickFormatter={kfmt} />
            <Tooltip {...tipProps} content={<FinanceTooltip />} cursor={cursor} />
            <Area className="glow-income" type="monotone" dataKey="income" name="Income" stroke="var(--income)" strokeWidth={2.5} fill="url(#gIncome)" dot={liveDot('#10b981', last)} activeDot={{ r: 5, fill: 'var(--income)', stroke: 'var(--surface)', strokeWidth: 3 }} animationDuration={1100} />
            <Area className="glow-spend" type="monotone" dataKey="spend" name="Spending" stroke="var(--spend)" strokeWidth={2.5} fill="url(#gSpend)" dot={liveDot('#f97316', last)} activeDot={{ r: 5, fill: 'var(--spend)', stroke: 'var(--surface)', strokeWidth: 3 }} animationDuration={1300} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}

export function CategoryChart({ transactions, rows = 5 }: { transactions: Transaction[]; rows?: number }) {
  const all = useMemo(() => categorySummary(transactions), [transactions])
  const total = all.reduce((s, x) => s + x.value, 0)
  const top = all.slice(0, rows)
  const rest = all.slice(rows).reduce((s, x) => s + x.value, 0)
  const items = (rest > 0 ? [...top, { name: 'Everything else', value: rest }] : top).map((x, i) => ({
    ...x, pct: total ? (x.value / total) * 100 : 0, color: x.name === 'Everything else' ? REST : PALETTE[i % PALETTE.length],
  }))
  const max = Math.max(1, ...items.map(x => x.value))
  // Recharts draws the first row innermost, so reverse to put the biggest category on the outside ring.
  // 'amount', not 'value': Recharts overwrites a 'value' field on radial sectors with the plotted percentage.
  const rings = [...items].reverse().map(x => ({ name: x.name, amount: x.value, pct: x.pct, fill: x.color }))
  return (
    <section className="card chart-card">
      <div className="card-head"><div><h2 className="card-title">Where your money goes</h2><p className="card-sub">Each ring is one category’s share of spending</p></div></div>
      <div className="ring-wrap">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart data={rings} innerRadius="46%" outerRadius="100%" startAngle={90} endAngle={-270} barSize={7} barGap={2}>
            <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
            <RadialBar dataKey="pct" cornerRadius={8} background={{ fill: 'var(--surface-2)' }} animationDuration={1200} />
            <Tooltip {...tipProps} content={<RingTip />} />
          </RadialBarChart>
        </ResponsiveContainer>
        <div className="donut-center"><span>Total spent</span><b>{money(total)}</b></div>
      </div>
      <div className="rank-list">
        {items.map(x => (
          <div className="rank-row" key={x.name}>
            <div className="rank-top"><i style={{ background: x.color }} /><span>{x.name}</span><b>{money(x.value)}</b><small>{Math.round(x.pct)}%</small></div>
            <div className="rank-bar"><i style={{ width: `${(x.value / max) * 100}%`, background: `linear-gradient(90deg, ${x.color}, color-mix(in srgb, ${x.color} 45%, transparent))` }} /></div>
          </div>
        ))}
      </div>
    </section>
  )
}

function RingTip({ active, payload }: { active?: boolean; payload?: { payload?: { name: string; amount: number; pct: number; fill: string } }[] }) {
  const p = payload?.[0]?.payload
  if (!active || !p) return null
  return <div className="finance-tooltip"><span>{p.name}</span><div><em><i style={{ background: p.fill }} />Spent</em><b>{money(p.amount)}</b></div><div><em>Share</em><b>{p.pct.toFixed(1)}%</b></div></div>
}

export function TrendChart({ transactions, forecast = false }: { transactions: Transaction[]; forecast?: boolean }) {
  const { data, last } = useMemo(() => {
    const months = monthlySummary(transactions)
    const avg = months.slice(-3).reduce((a, b) => a + b.spend, 0) / Math.max(1, months.slice(-3).length)
    const rows: { month: string; spend?: number; income?: number; projection?: number }[] = months.slice(-12).map(x => ({ ...x, month: shortMonth(x.month) }))
    const lastActual = rows.length - 1
    if (forecast && rows.length) {
      rows[lastActual] = { ...rows[lastActual], projection: rows[lastActual].spend } // start the dashed line at the last real point
      rows.push({ month: 'Next', projection: avg })
    }
    return { data: rows, last: lastActual }
  }, [transactions, forecast])
  return (
    <section className="card chart-card">
      <div className="card-head"><div><h2 className="card-title">{forecast ? 'Monthly spending and estimate' : 'Monthly spending trend'}</h2><p className="card-sub">Last 12 months</p></div></div>
      <div className="chart-area">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 12, right: 20, bottom: 0, left: 0 }}>
            <defs><linearGradient id="gTrend" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#f97316" stopOpacity={0.38} /><stop offset="100%" stopColor="#f97316" stopOpacity={0} /></linearGradient></defs>
            {grid}
            <XAxis dataKey="month" tickLine={false} axisLine={false} tick={axis} tickMargin={12} interval="preserveStartEnd" />
            <YAxis width={44} tickLine={false} axisLine={false} tick={axis} tickFormatter={kfmt} />
            <Tooltip {...tipProps} content={<FinanceTooltip />} cursor={cursor} />
            <Area className="glow-spend" type="monotone" dataKey="spend" name="Spending" stroke="var(--spend)" strokeWidth={2.5} fill="url(#gTrend)" dot={liveDot('#f97316', last)} activeDot={{ r: 5, fill: 'var(--spend)', stroke: 'var(--surface)', strokeWidth: 3 }} animationDuration={1200} />
            {forecast && <Area className="glow-violet" type="monotone" dataKey="projection" name="Estimate" stroke="#818cf8" strokeWidth={2.5} strokeDasharray="6 5" fill="none" dot={(p: { cx?: number; cy?: number; index?: number }) => (p.index === data.length - 1 && p.cx != null && p.cy != null ? <g key="est"><circle className="pulse-ring" cx={p.cx} cy={p.cy} r={7} fill="#818cf8" opacity={0.45} /><circle cx={p.cx} cy={p.cy} r={4} fill="#818cf8" stroke="var(--surface)" strokeWidth={2} /></g> : <g key={p.index} />)} activeDot={{ r: 5, fill: '#818cf8', stroke: 'var(--surface)', strokeWidth: 3 }} />}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
