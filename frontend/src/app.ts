import { PropsWithChildren } from 'react'
import { useLaunch } from '@tarojs/taro'
import { bootstrapAuth } from './services/auth'

import './app.scss'

function App({ children }: PropsWithChildren<any>) {
  useLaunch(() => {
    void bootstrapAuth().catch(() => undefined)
  })

  // children 是将要会渲染的页面
  return children
}
  


export default App
