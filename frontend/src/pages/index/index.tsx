import { View, Textarea, Button, Text, Image } from '@tarojs/components'
import { useRef, useState } from 'react'
import Taro, { useDidShow } from '@tarojs/taro'
import { Loading, Screen } from '../../components/Sketch'
import { get, post } from '../../api'
import type { Quiz } from '../../domain/quiz'
import type { PendingReport, QuizHistoryItem, QuizHistoryPage, UserProfile, UserSummary } from '../../domain/user'
import { STORAGE_KEYS, canStartOfficialQuiz } from '../../domain/user'
import { clearPendingReport, ensureLogin, getStoredUser, readOwnedPendingReport, taroStorage, updateStoredUser } from '../../services/auth'
import { setTabSelection } from '../../services/tabbar'

const CASES = [
  { title: 'RAG 基础概念', keywords: '检索 / 向量库 / 生成', text: 'RAG 和传统搜索有什么区别？我想弄懂向量数据库如何配合工作。' },
  { title: '提示词工程', keywords: '角色 / 约束 / 输出格式', text: '提示词工程中，角色、约束和输出格式分别有什么作用？' },
]
const TOPICS = ['产品方法', 'AI 基础', '汇报表达']
const H5_PREVIEW_USER: UserSummary = { id: 0, nickname: '学习者', avatar_url: '', total_xp: 80 }
const H5_PREVIEW_HISTORY: QuizHistoryItem = {
  quiz_id: 'preview', title: 'RAG 入门闯关', accuracy: 80, question_count: 5, created_at: '2026-09-07 09:48:00'
}

export default function Index() {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [authLoading, setAuthLoading] = useState(false)
  const [error, setError] = useState('')
  const [user, setUser] = useState<UserSummary | null>(() => getStoredUser())
  const [recent, setRecent] = useState<QuizHistoryItem | null>(null)
  const [pendingReport, setPendingReport] = useState<PendingReport | null>(null)
  const generation = useRef(0)
  const busy = useRef(false)
  const loadSequence = useRef(0)
  const displayedUserId = useRef<number | null>(user?.id || null)
  const official = canStartOfficialQuiz(process.env.TARO_ENV)

  const loadUser = async () => {
    const requestId = ++loadSequence.current
    if (!official) {
      setUser(H5_PREVIEW_USER)
      setRecent(H5_PREVIEW_HISTORY)
      setPendingReport(null)
      return
    }
    setAuthLoading(true)
    try {
      const authenticated = await ensureLogin()
      if (displayedUserId.current != null && displayedUserId.current !== authenticated.id) {
        setUser(null)
        setRecent(null)
        setPendingReport(null)
      }
      displayedUserId.current = authenticated.id
      const [profile, history] = await Promise.all([
        get<UserProfile>('user/profile'),
        get<QuizHistoryPage>('user/quizzes', { page: 1, page_size: 1 }),
      ])
      if (requestId !== loadSequence.current || getStoredUser()?.id !== authenticated.id) return
      updateStoredUser(profile)
      setUser(profile)
      setRecent(history.items[0] || null)
      setPendingReport(readOwnedPendingReport(taroStorage, authenticated.id))
      setError('')
    } catch {
      if (requestId !== loadSequence.current) return
      setUser(null)
      setRecent(null)
      setPendingReport(null)
      setError('微信登录暂时没有完成，你的输入会保留，可以重新登录。')
    } finally {
      setAuthLoading(false)
    }
  }

  useDidShow(() => {
    setTabSelection(0)
    void loadUser()
  })

  const cancel = () => {
    generation.current += 1
    busy.current = false
    setLoading(false)
  }
  const start = async () => {
    if (!official) {
      await Taro.showModal({ title: 'H5 界面预览', content: '正式闯关仅在微信小程序中开放。', showCancel: false })
      return
    }
    if (busy.current) return
    if (!input.trim()) { setError('先输入想学的内容，也可以点击下面的案例。'); return }
    busy.current = true
    const id = ++generation.current
    setError('')
    setLoading(true)
    try {
      const authenticated = await ensureLogin()
      const ownedPending = readOwnedPendingReport(taroStorage, authenticated.id)
      if (ownedPending) {
        const choice = await Taro.showModal({
          title: '上一轮复盘还没提交',
          content: '可以先重试上一轮复盘；如果开始新题，将放弃这份待提交记录。',
          confirmText: '放弃并开始',
          cancelText: '先去复盘',
        })
        if (choice.cancel) {
          busy.current = false
          setLoading(false)
          await Taro.navigateTo({ url: '/pages/report/index' })
          return
        }
        clearPendingReport()
        setPendingReport(null)
      }
      const quiz = await post<Quiz>('quiz/generate', { user_input: input.trim(), question_count: 5, difficulty: 'mixed' })
      if (id !== generation.current) return
      if (getStoredUser()?.id !== authenticated.id || Number(taroStorage.get(STORAGE_KEYS.cacheOwnerId)) !== authenticated.id) return
      if (!quiz.questions?.length) throw new Error('empty quiz')
      Taro.setStorageSync('quiz', quiz)
      Taro.setStorageSync('records', [])
      Taro.removeStorageSync('report')
      Taro.removeStorageSync('pending_report')
      await Taro.navigateTo({ url: '/pages/quiz/index' })
    } catch {
      if (id === generation.current) setError('这次备题没有成功，请重试。你的输入已保留。')
    } finally {
      if (id === generation.current) { busy.current = false; setLoading(false) }
    }
  }

  return <Screen tabbed title={loading ? '正在备题' : '开卷有戏'} icon={loading ? '×' : '?'}
    actionLabel={loading ? '取消生成' : '使用帮助'} onAction={loading ? cancel : () => {
      Taro.showModal({ title: '开卷有戏', content: '输入想学的主题，生成 5 道闯关题。提交答案后查看讲解，完成后查看本轮复盘。', showCancel: false })
    }}>
    {loading ? <Loading /> : <View className='ys-content'>
      {!official && <View className='ys-preview-note'>H5 界面预览 · 正式答题请使用微信小程序</View>}
      <View className='ys-user-strip'>
        {user?.avatar_url ? <Image className='ys-mini-avatar' src={user.avatar_url} mode='aspectFill' />
          : <View className='ys-mini-avatar'>{user?.nickname?.slice(0, 1) || '鱼'}</View>}
        <View className='ys-user-copy'>
          <Text className='ys-user-greeting'>{user ? `${user.nickname}，今天学点什么？` : '正在连接你的学习账号'}</Text>
          <Text className='ys-user-xp'>{user ? `累计 ${user.total_xp} XP` : '微信登录后开始闯关'}</Text>
        </View>
        {recent && <Button className='ys-text-button' onClick={() => {
          if (official) void Taro.navigateTo({ url: `/pages/report/index?quiz_id=${encodeURIComponent(recent.quiz_id)}` })
        }}>最近 {recent.accuracy}%</Button>}
      </View>
      {pendingReport && <Button className='ys-pending-card' onClick={() => Taro.navigateTo({ url: '/pages/report/index' })}>
        <View><Text className='ys-pending-title'>上一轮复盘还没交卷</Text><Text className='ys-pending-copy'>完整答题记录已保留，点这里继续提交</Text></View>
        <Text className='ys-pending-arrow'>→</Text>
      </Button>}
      <View className='ys-bubble'>今天摸鱼……不，学点啥？</View>
      <View className='ys-mascot'>鱼</View>
      <View className='ys-input'>
        <Textarea className='ys-textarea' maxlength={5000} value={input}
          placeholder='我想弄懂 RAG 和传统搜索到底有什么区别，最好能结合工作中的知识库案例。'
          placeholderClass='ys-placeholder' onInput={e => { setInput(e.detail.value); setError('') }} />
      </View>
      <View className='ys-chips'>{TOPICS.map(topic => <Button key={topic} className='ys-chip'
        onClick={() => { setInput(`我想学习${topic}，请结合工作场景讲解核心概念和易错点。`); setError('') }}>{topic}</Button>)}</View>
      {error && <View className='ys-error' role='alert'>{error}</View>}
      {!user && official && <Button className='ys-btn ys-secondary' disabled={authLoading} onClick={loadUser}>{authLoading ? '正在登录…' : '重新微信登录'}</Button>}
      <Button className={`ys-btn ${(!user || authLoading) && official ? 'is-disabled' : ''}`}
        disabled={(!user || authLoading) && official} onClick={start}>{official ? '开始生成闯关题' : 'H5 仅预览，微信小程序中闯关'}</Button>
      <View className='ys-cases'>{CASES.map(item => <Button key={item.title} className='ys-case'
        onClick={() => { setInput(item.text); setError('') }}>
        <Text className='ys-case-title'>{item.title}</Text><Text className='ys-case-meta'>{item.keywords}</Text>
      </Button>)}</View>
    </View>}
  </Screen>
}
