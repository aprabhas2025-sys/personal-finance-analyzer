import { CATEGORIES, type Category, type MonthlyPoint, type Period, type Transaction } from '../types'

const key = (value: string) => value.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()
function detectDelimiter(text: string): string {
  const lines = text.split(/\r\n|\n|\r/).filter(l => l.trim()).slice(0, 15)
  let best = ',', bestScore = 0
  for (const d of [',', ';', '\t', '|']) {
    const score = lines.reduce((n, l) => n + l.split(d).length - 1, 0)
    if (score > bestScore) { best = d; bestScore = score }
  }
  return best
}
export function parseCsvRows(text: string, delimiter = ','): string[][] {
  const rows: string[][] = []; let row: string[] = []; let cell = ''; let quoted = false
  for (let i=0;i<text.length;i++) { const ch=text[i]
    if(ch==='"' && quoted && text[i+1]==='"'){cell+='"';i++}
    else if(ch==='"') quoted=!quoted
    else if(ch===delimiter && !quoted){row.push(cell);cell=''}
    else if((ch==='\n'||ch==='\r')&&!quoted){if(ch==='\r'&&text[i+1]==='\n')i++;row.push(cell);if(row.some(v=>v.trim()))rows.push(row);row=[];cell=''}
    else cell+=ch
  }
  if(cell.length||row.length){row.push(cell);if(row.some(v=>v.trim()))rows.push(row)}
  return rows
}
function parseDate(raw: string): string | null {
  const s=raw.trim();let m=s.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})/)
  if(m)return `${m[1]}-${m[2].padStart(2,'0')}-${m[3].padStart(2,'0')}`
  m=s.match(/^(\d{1,2})[/-](\d{1,2})[/-](\d{4})/)
  if(m)return `${m[3]}-${m[2].padStart(2,'0')}-${m[1].padStart(2,'0')}`
  m=s.match(/^(\d{1,2})[/-](\d{1,2})[/-](\d{2})(?!\d)/)
  if(m)return `20${m[3]}-${m[2].padStart(2,'0')}-${m[1].padStart(2,'0')}`
  const months=['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']
  m=s.match(/^(\d{1,2})[ /-]+([A-Za-z]{3})[A-Za-z]*[ ,/-]+(\d{2}|\d{4})(?!\d)/)
  if(m){const mi=months.indexOf(m[2].toLowerCase());if(mi>=0)return `${m[3].length===2?'20'+m[3]:m[3]}-${String(mi+1).padStart(2,'0')}-${m[1].padStart(2,'0')}`}
  const d=new Date(s);return Number.isNaN(d.getTime())?null:d.toISOString().slice(0,10)
}
function parseAmount(raw: string): number {
  const s=raw.trim();if(!s)return 0
  const neg=/^\(.*\)$/.test(s)||/^\s*-/.test(s)||/\bdr\b/i.test(s)
  const n=Number(s.replace(/[^\d.]/g,''));return Number.isFinite(n)?(neg?-n:n):0
}
export function categorize(description: string, type: 'debit'|'credit'): { category: Category; confidence: number } {
  const d=key(description)
  if(type==='credit')return /salary|payroll|stipend/.test(d)?{category:'Salary',confidence:.94}:{category:'Other Income',confidence:.68}
  const rules: [RegExp,Category][]=[
    [/zomato|swiggy|foodpanda|ubereats|food delivery/,'Food Delivery'],[/restaurant|cafe|dining|pizza|dominos|burger|hotel dining/,'Dining Out'],
    [/grocery|supermarket|bigbasket|blinkit|zepto|dmart|reliance fresh/,'Groceries'],[/uber|ola|rapido|metro|bus|train|transport|irctc/,'Transport'],
    [/petrol|fuel|hpcl|iocl|bpcl|shell/,'Fuel'],[/netflix|spotify|prime video|hotstar|subscription|membership/,'Subscriptions'],
    [/rent|landlord|house rent/,'Rent'],[/emi|loan|mortgage/,'EMI'],[/electric|water bill|gas bill|broadband|mobile recharge|utility/,'Utilities'],
    [/pharmacy|hospital|clinic|doctor|medical|health/,'Health'],[/flight|airline|hotel|booking|travel/,'Travel'],[/school|college|course|education/,'Education'],
    [/transfer|neft|imps|self transfer|upi transfer/,'Transfers'],[/amazon|flipkart|myntra|shopping|store|marketplace/,'Shopping'],[/movie|cinema|game|concert/,'Entertainment'],
  ]
  const match=rules.find(([regex])=>regex.test(d));return match?{category:match[1],confidence:.82}:{category:'Other',confidence:.46}
}
type Cols = { dateIx:number; descIx:number; debitIx:number; creditIx:number; amountIx:number; typeIx:number; catIx:number }
function findCol(headers: string[], exact: string[], patterns: RegExp[], skip: number[] = []): number {
  const byName = headers.findIndex((h,i) => !skip.includes(i) && exact.includes(h))
  return byName >= 0 ? byName : headers.findIndex((h,i) => !skip.includes(i) && patterns.some(p => p.test(h)))
}
function detectColumns(row: string[]): Cols | null {
  const h = row.map(key)
  const dateIx = findCol(h, ['date','txn date','transaction date','tran date','posting date','value date'], [/\bdate\b/, /\bdt\b/])
  const descIx = findCol(h, ['description','narration','particulars','remarks','details','merchant'], [/descri|narrat|particular|remark|detail|merchant|payee/], [dateIx])
  const debitIx = findCol(h, ['debit','withdrawal','withdrawal amount','dr'], [/withdraw|^debit|^dr (amt|amount)|paid out|money out/], [dateIx, descIx])
  const creditIx = findCol(h, ['credit','deposit','deposit amount','cr'], [/deposit|^credit|^cr (amt|amount)|paid in|money in/], [dateIx, descIx, debitIx])
  const amountIx = findCol(h, ['amount','txn amount','transaction amount'], [/amount|\bamt\b/], [dateIx, descIx, debitIx, creditIx].concat(h.map((x,i)=>/balance|bal\b/.test(x)?i:-1).filter(i=>i>=0)))
  const typeIx = findCol(h, ['type','dr cr','cr dr','transaction type','txn type'], [/^(dr cr|cr dr|type)$/, /txn type|transaction type/], [dateIx, descIx, amountIx])
  const catIx = findCol(h, ['category'], [])
  if (dateIx < 0 || descIx < 0 || (debitIx < 0 && creditIx < 0 && amountIx < 0)) return null
  return { dateIx, descIx, debitIx, creditIx, amountIx, typeIx, catIx }
}
export function parseBankCsv(input: string): Transaction[] {
  const text = input.replace(/^\uFEFF/, '')
  const rows = parseCsvRows(text, detectDelimiter(text)); if (rows.length < 2) throw new Error('This CSV has no transaction rows.')
  // Bank exports often have account info above the real header, so look for the header row in the first 40 lines.
  let headerAt = -1, cols: Cols | null = null
  for (let i = 0; i < Math.min(rows.length - 1, 40); i++) { cols = detectColumns(rows[i]); if (cols) { headerAt = i; break } }
  if (!cols || headerAt < 0) throw new Error(`Could not identify the date, description, and debit/credit or amount columns. Columns found: ${rows[0].map(c => c.trim()).filter(Boolean).slice(0, 8).join(', ') || 'none'}.`)
  const { dateIx, descIx, debitIx, creditIx, amountIx, typeIx, catIx } = cols
  return rows.slice(headerAt + 1).flatMap((r,i)=>{const date=parseDate(r[dateIx]||'');const description=(r[descIx]||'').trim();let amount=0;let type:'debit'|'credit'='debit'
    if(debitIx>=0||creditIx>=0){const debit=parseAmount(r[debitIx]||'');const credit=parseAmount(r[creditIx]||'');if(Math.abs(debit)>0){amount=Math.abs(debit);type='debit'}else if(Math.abs(credit)>0){amount=Math.abs(credit);type='credit'}}
    else {const raw=parseAmount(r[amountIx]||'');amount=Math.abs(raw);const t=(r[typeIx]||'').toLowerCase();type=t?(/^(dr|d|debit|withdrawal)/.test(t)?'debit':'credit'):raw<0?'debit':'credit'}
    if(!date||!description||amount<=0)return []
    const guessed=categorize(description,type);const provided=(r[catIx]||'').trim();const category=(CATEGORIES as readonly string[]).includes(provided)?provided as Category:guessed.category
    return [{id:`${date}-${i}-${description.slice(0,10)}`,date,description,amount,type,category,confidence:provided?1:guessed.confidence,status:'Cleared' as const}]
  }).sort((a,b)=>a.date.localeCompare(b.date))
}
export function money(amount:number, decimals=0){return `₹${amount.toLocaleString('en-IN',{minimumFractionDigits:decimals,maximumFractionDigits:decimals})}`}
export function getPeriodStart(transactions:Transaction[], period:Period): string | null {
  if(period==='All data'||!transactions.length)return null
  const latest=new Date(`${transactions[transactions.length-1].date}T12:00:00`);const start=new Date(latest)
  if(period==='30 days')start.setDate(start.getDate()-30);else start.setMonth(start.getMonth()-(period==='3 months'?3:6))
  return start.toISOString().slice(0,10)
}
export function monthlySummary(transactions:Transaction[]):MonthlyPoint[]{
  const map=new Map<string,MonthlyPoint>();for(const t of transactions){const month=t.date.slice(0,7);const p=map.get(month)||{month,spend:0,income:0,net:0};if(t.type==='debit')p.spend+=t.amount;else p.income+=t.amount;p.net=p.income-p.spend;map.set(month,p)}return [...map.values()].sort((a,b)=>a.month.localeCompare(b.month))
}
export function categorySummary(transactions:Transaction[]){const map=new Map<string,number>();transactions.filter(t=>t.type==='debit').forEach(t=>map.set(t.category,(map.get(t.category)||0)+t.amount));return [...map].map(([name,value])=>({name,value})).sort((a,b)=>b.value-a.value)}
export function findAnomalies(transactions:Transaction[]){
  const seen=new Set<string>();const categoryAvg=new Map<string,number>();const totals=new Map<string,{sum:number;count:number}>();transactions.filter(t=>t.type==='debit').forEach(t=>{const x=totals.get(t.category)||{sum:0,count:0};x.sum+=t.amount;x.count++;totals.set(t.category,x)});totals.forEach((x,k)=>categoryAvg.set(k,x.sum/x.count))
  return transactions.filter(t=>t.type==='debit').flatMap(t=>{const fingerprint=`${t.date}|${key(t.description)}|${t.amount.toFixed(2)}`;const duplicate=seen.has(fingerprint);seen.add(fingerprint);const unusual=t.amount>(categoryAvg.get(t.category)||Infinity)*3;return duplicate||unusual?[{...t,reason:duplicate?'Possible duplicate charge':'Amount is far above the category average'}]:[]})
}
export function recurringPayments(transactions:Transaction[]){const groups=new Map<string,Transaction[]>();for(const t of transactions.filter(x=>x.type==='debit')){const merchant=key(t.description).split(' ').filter(Boolean).slice(0,3).join(' ');if(!merchant)continue;groups.set(merchant,[...(groups.get(merchant)||[]),t])}return [...groups].filter(([,v])=>v.length>=3).map(([merchant,items])=>({merchant,amount:items.reduce((a,b)=>a+b.amount,0)/items.length,count:items.length,last:items[items.length-1].date})).sort((a,b)=>b.amount-a.amount)}
export function shortMonth(value:string){return new Date(`${value}-15T12:00:00`).toLocaleDateString('en-IN',{month:'short',year:'2-digit'})}


