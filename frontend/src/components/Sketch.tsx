import { PropsWithChildren, useState } from 'react'
import { View, Text, Button } from '@tarojs/components'
import Taro from '@tarojs/taro'
import CustomTabBar from '../custom-tab-bar'

export function Screen({ title, icon, onAction, actionLabel, tabbed = false, children }: PropsWithChildren<{
  title: string; icon: string; onAction?: () => void; actionLabel?: string; tabbed?: boolean
}>) {
  const [top] = useState(() => {
    if (process.env.TARO_ENV !== 'weapp') return 24
    const system = Taro.getSystemInfoSync()
    const capsule = Taro.getMenuButtonBoundingClientRect()
    return Math.max(capsule.bottom + 8, (system.statusBarHeight || 20) + 44)
  })
  return <View className={`ys-screen ${tabbed ? 'ys-tab-screen' : ''}`}>
    <View className='ys-system-space' style={{ height: `${top}px` }} />
    <View className='ys-nav'>
      <Text className='ys-brand'>{title}</Text>
      {onAction ? <Button className='ys-round-icon' aria-label={actionLabel} onClick={onAction}>{icon}</Button>
        : <View className='ys-round-icon'>{icon}</View>}
    </View>
    {children}
    {tabbed && process.env.TARO_ENV === 'h5' && <CustomTabBar />}
  </View>
}

export function Loading({ report = false }: { report?: boolean }) {
  return <View className='ys-content ys-loading'>
    <View>
      <View className='ys-stack'>
        <View className='ys-sheet' /><View className='ys-sheet ys-sheet-blue' />
        <View className='ys-sheet ys-sheet-yellow' /><View className='ys-sheet ys-sheet-front'>AI</View>
      </View>
      <View className='ys-loading-title'>{report ? '正在整理本轮知识收获' : 'AI 正在翻资料、划重点'}</View>
      <View className='ys-loading-copy'>{report ? '结合你的答题结果\n整理掌握点与薄弱点' : '预计生成 5 道题\n覆盖概念、易错点和工作场景'}</View>
      <View className='ys-dots'>● ● ●</View>
    </View>
  </View>
}

export function OptionCard({ option, state = '', onClick }: {
  option: { key: string; text: string }; state?: string; onClick?: () => void
}) {
  return <Button className={`ys-option ${state}`} onClick={onClick}>
    <Text className='ys-option-key'>{option.key}</Text><Text className='ys-option-text'>{option.text}</Text>
  </Button>
}
