export interface ScreenMetricDependencies {
  getSystemInfoSync: () => { statusBarHeight?: number }
  getMenuButtonBoundingClientRect: () => { bottom: number }
}

let cachedTop: number | null = null

export function getScreenTop(env: string | undefined, dependencies: ScreenMetricDependencies): number {
  if (env !== 'weapp') return 24
  if (cachedTop != null) return cachedTop
  const system = dependencies.getSystemInfoSync()
  const capsule = dependencies.getMenuButtonBoundingClientRect()
  cachedTop = Math.max(capsule.bottom + 8, (system.statusBarHeight || 20) + 44)
  return cachedTop
}

export function resetScreenTopCache() {
  cachedTop = null
}
