import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './app/App.tsx'
import './styles/index.css'
import { registerServiceWorker } from './app/lib/registerSW.ts'
import { onlineManager } from '@tanstack/react-query'

registerServiceWorker({
  onUpdate: (registration) => {
    registration.waiting?.postMessage({ type: 'SKIP_WAITING' })
  },
})

onlineManager.setEventListener((setOnline) => {
  function handleOnline() { setOnline(true) }
  function handleOffline() { setOnline(false) }
  window.addEventListener('online', handleOnline)
  window.addEventListener('offline', handleOffline)
  setOnline(navigator.onLine)
  return () => {
    window.removeEventListener('online', handleOnline)
    window.removeEventListener('offline', handleOffline)
  }
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
