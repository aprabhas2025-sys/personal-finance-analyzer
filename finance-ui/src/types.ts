export const CATEGORIES = [
  'Food Delivery', 'Dining Out', 'Groceries', 'Transport', 'Fuel', 'Shopping', 'Entertainment',
  'Subscriptions', 'Utilities', 'Rent', 'EMI', 'Health', 'Travel', 'Education', 'Transfers',
  'Salary', 'Other Income', 'Other',
] as const
export type Category = typeof CATEGORIES[number]
export type TxType = 'debit' | 'credit'
export type Transaction = { id: string; date: string; description: string; amount: number; type: TxType; category: Category; confidence: number; status: 'Cleared' | 'Pending' }
export type Period = '30 days' | '3 months' | '6 months' | 'All data'
export type MonthlyPoint = { month: string; spend: number; income: number; net: number; forecast?: number }
