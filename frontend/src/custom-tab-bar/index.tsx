import { Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useEffect, useState } from 'react'
import { getTabSelection, setTabSelection, subscribeTabSelection } from '../services/tabbar'
import './index.scss'

const TABS = [
  { text: '闯关', icon: '闯', url: '/pages/index/index' },
  { text: '学习记录', icon: '记', url: '/pages/history/index' },
  { text: '我的', icon: '我', url: '/pages/profile/index' },
]

export default function CustomTabBar() {
  const [selected, setSelected] = useState(getTabSelection)
  useEffect(() => subscribeTabSelection(setSelected), [])
  const switchTo = (index: number) => {
    if (index === selected) return
    setTabSelection(index)
    void Taro.switchTab({ url: TABS[index].url })
  }
  return <View className='ys-tabbar-wrap'>
    <View className='ys-tabbar'>
      {TABS.map((tab, index) => <View key={tab.url} className={`ys-tabbar-item ${selected === index ? 'is-selected' : ''}`}
        onClick={() => switchTo(index)}>
        <Text className='ys-tabbar-icon'>{tab.icon}</Text>
        <Text className='ys-tabbar-text'>{tab.text}</Text>
      </View>)}
    </View>
  </View>
}
