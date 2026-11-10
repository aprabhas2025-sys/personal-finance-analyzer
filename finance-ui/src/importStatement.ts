import * as XLSX from 'xlsx'
import { parseBankCsv } from './lib/finance'
import type { Transaction } from './types'

const HEADER_WORDS = new Set([
  'date', 'txn date', 'transaction date', 'value date', 'posting date', 'tran date',
  'description', 'narration', 'particulars', 'remarks', 'details', 'transaction remarks',
  'transaction details', 'merchant', 'debit', 'withdrawal', 'withdrawal amt',
  'withdrawal amount', 'debit amount', 'money out', 'credit', 'deposit', 'deposit amt',
  'deposit amount', 'credit amount', 'money in', 'amount', 'txn amount',
  'transaction amount', 'type', 'dr/cr', 'cr/dr', 'transaction type', 'txn type', 'category',
])

const normalize = (value: unknown) => String(value ?? '').trim().toLowerCase().replace(/\s+/g, ' ')

function findHeaderRow(rows: unknown[][]): number {
  let best = -1
  let score = 0
  for (let i = 0; i < Math.min(rows.length, 30); i++) {
    const candidate = rows[i].map(normalize).filter(Boolean)
    const matches = candidate.filter(value => HEADER_WORDS.has(value)).length
    if (matches > score) { score = matches; best = i }
  }
  if (best < 0 || score < 2) throw new Error('Could not identify a transaction table. Include columns such as Date, Description, and Amount (or Debit and Credit).')
  return best
}

function rowsToCsv(rows: unknown[][]): string {
  const csvCell = (value: unknown) => {
    const text = value instanceof Date
      ? (Number.isNaN(value.getTime()) ? '' : value.toISOString().slice(0, 10))
      : String(value ?? '')
    return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
  }
  return rows.map(row => row.map(csvCell).join(',')).join('\n')
}

function jsonToRows(value: unknown): unknown[][] {
  const root = value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : null
  const records = Array.isArray(value) ? value : root
    ? (['transactions', 'data', 'rows'].map(key => root[key]).find(Array.isArray) as unknown[] | undefined) ?? Object.values(root)
    : []
  const objects = records.filter(item => item && typeof item === 'object' && !Array.isArray(item)) as Record<string, unknown>[]
  if (!objects.length) throw new Error('JSON must contain an array of transaction records.')
  const headers = [...new Set(objects.flatMap(record => Object.keys(record)))]
  return [headers, ...objects.map(record => headers.map(header => record[header] ?? ''))]
}

/** Parse supported tabular transaction files using the same column mapping and analysis as CSV imports. */
export async function parseStatementFile(file: File): Promise<Transaction[]> {
  const extension = file.name.split('.').pop()?.toLowerCase()
  let rows: unknown[][]

  if (extension === 'xlsx' || extension === 'xls') {
    const workbook = XLSX.read(await file.arrayBuffer(), { type: 'array', cellDates: true })
    const candidates = workbook.SheetNames.map(name => {
      const sheetRows = XLSX.utils.sheet_to_json<unknown[]>(workbook.Sheets[name], {
        header: 1, raw: false, defval: '', dateNF: 'yyyy-mm-dd', blankrows: false,
      })
      try { return { rows: sheetRows, header: findHeaderRow(sheetRows) } } catch { return null }
    }).filter((candidate): candidate is { rows: unknown[][]; header: number } => candidate !== null)
    candidates.sort((a, b) => (b.rows.length - b.header) - (a.rows.length - a.header))
    if (!candidates.length) throw new Error('No worksheet contains a recognizable transaction table.')
    const selected = candidates[0]
    rows = selected.rows.slice(selected.header)
  } else if (extension === 'json') {
    rows = jsonToRows(JSON.parse((await file.text()).replace(/^\uFEFF/, '')))
  } else if (extension === 'csv' || extension === 'tsv' || extension === 'txt') {
    return parseBankCsv(await file.text())
  } else {
    throw new Error('Use an Excel workbook (.xlsx or .xls), CSV, TSV, text table, or JSON transaction file.')
  }

  // parseBankCsv performs the app's established date, amount, and column mapping.
  return parseBankCsv(rowsToCsv(rows))
}
