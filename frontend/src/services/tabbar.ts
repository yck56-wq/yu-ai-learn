type Listener = (selected: number) => void

let selectedIndex = 0
const listeners = new Set<Listener>()

export function getTabSelection() {
  return selectedIndex
}

export function setTabSelection(selected: number) {
  selectedIndex = selected
  listeners.forEach(listener => listener(selected))
}

export function subscribeTabSelection(listener: Listener) {
  listeners.add(listener)
  return () => { listeners.delete(listener) }
}
