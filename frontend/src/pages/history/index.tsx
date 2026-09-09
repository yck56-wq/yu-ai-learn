import { Button, Text, View } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { useRef, useState } from 'react'
import { get } from '../../api'
import { Loading, Screen } from '../../components/Sketch'
import type { QuizHistoryItem, QuizHistoryPage } from '../../domain/user'
import { canStartOfficialQuiz } from '../../domain/user'
import { ensureLogin, getStoredUser } from '../../services/auth'
import { setTabSelection } from '../../services/tabbar'
import './index.scss'

const H5_ITEMS: QuizHistoryItem[] = [
  { quiz_id: 'preview-1', title: 'RAG 入门闯关', accuracy: 80, question_count: 5, created_at: '2026-09-07 09:48:00' },
  { quiz_id: 'preview-2', title: '提示词工程基础', accuracy: 60, question_count: 5, created_at: '2026-09-06 20:15:00' },
]

export default function HistoryPage() {
  const [items, setItems] = useState<QuizHistoryItem[]>([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const loadSequence = useRef(0)
  const displayedUserId = useRef<number | null>(getStoredUser()?.id || null)
  const official = canStartOfficialQuiz(process.env.TARO_ENV)

  const load = async (nextPage = 1) => {
    const requestId = ++loadSequence.current
    setLoading(true)
    setError('')
    if (!official) {
      setItems(H5_ITEMS)
      setTotal(H5_ITEMS.length)
      setPage(1)
      setLoading(false)
      return
    }
    try {
      const authenticated = await ensureLogin()
      if (displayedUserId.current != null && displayedUserId.current !== authenticated.id) {
        setItems([])
        setTotal(0)
        setPage(1)
      }
      displayedUserId.current = authenticated.id
      const result = await get<QuizHistoryPage>('user/quizzes', { page: nextPage, page_size: 10 })
      if (requestId !== loadSequence.current || getStoredUser()?.id !== authenticated.id) return
      setItems(current => nextPage === 1 ? result.items : [...current, ...result.items])
      setTotal(result.total)
      setPage(result.page)
    } catch {
      if (requestId !== loadSequence.current) return
      const activeUser = getStoredUser()
      if (!activeUser || activeUser.id !== displayedUserId.current) {
        setItems([])
        setTotal(0)
        setPage(1)
      }
      setError('学习记录暂时没有加载成功，可以稍后重试。')
    } finally {
      setLoading(false)
    }
  }

  useDidShow(() => {
    setTabSelection(1)
    void load(1)
  })

  const open = (item: QuizHistoryItem) => {
    if (!official) {
      void Taro.showModal({ title: 'H5 界面预览', content: '历史详情请在微信小程序登录后查看。', showCancel: false })
      return
    }
    void Taro.navigateTo({ url: `/pages/report/index?quiz_id=${encodeURIComponent(item.quiz_id)}` })
  }

  return <Screen tabbed title='学习记录' icon='记'>
    {!official && <View className='ys-preview-note ys-page-note'>H5 界面预览 · 以下为样式示例</View>}
    {loading && !items.length ? <Loading /> : <View className='ys-content'>
      <View className='ys-history-heading'>
        <View><Text className='ys-section-kicker'>完成才算一页</Text><View className='ys-section-title'>闯过的关，都在这里</View></View>
        <View className='ys-history-total'>{total}<Text>轮</Text></View>
      </View>
      {error && <View className='ys-error'>{error}</View>}
      {!items.length && !error ? <View className='ys-empty-card'>
        <View className='ys-bubble'>还没有完成记录，先去闯一轮吧。</View>
        <View className='ys-mascot'>鱼</View>
        <Button className='ys-btn' onClick={() => Taro.switchTab({ url: '/pages/index/index' })}>去闯关</Button>
      </View> : <View className='ys-history-list'>
        {items.map((item, index) => <Button key={item.quiz_id} className='ys-history-card' onClick={() => open(item)}>
          <View className='ys-history-index'>{String(index + 1).padStart(2, '0')}</View>
          <View className='ys-history-main'>
            <Text className='ys-history-title'>{item.title}</Text>
            <Text className='ys-history-meta'>{item.question_count} 题 · {item.created_at}</Text>
          </View>
          <View className={`ys-accuracy-stamp ${item.accuracy >= 80 ? 'is-good' : ''}`}>{item.accuracy}%</View>
        </Button>)}
      </View>}
      {error && <Button className='ys-btn ys-next' onClick={() => load(1)}>重新加载</Button>}
      {!error && items.length < total && <Button className='ys-btn ys-next' disabled={loading} onClick={() => load(page + 1)}>
        {loading ? '正在翻下一页…' : '再翻一页'}
      </Button>}
    </View>}
  </Screen>
}
