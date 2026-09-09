import { View, Text, Button } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useEffect, useRef, useState } from 'react'
import { Loading, OptionCard, Screen } from '../../components/Sketch'
import { AnswerRecord, Quiz, getStats, isCorrect, recordAnswer, toggleAnswer } from '../../domain/quiz'
import { canStartOfficialQuiz } from '../../domain/user'
import { clearLearningCache, ensureLogin, readOwnedQuiz, savePendingReport, taroStorage } from '../../services/auth'

const TYPE_NAMES = { single: '单选题', multiple: '多选题', judge: '判断题' }

export default function QuizPage() {
  const [quiz, setQuiz] = useState<Quiz | null>(null)
  const [authReady, setAuthReady] = useState(false)
  const [index, setIndex] = useState(0)
  const [selected, setSelected] = useState<string[]>([])
  const [answered, setAnswered] = useState(false)
  const [records, setRecords] = useState<AnswerRecord[]>([])
  const [expanded, setExpanded] = useState(true)
  const started = useRef(Date.now())
  const locked = useRef(false)
  const official = canStartOfficialQuiz(process.env.TARO_ENV)
  const home = () => {
    clearLearningCache()
    return Taro.switchTab({ url: '/pages/index/index' })
  }
  useEffect(() => {
    if (!official) return
    let active = true
    void ensureLogin().then(user => {
      if (!active) return
      const ownedQuiz = readOwnedQuiz(taroStorage, user.id)
      if (!ownedQuiz) {
        void Taro.switchTab({ url: '/pages/index/index' })
        return
      }
      setQuiz(ownedQuiz)
      setAuthReady(true)
    }).catch(() => Taro.switchTab({ url: '/pages/index/index' }))
    return () => { active = false }
  }, [official])
  if (!official) return <Screen title='开卷有戏' icon='鱼'>
    <View className='ys-content'><View className='ys-preview-note'>H5 仅用于界面预览，正式答题请使用微信小程序。</View>
      <Button className='ys-btn ys-next' onClick={() => Taro.switchTab({ url: '/pages/index/index' })}>返回首页</Button></View>
  </Screen>
  if (!authReady) return <Screen title='正在确认账号' icon='鱼'><Loading /></Screen>
  const question = quiz?.questions[index]
  if (!question || !quiz) return <Screen title='开卷有戏' icon='?' onAction={home} actionLabel='返回首页'>
    <View className='ys-content'><View className='ys-feedback wrong'>本轮题库已失效，请返回首页重新生成。</View>
      <Button className='ys-btn ys-next' onClick={home}>返回首页</Button></View>
  </Screen>
  const correct = isCorrect(selected, question.answer)
  const { xp } = getStats(records)
  const submit = () => {
    if (locked.current || !selected.length) return
    locked.current = true
    const next = recordAnswer(records, { question_id: question.id, selected_answers: selected,
      is_correct: correct, duration_ms: Math.max(0, Date.now() - started.current) })
    setRecords(next)
    Taro.setStorageSync('records', next)
    setAnswered(true)
    setExpanded(true)
    Taro.pageScrollTo({ scrollTop: 0, duration: 0 })
  }
  const next = () => {
    if (index === quiz.questions.length - 1) {
      savePendingReport(quiz, records)
      Taro.redirectTo({ url: '/pages/report/index' })
      return
    }
    setIndex(index + 1)
    setSelected([])
    setAnswered(false)
    locked.current = false
    started.current = Date.now()
    Taro.pageScrollTo({ scrollTop: 0, duration: 0 })
  }
  const pause = async () => {
    const pauseStarted = Date.now()
    const result = await Taro.showModal({ title: '休息一下', content: '题目会留在这里，准备好就继续。返回首页将结束本轮答题。', confirmText: '继续答题', cancelText: '返回首页' })
    started.current += Date.now() - pauseStarted
    if (result.cancel) home()
  }
  return <Screen title={answered ? '回答结果' : quiz.title} icon={answered ? (correct ? '✓' : '!') : 'Ⅱ'}
    onAction={answered ? undefined : pause} actionLabel='暂停答题'>
    <View className={`ys-content ${answered ? 'ys-result' : ''}`}>
      {!answered ? <>
        <View className='ys-meta-row'><Text>第 {index + 1} / {quiz.questions.length} 题</Text>
          <View className='ys-progress'><View className='ys-progress-fill' style={{ width: `${(index + 1) / quiz.questions.length * 100}%` }} /></View><Text>{xp} XP</Text></View>
        <Text className='ys-type'>{TYPE_NAMES[question.type]} · {question.knowledge_point}</Text>
        <View className='ys-question'>{question.stem}</View>
        {question.type === 'multiple' && <View className='ys-hint'>选择所有正确选项，再提交答案</View>}
        {question.options.map(option => <OptionCard key={option.key} option={option}
          state={selected.includes(option.key) ? 'is-picked' : ''}
          onClick={() => setSelected(toggleAnswer(selected, option.key, question.type))} />)}
        <Button className={`ys-btn ys-next ${!selected.length ? 'is-disabled' : ''}`} disabled={!selected.length} onClick={submit}>提交答案</Button>
      </> : <>
        {correct && <View className='ys-xp-pop'>+20 XP!</View>}
        <View className='ys-bubble'>{correct ? '漂亮！这次没被概念绕进去。' : '踩坑了，但这个坑现在归你了。'}</View>
        <View className={`ys-mascot ${correct ? 'ys-mascot-green' : 'ys-mascot-red'}`}>{correct ? '耶' : '晕'}</View>
        {!correct && question.options.filter(option => selected.includes(option.key) && !question.answer.includes(option.key))
          .map(option => <OptionCard key={option.key} option={option} state='is-wrong' />)}
        {question.options.filter(option => question.answer.includes(option.key))
          .map(option => <OptionCard key={option.key} option={option} state='is-right' />)}
        <View className={`ys-feedback ${correct ? 'correct' : 'wrong'}`}>
          <View className='ys-feedback-title'>{correct ? '答对了，记住这个知识点' : '容易混淆，这里划个重点'}</View>
          {expanded && <View className='ys-feedback-copy'>{!correct && `正确答案：${question.answer.join('、')}。`}{question.explanation}</View>}
          <Button className='ys-expand' onClick={() => setExpanded(!expanded)}>{expanded ? '收起讲解 ∧' : '展开讲解 ∨'}</Button>
        </View>
        <Button className='ys-btn ys-next' onClick={next}>{index === quiz.questions.length - 1 ? '查看本轮复盘' : correct ? '下一题' : '记住了，下一题'}</Button>
      </>}
    </View>
  </Screen>
}
