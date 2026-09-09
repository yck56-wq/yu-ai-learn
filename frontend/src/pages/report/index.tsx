import { View, Button } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import { useEffect, useState } from 'react'
import { Loading, Screen } from '../../components/Sketch'
import { get, post } from '../../api'
import { Report, getStats } from '../../domain/quiz'
import type { QuizHistoryDetail } from '../../domain/user'
import { STORAGE_KEYS, canStartOfficialQuiz } from '../../domain/user'
import { clearPendingReport, ensureLogin } from '../../services/auth'

const H5_DETAIL: QuizHistoryDetail = {
  quiz_id: 'preview',
  title: 'RAG 入门闯关',
  summary: 'H5 界面预览',
  questions: [],
  answer_records: [
    { question_id: 'q1', selected_answers: ['B'], duration_ms: 36000, is_correct: true },
    { question_id: 'q2', selected_answers: ['A'], duration_ms: 42000, is_correct: true },
    { question_id: 'q3', selected_answers: ['A'], duration_ms: 39000, is_correct: false },
    { question_id: 'q4', selected_answers: ['A'], duration_ms: 44000, is_correct: true },
    { question_id: 'q5', selected_answers: ['B'], duration_ms: 45000, is_correct: true },
  ],
  report: {
    accuracy: 80,
    mastered_points: ['RAG 基本结构', '检索与生成关系'],
    weak_points: ['向量检索', '知识库更新机制'],
    three_line_summary: ['先检索，再生成；', '资料决定回答边界；', '知识库质量影响最终效果。'],
    advice: ['再练习一次。'],
  },
}

export default function ReportPage() {
  const router = useRouter()
  const historyQuizId = router.params.quiz_id
  const historyMode = Boolean(historyQuizId)
  const [detail, setDetail] = useState<QuizHistoryDetail | null>(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const official = canStartOfficialQuiz(process.env.TARO_ENV)

  useEffect(() => {
    let active = true
    const load = async () => {
      if (!official) {
        setDetail(H5_DETAIL)
        return
      }
      setError('')
      setDetail(null)
      try {
        await ensureLogin()
        let result: QuizHistoryDetail
        if (historyQuizId) {
          result = await get<QuizHistoryDetail>(`user/quizzes/${encodeURIComponent(historyQuizId)}`)
        } else {
          const pending = Taro.getStorageSync(STORAGE_KEYS.pendingReport)
          const quiz = pending?.quiz
          const records = pending?.records
          if (!quiz || !Array.isArray(records) || records.length !== quiz.questions?.length) {
            throw new Error('missing pending report')
          }
          await post<Report>('report/generate', {
            quiz_id: quiz.quiz_id,
            topic: quiz.title,
            questions: quiz.questions,
            answer_records: records,
          })
          result = await get<QuizHistoryDetail>(`user/quizzes/${encodeURIComponent(quiz.quiz_id)}`)
          Taro.setStorageSync(STORAGE_KEYS.report, result.report)
          clearPendingReport()
        }
        if (active) setDetail(result)
      } catch {
        if (active) setError(historyMode ? '这份学习记录暂时没有加载成功。' : '复盘暂时没有生成成功，完整答题记录已保留。')
      }
    }
    void load()
    return () => { active = false }
  }, [attempt, historyMode, historyQuizId, official])

  const home = () => Taro.switchTab({ url: '/pages/index/index' })
  const back = () => Taro.navigateBack({ delta: 1 })
  const stats = detail ? getStats(detail.answer_records) : { xp: 0, durationSeconds: 0 }

  return <Screen title={historyMode ? '历史复盘' : '本轮复盘'} icon={historyMode ? '←' : '↗'}
    onAction={historyMode ? back : undefined} actionLabel={historyMode ? '返回上一页' : undefined}>
    {!official && <View className='ys-preview-note ys-page-note'>H5 界面预览 · 服务端成绩以微信小程序登录记录为准</View>}
    {error ? <View className='ys-content'><View className='ys-feedback wrong'>{error}</View>
      <Button className='ys-btn ys-next' onClick={() => setAttempt(value => value + 1)}>{historyMode ? '重新加载' : '重试提交并读取成绩'}</Button>
      <Button className='ys-btn ys-next ys-secondary' onClick={home}>返回首页</Button></View>
      : !detail ? <Loading report /> : <View className='ys-content'>
        <View className='ys-report-title'>{detail.title} · 通关！</View>
        <View className='ys-report-sub'>{detail.answer_records.length} 题用时 {Math.floor(stats.durationSeconds / 60)} 分 {stats.durationSeconds % 60} 秒 · 获得 {stats.xp} XP</View>
        <View className='ys-score'><View className='ys-score-number'>{detail.report.accuracy}%</View><View className='ys-score-label'>知识掌握度</View></View>
        <View className='ys-two-col'>
          <View className='ys-note good'><View className='ys-note-title'>已经掌握</View>{detail.report.mastered_points.length ? detail.report.mastered_points.map(point => <View key={point}>{point}</View>) : '再练一轮，逐个掌握'}</View>
          <View className='ys-note weak'><View className='ys-note-title'>还需补一补</View>{detail.report.weak_points.length ? detail.report.weak_points.map(point => <View key={point}>{point}</View>) : '本轮没有答错，继续保持'}</View>
        </View>
        <View className='ys-summary'><View className='ys-summary-title'>三句话带走：</View>{detail.report.three_line_summary.map((line, index) => <View key={index}>{line}</View>)}</View>
        <Button className='ys-btn ys-next' onClick={historyMode ? back : home}>{historyMode ? '返回学习记录' : '再闯一轮巩固'}</Button>
      </View>}
  </Screen>
}
