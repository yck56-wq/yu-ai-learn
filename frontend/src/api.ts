import Taro from '@tarojs/taro'
import { STORAGE_KEYS } from './domain/user'

// 仅公开后端地址，不能在前端放入模型密钥。
const API_BASE = typeof __API_BASE__ === 'undefined' ? 'http://localhost:8000' : __API_BASE__

interface ApiEnvelope<T> { code: number; message: string; data: T | null }
interface RequestOptions {
  url: string
  method: 'GET' | 'POST' | 'PUT'
  data?: object
  header: Record<string, string>
  timeout: number
}
interface RequestResponse<T> { statusCode: number; data: ApiEnvelope<T> }
interface ApiClientDependencies {
  baseUrl: string
  getToken: () => string
  clearIdentity: () => void
  request: <T>(options: RequestOptions) => Promise<RequestResponse<T>>
}

export class ApiError extends Error {
  constructor(message: string, public statusCode: number) {
    super(message)
    this.name = 'ApiError'
  }
}

export function createApiClient(dependencies: ApiClientDependencies) {
  const request = async <T>(method: RequestOptions['method'], path: string, data?: object, authorized = true): Promise<T> => {
    const token = authorized ? dependencies.getToken() : ''
    if (authorized && !token) {
      dependencies.clearIdentity()
      throw new ApiError('请先登录', 401)
    }
    const response = await dependencies.request<T>({
      url: `${dependencies.baseUrl.replace(/\/$/, '')}/${path}`,
      method,
      data,
      header: authorized ? { Authorization: `Bearer ${token}` } : {},
      timeout: 120000,
    })
    if (response.statusCode === 401) {
      if (authorized && dependencies.getToken() === token) dependencies.clearIdentity()
      throw new ApiError('登录状态已失效', 401)
    }
    if (response.statusCode < 200 || response.statusCode >= 300 || response.data.code !== 0 || response.data.data == null) {
      throw new ApiError('请求失败，请稍后重试', response.statusCode)
    }
    return response.data.data
  }
  return {
    get: <T>(path: string, data?: object) => request<T>('GET', path, data),
    post: <T>(path: string, data?: object) => request<T>('POST', path, data),
    put: <T>(path: string, data?: object) => request<T>('PUT', path, data),
    postPublic: <T>(path: string, data?: object) => request<T>('POST', path, data, false),
  }
}

const client = createApiClient({
  baseUrl: `${API_BASE}/api/v1`,
  getToken: () => Taro.getStorageSync(STORAGE_KEYS.token) || '',
  clearIdentity: () => {
    Taro.removeStorageSync(STORAGE_KEYS.token)
    Taro.removeStorageSync(STORAGE_KEYS.user)
  },
  request: options => Taro.request(options) as unknown as Promise<RequestResponse<any>>,
})

export const get = client.get
export const post = client.post
export const put = client.put
export const postPublic = client.postPublic
