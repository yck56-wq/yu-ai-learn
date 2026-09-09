import { Button, Image, Input, Text, View } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { useRef, useState } from 'react'
import { get, put } from '../../api'
import { Loading, Screen } from '../../components/Sketch'
import type { UserProfile } from '../../domain/user'
import { canStartOfficialQuiz, canSubmitProfileUpdate, validateNickname } from '../../domain/user'
import { ensureLogin, getStoredUser, updateStoredUser } from '../../services/auth'
import { setTabSelection } from '../../services/tabbar'
import './index.scss'

const H5_PROFILE: UserProfile = {
  id: 0, nickname: '学习者', avatar_url: '', total_xp: 80,
  quiz_count: 3, correct_count: 11, average_accuracy: 73,
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [nickname, setNickname] = useState('')
  const [editing, setEditing] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const loadSequence = useRef(0)
  const displayedUserId = useRef<number | null>(getStoredUser()?.id || null)
  const official = canStartOfficialQuiz(process.env.TARO_ENV)

  const load = async () => {
    const requestId = ++loadSequence.current
    setLoading(true)
    setError('')
    if (!official) {
      setProfile(H5_PROFILE)
      setNickname(H5_PROFILE.nickname)
      setLoading(false)
      return
    }
    try {
      const authenticated = await ensureLogin()
      if (displayedUserId.current != null && displayedUserId.current !== authenticated.id) {
        setProfile(null)
        setNickname('')
        setEditing(false)
      }
      displayedUserId.current = authenticated.id
      const result = await get<UserProfile>('user/profile')
      if (requestId !== loadSequence.current || getStoredUser()?.id !== authenticated.id) return
      setProfile(result)
      setNickname(result.nickname)
      updateStoredUser(result)
    } catch {
      if (requestId !== loadSequence.current) return
      const activeUser = getStoredUser()
      if (!activeUser || activeUser.id !== displayedUserId.current) {
        setProfile(null)
        setNickname('')
        setEditing(false)
      }
      setError('个人资料暂时没有加载成功，可以重新登录后再试。')
    } finally {
      setLoading(false)
    }
  }

  useDidShow(() => {
    setTabSelection(2)
    void load()
  })

  const save = async () => {
    const validation = validateNickname(nickname)
    if (validation) { setError(validation); return }
    if (!official) {
      setProfile(current => current ? { ...current, nickname: nickname.trim() } : current)
      setEditing(false)
      return
    }
    if (!profile) return
    setSaving(true)
    setError('')
    try {
      const authenticated = await ensureLogin()
      if (!canSubmitProfileUpdate(profile.id, authenticated.id)) {
        setProfile(null)
        setNickname('')
        setEditing(false)
        displayedUserId.current = authenticated.id
        await load()
        return
      }
      const result = await put<UserProfile>('user/profile', { nickname: nickname.trim(), avatar_url: profile.avatar_url })
      if (getStoredUser()?.id !== authenticated.id) return
      setProfile(result)
      updateStoredUser(result)
      setEditing(false)
    } catch {
      setError('昵称没有保存成功，请稍后重试。')
    } finally {
      setSaving(false)
    }
  }

  return <Screen tabbed title='我的' icon='我'>
    {!official && <View className='ys-preview-note ys-page-note'>H5 界面预览 · 编辑不会提交到服务端</View>}
    {loading && !profile ? <Loading /> : <View className='ys-content'>
      {profile && <>
        <View className='ys-profile-card'>
          {profile.avatar_url ? <Image className='ys-profile-avatar' src={profile.avatar_url} mode='aspectFill' />
            : <View className='ys-profile-avatar ys-default-avatar'>鱼</View>}
          <View className='ys-profile-copy'>
            {editing ? <Input className='ys-nickname-input' maxlength={100} value={nickname}
              onInput={event => { setNickname(event.detail.value); setError('') }} />
              : <Text className='ys-profile-name'>{profile.nickname}</Text>}
            <Text className='ys-profile-caption'>默认头像也能认真闯关</Text>
          </View>
          {editing ? <Button className='ys-small-button' disabled={saving} onClick={save}>{saving ? '保存中' : '保存'}</Button>
            : <Button className='ys-small-button' onClick={() => setEditing(true)}>改昵称</Button>}
        </View>
        {error && <View className='ys-error'>{error}</View>}
        <View className='ys-xp-ticket'><Text>累计经验</Text><View>{profile.total_xp}<Text> XP</Text></View></View>
        <View className='ys-stats-grid'>
          <View className='ys-stat-card'><Text>完成闯关</Text><View>{profile.quiz_count}<Text> 轮</Text></View></View>
          <View className='ys-stat-card'><Text>答对题目</Text><View>{profile.correct_count}<Text> 题</Text></View></View>
          <View className='ys-stat-card'><Text>累计正确率</Text><View>{profile.average_accuracy}<Text>%</Text></View></View>
        </View>
        <Button className='ys-profile-link' onClick={() => Taro.switchTab({ url: '/pages/history/index' })}>
          <View><Text className='ys-profile-link-title'>翻翻学习记录</Text><Text className='ys-profile-link-copy'>只展示已经完成的闯关</Text></View>
          <Text>→</Text>
        </Button>
      </>}
      {!profile && <>
        <View className='ys-error'>{error || '暂时无法读取个人资料。'}</View>
        <Button className='ys-btn ys-next' onClick={load}>重新加载</Button>
      </>}
    </View>}
  </Screen>
}
