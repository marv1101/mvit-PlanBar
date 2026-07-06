import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import fs from 'fs'
import path from 'path'
import OfflineIndicator from '../components/OfflineIndicator'

describe('PWA - manifest.json', () => {
  const manifestPath = path.resolve(__dirname, '../../public/manifest.json')

  it('exists and is valid JSON', () => {
    const content = fs.readFileSync(manifestPath, 'utf-8')
    const manifest = JSON.parse(content)
    expect(manifest).toBeDefined()
  })

  it('has required PWA fields', () => {
    const content = fs.readFileSync(manifestPath, 'utf-8')
    const manifest = JSON.parse(content)
    expect(manifest.name).toBe('PlanBar - Dienstplan')
    expect(manifest.short_name).toBe('PlanBar')
    expect(manifest.description).toBeDefined()
    expect(manifest.theme_color).toBe('#1a1a2e')
    expect(manifest.background_color).toBe('#1a1a2e')
    expect(manifest.display).toBe('standalone')
    expect(manifest.orientation).toBe('portrait-primary')
    expect(manifest.start_url).toBe('/')
    expect(manifest.scope).toBe('/')
    expect(manifest.categories).toContain('productivity')
    expect(manifest.categories).toContain('business')
  })

  it('has icons array with 192x192 and 512x512', () => {
    const content = fs.readFileSync(manifestPath, 'utf-8')
    const manifest = JSON.parse(content)
    expect(manifest.icons).toBeInstanceOf(Array)
    expect(manifest.icons.length).toBeGreaterThanOrEqual(2)
    const sizes = manifest.icons.map((i: { sizes: string }) => i.sizes)
    expect(sizes).toContain('192x192')
    expect(sizes).toContain('512x512')
  })
})

describe('PWA - vite.config.ts', () => {
  const configPath = path.resolve(__dirname, '../../vite.config.ts')

  it('includes VitePWA plugin', () => {
    const content = fs.readFileSync(configPath, 'utf-8')
    expect(content).toContain('vite-plugin-pwa')
    expect(content).toContain('VitePWA')
    expect(content).toContain('registerType')
    expect(content).toContain('autoUpdate')
    expect(content).toContain('workbox')
    expect(content).toContain('runtimeCaching')
  })
})

describe('PWA - index.html', () => {
  const htmlPath = path.resolve(__dirname, '../../index.html')

  it('contains PWA meta tags', () => {
    const content = fs.readFileSync(htmlPath, 'utf-8')
    expect(content).toContain('name="theme-color"')
    expect(content).toContain('link rel="manifest"')
    expect(content).toContain('href="/manifest.json"')
    expect(content).toContain('name="apple-mobile-web-app-capable"')
    expect(content).toContain('name="apple-mobile-web-app-status-bar-style"')
    expect(content).toContain('name="apple-mobile-web-app-title"')
    expect(content).toContain('link rel="apple-touch-icon"')
    expect(content).toContain('href="/icons/icon-192x192.png"')
  })
})

describe('OfflineIndicator', () => {
  beforeEach(() => {
    vi.stubGlobal('navigator', { onLine: true })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders when offline', () => {
    vi.stubGlobal('navigator', { onLine: false })
    render(<OfflineIndicator />)
    expect(screen.getByText('Keine Internetverbindung')).toBeInTheDocument()
  })

  it('hides when online', () => {
    vi.stubGlobal('navigator', { onLine: true })
    render(<OfflineIndicator />)
    expect(screen.queryByText('Keine Internetverbindung')).not.toBeInTheDocument()
  })

  it('is dismissable by user', () => {
    vi.stubGlobal('navigator', { onLine: false })
    render(<OfflineIndicator />)
    expect(screen.getByText('Keine Internetverbindung')).toBeInTheDocument()
    fireEvent.click(screen.getByLabelText('Schließen'))
    expect(screen.queryByText('Keine Internetverbindung')).not.toBeInTheDocument()
  })
})
