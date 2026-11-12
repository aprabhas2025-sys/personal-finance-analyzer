import { useState } from 'react'
import { Bot, Send, Sparkles, UserRound } from 'lucide-react'
import { marked } from 'marked'
import type { Transaction } from '../types'
import { categorySummary, money, recurringPayments } from '../lib/finance'

marked.use({
  breaks: true,
  gfm: true,
})

function renderMarkdown(content: string): string {
  try {
    return marked.parse(content) as string
  } catch {
    return content
  }
}

interface FinanceAiConfig {
  groqKey?: string
  groqModel?: string
  geminiKey?: string
  geminiModel?: string
}

declare global {
  interface Window {
    __FINANCE_AI__?: FinanceAiConfig
  }
}

type Message = {
  who: 'you' | 'assistant'
  text: string
  provider?: 'groq' | 'gemini' | 'rules'
}

const initial: Message[] = [
  {
    who: 'assistant',
    text: 'Ask me about spending, savings, recurring charges, or how your data is handled. I’ll answer from this statement using AI.',
    provider: 'rules',
  },
]

function answerRule(question: string, tx: Transaction[]): string {
  const q = question.toLowerCase()
  const spend = tx.filter(t => t.type === 'debit').reduce((a, b) => a + b.amount, 0)
  const income = tx.filter(t => t.type === 'credit').reduce((a, b) => a + b.amount, 0)
  const categories = categorySummary(tx)
  const rec = recurringPayments(tx)

  if (q.includes('subscription') || q.includes('recurring')) {
    return `I found **${rec.length} possible recurring merchants** from repeated charges:\n\n` +
      (rec.slice(0, 4).map(x => `- **${x.merchant}**: ~${money(x.amount)} average`).join('\n') || '- No strong recurring pattern yet') +
      '\n\nPlease review the transactions to confirm.'
  }
  if (q.includes('grocer')) {
    return `Groceries total **${money(categories.find(c => c.name === 'Groceries')?.value || 0)}** in the loaded statement.`
  }
  if (q.includes('budget')) {
    return 'Open **Budgets** to set category limits. The bar compares spending in the latest statement month with each limit.'
  }
  if (q.includes('unusual') || q.includes('duplicate')) {
    return 'Open **Anomalies** to review repeated charges and transactions much larger than the average for their category. A flag is only a review prompt.'
  }
  if (q.includes('forecast') || q.includes('next month')) {
    return `Average monthly spending in the latest few months points to about **${money(
      spend / Math.max(1, new Set(tx.map(t => t.date.slice(0, 7))).size)
    )}** per month. Open **Forecast** for the trend; it is an estimate, not a promise.`
  }
  if (q.includes('savings') || q.includes('rate')) {
    return `Across this statement:\n- **Income:** ${money(income)}\n- **Spending:** ${money(spend)}\n- **Net Savings:** ${money(income - spend)}${
      income ? ` (${(((income - spend) / income) * 100).toFixed(1)}% of income)` : ''
    }.`
  }
  if (q.includes('data') || q.includes('stored') || q.includes('private')) {
    return 'This demo processes the CSV in your browser and keeps the imported rows in this browser’s local storage. It does not send your raw statement to a server.'
  }
  return `Based on the loaded statement, total spending is **${money(spend)}** and total received income is **${money(income)}**.\n\nYou can ask about groceries, savings rate, recurring subscriptions, budgets, anomalies, or forecasts.`
}

function buildSummary(tx: Transaction[]): string {
  if (!tx.length) return 'No statement transactions loaded yet.'
  const spend = tx.filter(t => t.type === 'debit').reduce((a, b) => a + b.amount, 0)
  const income = tx.filter(t => t.type === 'credit').reduce((a, b) => a + b.amount, 0)
  const categories = categorySummary(tx)
  const rec = recurringPayments(tx)
  const sortedDates = tx.map(t => t.date).sort()
  const start = sortedDates[0]
  const end = sortedDates[sortedDates.length - 1]
  const topCats = categories.slice(0, 6).map(c => `${c.name}: ${money(c.value)}`).join(', ')
  const recList = rec.slice(0, 6).map(r => `${r.merchant} (~${money(r.amount)})`).join(', ')

  return `Statement Summary:
- Period: ${start} to ${end}
- Total Spend (debits): ${money(spend)} across ${tx.filter(t => t.type === 'debit').length} transactions
- Total Income (credits): ${money(income)} across ${tx.filter(t => t.type === 'credit').length} transactions
- Net Savings: ${money(income - spend)}${income ? ` (${(((income - spend) / income) * 100).toFixed(1)}% savings rate)` : ''}
- Top Categories: ${topCats}
- Recurring Subscriptions Detected: ${recList || 'None detected'}
`
}

async function fetchGroq(apiKey: string, model: string, prompt: string, summary: string, history: Message[]): Promise<string> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 12000)
  try {
    const res = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: model || 'openai/gpt-oss-120b',
        messages: [
          {
            role: 'system',
            content: `You are an intelligent, friendly personal finance assistant analyzing this user's bank statement.
Amounts are in Indian Rupees (₹).
Here is the aggregate statement data:
${summary}

Formatting instructions:
- Output clean, beautifully formatted Markdown.
- Use bold text for key figures, metrics, and merchant names.
- When listing items, features, or tasks, use clear bullet points with concise bold headers.
- If presenting comparison data, use a clean Markdown table with headers.
- Keep answers readable, structured, and pleasant to read. Avoid messy run-on pipe characters.`,
          },
          ...history.slice(-6).map(m => ({
            role: m.who === 'you' ? 'user' : 'assistant',
            content: m.text,
          })),
          { role: 'user', content: prompt },
        ],
        max_tokens: 650,
        temperature: 0.3,
      }),
      signal: controller.signal,
    })
    clearTimeout(timeoutId)
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err?.error?.message || `Groq error ${res.status}`)
    }
    const data = await res.json()
    const text = data.choices?.[0]?.message?.content?.trim()
    if (!text) throw new Error('Empty response from Groq')
    return text
  } finally {
    clearTimeout(timeoutId)
  }
}

async function fetchGemini(apiKey: string, model: string, prompt: string, summary: string, history: Message[]): Promise<string> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 12000)
  try {
    const modelName = model || 'gemini-2.5-flash'
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${modelName}:generateContent?key=${apiKey}`
    const contents = [
      ...history.slice(-6).map(m => ({
        role: m.who === 'you' ? 'user' : 'model',
        parts: [{ text: m.text }],
      })),
      { role: 'user', parts: [{ text: prompt }] },
    ]
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        system_instruction: {
          parts: [
            {
              text: `You are an intelligent, friendly personal finance assistant analyzing this user's bank statement. Amounts are in Indian Rupees (₹).\nStatement data:\n${summary}\nFormat all responses with clean Markdown, bold figures, bullet points, and clean tables where appropriate.`,
            },
          ],
        },
        contents,
        generationConfig: { maxOutputTokens: 650, temperature: 0.3 },
      }),
      signal: controller.signal,
    })
    clearTimeout(timeoutId)
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err?.error?.message || `Gemini error ${res.status}`)
    }
    const data = await res.json()
    const text = data.candidates?.[0]?.content?.parts?.[0]?.text?.trim()
    if (!text) throw new Error('Empty response from Gemini')
    return text
  } finally {
    clearTimeout(timeoutId)
  }
}

export default function AssistantPanel({ transactions }: { transactions: Transaction[] }) {
  const [messages, setMessages] = useState<Message[]>(initial)
  const [value, setValue] = useState('')
  const [loading, setLoading] = useState(false)

  const aiConfig = typeof window !== 'undefined' ? window.__FINANCE_AI__ : undefined
  const hasGroq = Boolean(aiConfig?.groqKey)
  const hasGemini = Boolean(aiConfig?.geminiKey)

  async function send(text = value) {
    const q = text.trim()
    if (!q || loading) return
    setValue('')
    setMessages(v => [...v, { who: 'you', text: q }])
    setLoading(true)

    const summary = buildSummary(transactions)
    let reply = ''
    let provider: 'groq' | 'gemini' | 'rules' = 'rules'

    if (hasGroq && aiConfig?.groqKey) {
      try {
        reply = await fetchGroq(aiConfig.groqKey, aiConfig.groqModel || 'openai/gpt-oss-120b', q, summary, messages)
        provider = 'groq'
      } catch (err) {
        console.warn('Groq failed, attempting Gemini backup:', err)
      }
    }

    if (!reply && hasGemini && aiConfig?.geminiKey) {
      try {
        reply = await fetchGemini(aiConfig.geminiKey, aiConfig.geminiModel || 'gemini-2.5-flash', q, summary, messages)
        provider = 'gemini'
      } catch (err) {
        console.warn('Gemini failed, falling back to local rules:', err)
      }
    }

    if (!reply) {
      reply = answerRule(q, transactions)
      provider = 'rules'
    }

    setMessages(v => [...v, { who: 'assistant', text: reply, provider }])
    setLoading(false)
  }

  return (
    <section className="card chat">
      <div className="messages" aria-live="polite">
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.who === 'you' ? 'from-user' : ''}`}>
            <span className="msg-avatar">{m.who === 'assistant' ? <Bot size={18} /> : <UserRound size={18} />}</span>
            <div className="msg-content">
              {m.who === 'assistant' && m.provider && (
                <span className={`msg-tag ${m.provider}`}>
                  {m.provider === 'groq' ? '⚡ Groq AI' : m.provider === 'gemini' ? '✨ Gemini Backup' : 'Rules'}
                </span>
              )}
              <div
                className="msg-bubble markdown-body"
                dangerouslySetInnerHTML={{ __html: renderMarkdown(m.text) }}
              />
            </div>
          </div>
        ))}
        {loading && (
          <div className="msg">
            <span className="msg-avatar"><Bot size={18} /></span>
            <div className="msg-content">
              <span className="msg-tag">Thinking</span>
              <div className="msg-bubble">
                <span className="typing-dots"><span /><span /><span /></span>
              </div>
            </div>
          </div>
        )}
      </div>
      <div className="suggestions">
        {['What is my savings rate?', 'Any subscriptions?', 'How is my data stored?'].map(q => (
          <button key={q} onClick={() => void send(q)} disabled={loading}>{q}</button>
        ))}
      </div>
      <form className="chat-input" onSubmit={e => { e.preventDefault(); void send() }}>
        <input
          value={value}
          onChange={e => setValue(e.target.value)}
          placeholder="Ask a question about your statement…"
          aria-label="Ask the finance assistant"
          disabled={loading}
        />
        <button type="submit" aria-label="Send question" disabled={loading}><Send size={20} /></button>
      </form>
      <p className="chat-foot">
        {hasGroq ? (
          <>
            <Sparkles size={13} style={{ display: 'inline', verticalAlign: '-2px', marginRight: 4, color: 'var(--accent)' }} />
            Powered by Groq ({aiConfig?.groqModel || 'openai/gpt-oss-120b'}){hasGemini ? ' with Gemini backup' : ''} · Private aggregate summaries only
          </>
        ) : hasGemini ? (
          <>
            <Sparkles size={13} style={{ display: 'inline', verticalAlign: '-2px', marginRight: 4, color: '#60a5fa' }} />
            Powered by Gemini ({aiConfig?.geminiModel || 'gemini-2.5-flash'}) · Private aggregate summaries only
          </>
        ) : (
          'Answers are calculated on your device from the loaded statement.'
        )}
      </p>
    </section>
  )
}
