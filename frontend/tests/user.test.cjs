const assert = require('node:assert/strict')
const { test } = require('node:test')
const ts = require('typescript')
const fs = require('node:fs')
const Module = require('node:module')

global.__API_BASE__ = 'https://api.example.test'
const originalLoad = Module._load
Module._load = function (request, parent, isMain) {
  if (request === '@tarojs/taro') return { request: async () => { throw new Error('测试必须注入 request') } }
  return originalLoad.call(this, request, parent, isMain)
}

require.extensions['.ts'] = (module, filename) => {
  module._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2017 }
  }).outputText, filename)
}

function optionalModule(path) {
  try {
    return require(path)
  } catch (error) {
    if (error?.code === 'MODULE_NOT_FOUND' && String(error.message).includes(path.replace('../', ''))) return {}
    throw error
  }
}

const api = optionalModule('../src/api.ts')
const auth = optionalModule('../src/services/auth.ts')
const user = optionalModule('../src/domain/user.ts')

function memoryStorage(initial = {}) {
  const values = new Map(Object.entries(initial))
  return {
    get(key) { return values.get(key) },
    set(key, value) { values.set(key, value) },
    remove(key) { values.delete(key) },
    has(key) { return values.has(key) },
  }
}

test('业务请求统一携带 Bearer，并保留 GET、POST、PUT 的请求语义', async () => {
  assert.equal(typeof api.createApiClient, 'function', '需要实现 createApiClient')
  const calls = []
  const client = api.createApiClient({
    baseUrl: 'https://api.example.test/api/v1',
    getToken: () => 'token-for-test',
    clearIdentity: () => {},
    request: async options => {
      calls.push(options)
      return { statusCode: 200, data: { code: 0, message: 'ok', data: { ok: true } } }
    },
  })

  await client.get('user/profile', { page: 1 })
  await client.post('quiz/generate', { user_input: 'RAG' })
  await client.put('user/profile', { nickname: '学习者' })

  assert.deepEqual(calls.map(call => call.method), ['GET', 'POST', 'PUT'])
  assert.deepEqual(calls.map(call => call.header.Authorization), [
    'Bearer token-for-test', 'Bearer token-for-test', 'Bearer token-for-test'
  ])
  assert.deepEqual(calls[0].data, { page: 1 })
})

test('业务请求遇到 401 清理身份，但保留待提交闯关缓存', async () => {
  assert.equal(typeof api.createApiClient, 'function', '需要实现 createApiClient')
  let cleared = 0
  const client = api.createApiClient({
    baseUrl: 'https://api.example.test/api/v1',
    getToken: () => 'expired-token',
    clearIdentity: () => { cleared += 1 },
    request: async () => ({ statusCode: 401, data: { code: 401, message: 'unauthorized', data: null } }),
  })

  await assert.rejects(() => client.get('user/profile'), error => error?.statusCode === 401)
  assert.equal(cleared, 1)
})

test('旧请求迟到的 401 不得清理重新登录后的新身份', async () => {
  assert.equal(typeof api.createApiClient, 'function', '需要实现 createApiClient')
  let token = 'old-token'
  let cleared = 0
  let release
  const delayed = new Promise(resolve => { release = resolve })
  const client = api.createApiClient({
    baseUrl: 'https://api.example.test/api/v1',
    getToken: () => token,
    clearIdentity: () => { cleared += 1 },
    request: async () => { await delayed; return { statusCode: 401, data: { code: 401, message: 'unauthorized', data: null } } },
  })

  const oldRequest = client.get('user/profile')
  token = 'new-token'
  release()
  await assert.rejects(() => oldRequest, error => error?.statusCode === 401)
  assert.equal(cleared, 0)
})

test('并发登录共享同一次微信登录和服务端登录请求', async () => {
  assert.equal(typeof auth.createAuthController, 'function', '需要实现 createAuthController')
  let platformLoginCount = 0
  let serverLoginCount = 0
  let releaseLogin
  const loginPending = new Promise(resolve => { releaseLogin = resolve })
  const storage = memoryStorage()
  const controller = auth.createAuthController({
    env: 'weapp', storage,
    platformLogin: async () => { platformLoginCount += 1; await loginPending; return { code: 'wechat-code' } },
    loginRequest: async code => {
      serverLoginCount += 1
      assert.equal(code, 'wechat-code')
      return { token: 'jwt-for-test', user: { id: 7, nickname: '学习者', avatar_url: '', total_xp: 0 } }
    },
  })

  const first = controller.ensureLogin()
  const second = controller.ensureLogin()
  releaseLogin()
  const [left, right] = await Promise.all([first, second])

  assert.equal(platformLoginCount, 1)
  assert.equal(serverLoginCount, 1)
  assert.deepEqual(left, right)
})

test('401 后同账号重新登录保留完整待提交记录，换账号则清理', async () => {
  assert.equal(typeof auth.createAuthController, 'function', '需要实现 createAuthController')
  assert.equal(typeof auth.clearIdentity, 'function', '需要实现 clearIdentity')
  const pending = { quiz: { quiz_id: 'quiz-1', questions: [{ id: 'q1' }] }, records: [{ question_id: 'q1' }] }
  const storage = memoryStorage({
    auth_token: 'old-token', auth_user: { id: 7 }, cache_owner_id: 7,
    quiz: pending.quiz, records: pending.records, pending_report: pending,
  })

  auth.clearIdentity(storage)
  assert.equal(storage.has('auth_token'), false)
  assert.equal(storage.has('auth_user'), false)
  assert.equal(storage.has('pending_report'), true)

  const sameAccount = auth.createAuthController({
    env: 'weapp', storage,
    platformLogin: async () => ({ code: 'same' }),
    loginRequest: async () => ({ token: 'new-token', user: { id: 7, nickname: '原账号', avatar_url: '', total_xp: 20 } }),
  })
  await sameAccount.ensureLogin()
  assert.equal(storage.has('pending_report'), true)
  assert.equal(storage.has('quiz'), true)

  auth.clearIdentity(storage)
  const otherAccount = auth.createAuthController({
    env: 'weapp', storage,
    platformLogin: async () => ({ code: 'other' }),
    loginRequest: async () => ({ token: 'other-token', user: { id: 8, nickname: '新账号', avatar_url: '', total_xp: 0 } }),
  })
  await otherAccount.ensureLogin()
  assert.equal(storage.has('pending_report'), false)
  assert.equal(storage.has('quiz'), false)
  assert.equal(storage.has('records'), false)
})

test('应用重启只保留完整待提交报告，不恢复中途答题', () => {
  assert.equal(typeof auth.discardInterruptedQuiz, 'function', '需要实现 discardInterruptedQuiz')
  const interrupted = memoryStorage({ quiz: { quiz_id: 'quiz-1' }, records: [{ question_id: 'q1' }] })
  auth.discardInterruptedQuiz(interrupted)
  assert.equal(interrupted.has('quiz'), false)
  assert.equal(interrupted.has('records'), false)

  const completedQuiz = { quiz_id: 'quiz-2', questions: [{ id: 'q1' }] }
  const complete = memoryStorage({
    quiz: completedQuiz, records: [{ question_id: 'q1' }],
    pending_report: { quiz: completedQuiz, records: [{ question_id: 'q1' }] },
  })
  auth.discardInterruptedQuiz(complete)
  assert.equal(complete.has('quiz'), true)
  assert.equal(complete.has('pending_report'), true)
})

test('题库只在缓存归属与鉴权用户一致时可读取', () => {
  assert.equal(typeof auth.readOwnedQuiz, 'function', '需要实现 readOwnedQuiz')
  const ownedQuiz = { quiz_id: 'quiz-owned' }
  const matched = memoryStorage({ cache_owner_id: 7, quiz: ownedQuiz, records: [] })
  assert.deepEqual(auth.readOwnedQuiz(matched, 7), ownedQuiz)

  const mismatched = memoryStorage({ cache_owner_id: 7, quiz: { quiz_id: 'quiz-old' }, records: [{ question_id: 'q1' }] })
  assert.equal(auth.readOwnedQuiz(mismatched, 8), null)
  assert.equal(mismatched.has('quiz'), false)
  assert.equal(mismatched.has('records'), false)
})

test('首页只恢复当前账号且题数完整的待提交复盘', () => {
  assert.equal(typeof auth.readOwnedPendingReport, 'function', '需要实现 readOwnedPendingReport')
  const pending = {
    quiz: { quiz_id: 'quiz-pending', questions: [{ id: 'q1' }, { id: 'q2' }] },
    records: [{ question_id: 'q1' }, { question_id: 'q2' }],
  }
  const matched = memoryStorage({ cache_owner_id: 7, pending_report: pending })
  assert.deepEqual(auth.readOwnedPendingReport(matched, 7), pending)

  const incomplete = memoryStorage({ cache_owner_id: 7, pending_report: { ...pending, records: pending.records.slice(0, 1) } })
  assert.equal(auth.readOwnedPendingReport(incomplete, 7), null)

  const mismatched = memoryStorage({ cache_owner_id: 7, pending_report: pending, quiz: pending.quiz, records: pending.records })
  assert.equal(auth.readOwnedPendingReport(mismatched, 8), null)
  assert.equal(mismatched.has('pending_report'), false)
})

test('资料编辑只允许提交给当前页面同一用户', () => {
  assert.equal(typeof user.canSubmitProfileUpdate, 'function', '需要实现 canSubmitProfileUpdate')
  assert.equal(user.canSubmitProfileUpdate(7, 7), true)
  assert.equal(user.canSubmitProfileUpdate(7, 8), false)
})

test('H5 只能预览，昵称按方案做基础校验', () => {
  assert.equal(typeof user.canStartOfficialQuiz, 'function', '需要实现 canStartOfficialQuiz')
  assert.equal(typeof user.validateNickname, 'function', '需要实现 validateNickname')
  assert.equal(user.canStartOfficialQuiz('h5'), false)
  assert.equal(user.canStartOfficialQuiz('weapp'), true)
  assert.equal(user.validateNickname(''), '请输入昵称')
  assert.equal(user.validateNickname('a'.repeat(101)), '昵称不能超过 100 个字符')
  assert.equal(user.validateNickname(' 学习者 '), '')
})
