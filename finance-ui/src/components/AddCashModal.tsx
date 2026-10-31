import { useEffect, useMemo, useRef, useState } from 'react'
import { Plus, X } from 'lucide-react'
import { CATEGORIES, type Category, type Transaction, type TxType } from '../types'
import { categorize } from '../lib/finance'

export type CashEntry = Pick<Transaction, 'date' | 'description' | 'amount' | 'type' | 'category'>
type Props = { onAdd: (entry: CashEntry) => void; onClose: () => void }

const INCOME: Category[] = ['Salary', 'Other Income', 'Transfers', 'Other']
const today = () => new Date().toLocaleDateString('en-CA') // YYYY-MM-DD in the viewer's own time zone

export default function AddCashModal({ onAdd, onClose }: Props) {
  const [type, setType] = useState<TxType>('debit')
  const [amount, setAmount] = useState('')
  const [description, setDescription] = useState('')
  const [date, setDate] = useState(today())
  const [category, setCategory] = useState<Category>('Other')
  const [touched, setTouched] = useState(false) // once the person picks a category, stop auto-suggesting
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(0)
  const amountRef = useRef<HTMLInputElement>(null)

  const options = useMemo<readonly Category[]>(() => (type === 'credit' ? INCOME : CATEGORIES.filter(c => c !== 'Salary' && c !== 'Other Income')), [type])
  useEffect(() => { amountRef.current?.focus() }, [])
  useEffect(() => { const k = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }; window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k) }, [onClose])
  useEffect(() => {
    if (touched) { if (!options.includes(category)) setCategory('Other'); return }
    setCategory(description.trim() ? categorize(description, type).category : 'Other')
  }, [description, type, touched, options])

  function save(another: boolean) {
    const value = Math.round(Number(amount) * 100) / 100
    if (!amount.trim() || !Number.isFinite(value) || value <= 0) return setError('Enter an amount greater than zero.')
    if (!description.trim()) return setError('Add a short description, for example "Auto fare" or "Tea stall".')
    if (!date) return setError('Pick the date of this transaction.')
    if (date > today()) return setError('The date can’t be in the future.')
    onAdd({ date, description: description.trim(), amount: value, type, category })
    if (another) { setAmount(''); setDescription(''); setTouched(false); setError(''); setSaved(n => n + 1); amountRef.current?.focus() } else onClose()
  }

  return (
    <div className="modal-scrim" onMouseDown={e => { if (e.target === e.currentTarget) onClose() }}>
      <form noValidate className="modal card" role="dialog" aria-modal="true" aria-labelledby="cash-title" onSubmit={e => { e.preventDefault(); save(false) }}>
        <div className="modal-head">
          <div><h2 id="cash-title" className="card-title">Add a cash transaction</h2><p className="card-sub">For money that never shows up on a bank statement.</p></div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Close"><X size={16} /></button>
        </div>

        <div className="segmented segmented-full" role="tablist" aria-label="Type">
          <button type="button" role="tab" aria-selected={type === 'debit'} onClick={() => setType('debit')}>Spent</button>
          <button type="button" role="tab" aria-selected={type === 'credit'} onClick={() => setType('credit')}>Received</button>
        </div>

        <div className="field-grid">
          <label className="field"><span>Amount (₹)</span>
            <input ref={amountRef} type="number" inputMode="decimal" min="0.01" step="0.01" placeholder="0.00" value={amount} onChange={e => { setAmount(e.target.value); setError('') }} />
          </label>
          <label className="field"><span>Date</span>
            <input type="date" max={today()} value={date} onChange={e => { setDate(e.target.value); setError('') }} />
          </label>
        </div>
        <label className="field"><span>Description</span>
          <input type="text" maxLength={80} placeholder={type === 'debit' ? 'e.g. Auto fare, vegetables, tea' : 'e.g. Cash from parents, tuition fee'} value={description} onChange={e => { setDescription(e.target.value); setError('') }} />
        </label>
        <label className="field"><span>Category {!touched && description.trim() ? <em>(suggested)</em> : null}</span>
          <select value={category} onChange={e => { setCategory(e.target.value as Category); setTouched(true) }}>{options.map(c => <option key={c}>{c}</option>)}</select>
        </label>

        {error && <p className="form-error" role="alert">{error}</p>}
        {saved > 0 && !error && <p className="form-ok">{saved} added. You can add another.</p>}

        <div className="modal-actions">
          <button type="button" className="btn" onClick={onClose}>Cancel</button>
          <button type="button" className="btn" onClick={() => save(true)}><Plus size={15} />Save &amp; add another</button>
          <button type="submit" className="btn btn-primary">Add transaction</button>
        </div>
      </form>
    </div>
  )
}
