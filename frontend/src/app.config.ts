export default defineAppConfig({
  pages: [
    'pages/index/index',
    'pages/history/index',
    'pages/profile/index',
    'pages/quiz/index',
    'pages/report/index'
  ],
  tabBar: {
    custom: true,
    color: '#6d6a62',
    selectedColor: '#222222',
    backgroundColor: '#fffdf6',
    borderStyle: 'black',
    list: [
      { pagePath: 'pages/index/index', text: '闯关' },
      { pagePath: 'pages/history/index', text: '学习记录' },
      { pagePath: 'pages/profile/index', text: '我的' }
    ]
  },
  window: {
    navigationStyle: 'custom',
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#fffdf6',
    navigationBarTitleText: '开卷有戏',
    navigationBarTextStyle: 'black'
  }
})
