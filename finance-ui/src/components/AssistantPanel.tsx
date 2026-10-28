import { useState } from 'react'
import { Bot, Send, UserRound } from 'lucide-react'
import type { Transaction } from '../types'
import { categorySummary, money, recurringPayments } from '../lib/finance'
type Message={who:'you'|'assistant';text:string}
const initial:Message[]=[{who:'assistant',text:'Ask me about spending, savings, recurring charges, or how your data is handled. I’ll answer from this statement on your device.'}]
function answer(question:string,tx:Transaction[]){const q=question.toLowerCase(),spend=tx.filter(t=>t.type==='debit').reduce((a,b)=>a+b.amount,0),income=tx.filter(t=>t.type==='credit').reduce((a,b)=>a+b.amount,0),categories=categorySummary(tx),rec=recurringPayments(tx);if(q.includes('subscription')||q.includes('recurring'))return `I found ${rec.length} possible recurring merchants from repeated charges. ${rec.slice(0,3).map(x=>`${x.merchant} (${money(x.amount)} average)`).join(', ')||'No strong recurring pattern yet'}. Please review the transactions to confirm.`;if(q.includes('grocer'))return `Groceries total ${money(categories.find(c=>c.name==='Groceries')?.value||0)} in the loaded statement.`;if(q.includes('budget'))return 'Open Budgets to set category limits. The bar compares spending in the latest statement month with each limit.';if(q.includes('unusual')||q.includes('duplicate'))return 'Open Anomalies to review repeated charges and transactions much larger than the average for their category. A flag is only a review prompt.';if(q.includes('forecast')||q.includes('next month'))return `Average monthly spending in the latest few months points to about ${money(spend/Math.max(1,new Set(tx.map(t=>t.date.slice(0,7))).size))} per month. Open Forecast for the trend; it is an estimate, not a promise.`;if(q.includes('savings')||q.includes('rate'))return `Across this statement, income is ${money(income)} and spending is ${money(spend)}. Net savings are ${money(income-spend)}${income?` (${((income-spend)/income*100).toFixed(1)}% of income)`:''}.`;if(q.includes('data')||q.includes('stored')||q.includes('private'))return 'This demo processes the CSV in your browser and keeps the imported rows in this browser’s local storage. It does not send your statement to a server.';return `Based on the loaded statement, spending is ${money(spend)} and received income is ${money(income)}. You can ask about groceries, savings, recurring charges, budgets, anomalies, or forecasts.`}
export default function AssistantPanel({ transactions }: { transactions: Transaction[] }) {
  const [messages, setMessages] = useState<Message[]>(initial)
  const [value, setValue] = useState('')
  function send(text = value) {
    const q = text.trim()
    if (!q) return
    setMessages(v => [...v, { who: 'you', text: q }, { who: 'assistant', text: answer(q, transactions) }])
    setValue('')
  }
  return (
    <section className="card chat">
      <div className="messages" aria-live="polite">
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.who === 'you' ? 'from-user' : ''}`}>
            <span className="msg-avatar">{m.who === 'assistant' ? <Bot size={18} /> : <UserRound size={18} />}</span>
            <p>{m.text}</p>
          </div>
        ))}
      </div>
      <div className="suggestions">
        {['What is my savings rate?', 'Any subscriptions?', 'How is my data stored?'].map(q => <button key={q} onClick={() => send(q)}>{q}</button>)}
      </div>
      <form className="chat-input" onSubmit={e => { e.preventDefault(); send() }}>
        <input value={value} onChange={e => setValue(e.target.value)} placeholder="Ask a question about your statement…" aria-label="Ask the finance assistant" />
        <button type="submit" aria-label="Send question"><Send size={20} /></button>
      </form>
      <p className="chat-foot">Answers are calculated on your device from the loaded statement.</p>
    </section>
  )
}
