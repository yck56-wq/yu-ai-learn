export type QuestionType = 'single' | 'multiple' | 'judge'
export interface Option { key: string; text: string }
export interface Question {
  id: string
  type: QuestionType
  stem: string
  options: Option[]
  answer: string[]
  explanation: string
  knowledge_point: string
  difficulty: string
}
export interface Quiz { quiz_id: string; title: string; summary: string; questions: Question[] }
export interface AnswerRecord {
  question_id: string
  selected_answers: string[]
  duration_ms: number
  is_correct: boolean
}
export interface Report {
  accuracy: number
  mastered_points: string[]
  weak_points: string[]
  three_line_summary: string[]
  advice: string[]
}
export function toggleAnswer(selected: string[], key: string, type: QuestionType): string[] {
  if (type !== 'multiple') return [key]
  return selected.includes(key) ? selected.filter(value => value !== key) : [...selected, key]
}
export function isCorrect(selected: string[], answer: string[]): boolean {
  return selected.length > 0 && selected.length === answer.length && answer.every(key => selected.includes(key))
}
export function recordAnswer(records: AnswerRecord[], record: AnswerRecord): AnswerRecord[] {
  if (!record.selected_answers.length || records.some(item => item.question_id === record.question_id)) return records
  return [...records, record]
}
export function getStats(records: AnswerRecord[]) {
  const correct = records.filter(record => record.is_correct).length
  return { xp: correct * 20, correct, durationSeconds: Math.round(records.reduce((sum, record) => sum + record.duration_ms, 0) / 1000) }
}
