import type { AnswerRecord, Question, Quiz, Report } from './quiz'

export const STORAGE_KEYS = {
  token: 'auth_token',
  user: 'auth_user',
  cacheOwnerId: 'cache_owner_id',
  quiz: 'quiz',
  records: 'records',
  report: 'report',
  pendingReport: 'pending_report',
} as const

export interface UserSummary {
  id: number
  nickname: string
  avatar_url: string
  total_xp: number
}

export interface UserProfile extends UserSummary {
  quiz_count: number
  correct_count: number
  average_accuracy: number
}

export interface LoginResult {
  token: string
  user: UserSummary
}

export interface PendingReport {
  quiz: Quiz
  records: AnswerRecord[]
}

export interface QuizHistoryItem {
  quiz_id: string
  title: string
  accuracy: number
  question_count: number
  created_at: string
}

export interface QuizHistoryPage {
  items: QuizHistoryItem[]
  total: number
  page: number
  page_size: number
}

export interface QuizHistoryDetail {
  quiz_id: string
  title: string
  summary: string
  questions: Question[]
  answer_records: AnswerRecord[]
  report: Report
}

export function canStartOfficialQuiz(env: string | undefined): boolean {
  return env === 'weapp'
}

export function validateNickname(value: string): string {
  const nickname = value.trim()
  if (!nickname) return '请输入昵称'
  if (nickname.length > 100) return '昵称不能超过 100 个字符'
  return ''
}

export function canSubmitProfileUpdate(profileUserId: number, authenticatedUserId: number): boolean {
  return profileUserId === authenticatedUserId
}
