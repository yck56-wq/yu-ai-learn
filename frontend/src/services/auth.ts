import Taro from '@tarojs/taro'
import { get, postPublic } from '../api'
import type { Quiz } from '../domain/quiz'
import { LoginResult, PendingReport, STORAGE_KEYS, UserProfile, UserSummary, canStartOfficialQuiz } from '../domain/user'

export interface StorageAdapter {
  get(key: string): any
  set(key: string, value: any): void
  remove(key: string): void
}

interface AuthDependencies {
  env: string | undefined
  storage: StorageAdapter
  platformLogin: () => Promise<{ code?: string }>
  loginRequest: (code: string) => Promise<LoginResult>
}

const LEARNING_KEYS = [STORAGE_KEYS.quiz, STORAGE_KEYS.records, STORAGE_KEYS.report, STORAGE_KEYS.pendingReport]

export const taroStorage: StorageAdapter = {
  get: key => Taro.getStorageSync(key),
  set: (key, value) => Taro.setStorageSync(key, value),
  remove: key => Taro.removeStorageSync(key),
}

export function clearIdentity(storage: StorageAdapter = taroStorage) {
  storage.remove(STORAGE_KEYS.token)
  storage.remove(STORAGE_KEYS.user)
}

export function clearLearningCache(storage: StorageAdapter = taroStorage) {
  LEARNING_KEYS.forEach(key => storage.remove(key))
}

export function discardInterruptedQuiz(storage: StorageAdapter = taroStorage) {
  const pending = storage.get(STORAGE_KEYS.pendingReport)
  if (isCompletePendingReport(pending)) return
  clearLearningCache(storage)
}

function isCompletePendingReport(value: any): value is PendingReport {
  return Boolean(value?.quiz?.quiz_id && Array.isArray(value.quiz.questions) && value.quiz.questions.length > 0
    && Array.isArray(value.records) && value.records.length === value.quiz.questions.length)
}

export function readOwnedQuiz(storage: StorageAdapter, userId: number): Quiz | null {
  const ownerId = storage.get(STORAGE_KEYS.cacheOwnerId)
  if (ownerId == null || Number(ownerId) !== userId) {
    clearLearningCache(storage)
    return null
  }
  return storage.get(STORAGE_KEYS.quiz) || null
}

export function readOwnedPendingReport(storage: StorageAdapter, userId: number): PendingReport | null {
  const ownerId = storage.get(STORAGE_KEYS.cacheOwnerId)
  if (ownerId == null || Number(ownerId) !== userId) {
    clearLearningCache(storage)
    return null
  }
  const pending = storage.get(STORAGE_KEYS.pendingReport)
  if (!isCompletePendingReport(pending)) {
    if (pending) clearLearningCache(storage)
    return null
  }
  return pending
}

function saveLogin(storage: StorageAdapter, result: LoginResult) {
  const previousOwner = storage.get(STORAGE_KEYS.cacheOwnerId)
  const hasLearningCache = LEARNING_KEYS.some(key => Boolean(storage.get(key)))
  if ((previousOwner == null && hasLearningCache) || (previousOwner != null && Number(previousOwner) !== result.user.id)) {
    clearLearningCache(storage)
  }
  storage.set(STORAGE_KEYS.cacheOwnerId, result.user.id)
  storage.set(STORAGE_KEYS.token, result.token)
  storage.set(STORAGE_KEYS.user, result.user)
}

export function createAuthController(dependencies: AuthDependencies) {
  let loginInFlight: Promise<UserSummary> | null = null
  const ensureLogin = () => {
    const storedUser = dependencies.storage.get(STORAGE_KEYS.user) as UserSummary | undefined
    const token = dependencies.storage.get(STORAGE_KEYS.token)
    if (storedUser && token) return Promise.resolve(storedUser)
    if (!canStartOfficialQuiz(dependencies.env)) return Promise.reject(new Error('H5 仅用于界面预览'))
    if (!loginInFlight) {
      loginInFlight = dependencies.platformLogin()
        .then(result => {
          if (!result.code) throw new Error('微信登录失败')
          return dependencies.loginRequest(result.code)
        })
        .then(result => {
          saveLogin(dependencies.storage, result)
          return result.user
        })
        .finally(() => { loginInFlight = null })
    }
    return loginInFlight
  }
  return { ensureLogin }
}

const runtimeAuth = createAuthController({
  env: process.env.TARO_ENV,
  storage: taroStorage,
  platformLogin: () => Taro.login(),
  loginRequest: code => postPublic<LoginResult>('user/login', { code }),
})

export const ensureLogin = runtimeAuth.ensureLogin

export function getStoredUser(): UserSummary | null {
  return taroStorage.get(STORAGE_KEYS.user) || null
}

export function updateStoredUser(user: UserSummary) {
  taroStorage.set(STORAGE_KEYS.user, user)
}

export async function bootstrapAuth(): Promise<UserSummary | null> {
  discardInterruptedQuiz()
  if (!canStartOfficialQuiz(process.env.TARO_ENV)) return null
  if (taroStorage.get(STORAGE_KEYS.token)) {
    try {
      const profile = await get<UserProfile>('user/profile')
      updateStoredUser(profile)
      return profile
    } catch {
      // 请求层会在 401 时清理身份，随后统一走微信登录。
    }
  }
  return ensureLogin()
}

export function savePendingReport(quiz: unknown, records: unknown[]) {
  taroStorage.set(STORAGE_KEYS.pendingReport, { quiz, records })
}

export function clearPendingReport() {
  taroStorage.remove(STORAGE_KEYS.pendingReport)
}
