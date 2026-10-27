import { useMemo, useState } from 'react'
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis } from 'recharts'
import { ChevronDown, CircleHelp } from 'lucide-react'

const categories = [
  { name: 'Hospital visits', value: 40, color: '#84CC16' },
  { name: 'Medication', value: 35, color: '#2DD4BF' },
  { name: 'Lab tests', value: 25, color: '#FACC15' },
]
const series = {
  Monthly: [{ month: 'Jan', spending: 7.1, cover: 5.3 }, { month: 'Feb', spending: 8.2, cover: 6.0 }, { month: 'Mar', spending: 7.7, cover: 6.7 }, { month: 'Apr', spending: 10.5, cover: 8.2 }, { month: 'May', spending: 9.4, cover: 7.6 }, { month: 'Jun', spending: 11.2, cover: 9.2 }],
  Weekly: [{ month: 'W1', spending: 2.8, cover: 1.7 }, { month: 'W2', spending: 4.2, cover: 2.9 }, { month: 'W3', spending: 3.6, cover: 2.7 }, { month: 'W4', spending: 5.0, cover: 3.6 }],
  Yearly: [{ month: '2022', spending: 6.1, cover: 4.5 }, { month: '2023', spending: 7.6, cover: 5.8 }, { month: '2024', spending: 8.5, cover: 6.3 }, { month: '2025', spending: 10.5, cover: 8.2 }],
}
type Range = keyof typeof series
const moneyTip = (value: number) => `$${(value * 1000).toLocaleString()}`
function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: { dataKey?: string; value?: number }[]; label?: string }) {
  if (!active || !payload?.length) return null
  return <div className="chart-tooltip"><span>{label}</span>{payload.map(row => <div key={row.dataKey} className={row.dataKey === 'spending' ? 'tooltip-mint' : 'tooltip-yellow'}><i/>{row.dataKey === 'spending' ? 'Care spending' : 'Insurance'} <b>{moneyTip(row.value ?? 0)}</b></div>)}</div>
}
export default function SmartHealthFinance() {
  const [range, setRange] = useState<Range>('Monthly')
  const data = useMemo(() => series[range], [range])
  return <section className="panel smart-card">
    <div className="panel-heading"><div><div className="eyebrow">Smart health finance <CircleHelp size={13}/></div><div className="chart-title">Your health, in balance</div></div><label className="select-wrap"><select value={range} onChange={e => setRange(e.target.value as Range)} aria-label="Chart period"><option>Monthly</option><option>Weekly</option><option>Yearly</option></select><ChevronDown size={13}/></label></div>
    <div className="donut-row">
      <div className="donut-wrap"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={categories} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius="68%" outerRadius="91%" paddingAngle={5} stroke="none" animationDuration={850}>{categories.map(item => <Cell key={item.name} fill={item.color}/>)}</Pie><Tooltip formatter={(value) => [`${value}%`, 'Share']} contentStyle={{ background: '#171a1d', border: '1px solid #292d31', borderRadius: 10, color: '#f3f4f6', fontSize: 12 }}/></PieChart></ResponsiveContainer><div className="donut-center"><span>Care mix</span><b>100%</b></div></div>
      <div className="legend-list">{categories.map(item => <div className="legend-item" key={item.name}><i style={{ background: item.color }}/><span>{item.name}</span><b>{item.value}%</b></div>)}</div>
    </div>
    <div className="chart-divider" />
    <div className="line-legend"><span><i className="legend-mint"/> Care spending</span><span><i className="legend-yellow"/> Insurance</span><b>$10,500 <em>/</em> $8,200</b></div>
    <div className="line-chart-wrap"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data} margin={{ top: 10, right: 6, bottom: 0, left: -24 }}>
      <defs><linearGradient id="mintFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#2DD4BF" stopOpacity={0.2}/><stop offset="100%" stopColor="#2DD4BF" stopOpacity={0}/></linearGradient><linearGradient id="yellowFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#FACC15" stopOpacity={0.11}/><stop offset="100%" stopColor="#FACC15" stopOpacity={0}/></linearGradient></defs>
      <CartesianGrid vertical={false} stroke="#262a2d" strokeDasharray="3 5"/><XAxis dataKey="month" tickLine={false} axisLine={false} tick={{ fill: '#727a80', fontSize: 10 }}/><Tooltip content={<ChartTooltip/>}/>
      <Area type="monotone" dataKey="spending" stroke="#2DD4BF" strokeWidth={2.4} fill="url(#mintFill)" dot={false} activeDot={{ r: 4, fill: '#2DD4BF', stroke: '#0c1716', strokeWidth: 3 }} animationDuration={900}/>
      <Area type="monotone" dataKey="cover" stroke="#FACC15" strokeWidth={2.1} fill="url(#yellowFill)" dot={false} activeDot={{ r: 4, fill: '#FACC15', stroke: '#19170d', strokeWidth: 3 }} animationDuration={1000}/>
    </AreaChart></ResponsiveContainer></div>
  </section>
}
