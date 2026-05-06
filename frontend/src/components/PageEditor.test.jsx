import { StrictMode } from 'react'
import { render, screen, act, cleanup } from '@testing-library/react'
import { vi, beforeEach, afterEach } from 'vitest'

const { mockEditor, capturedConfig } = vi.hoisted(() => ({
  mockEditor: {
    getText: () => '',
    getJSON: () => ({}),
    isActive: () => false,
    commands: { setContent: () => {} },
  },
  capturedConfig: { current: null },
}))

vi.mock('@tiptap/react', () => ({
  useEditor: (config) => {
    capturedConfig.current = config
    return mockEditor
  },
  EditorContent: () => null,
}))

vi.mock('@tiptap/react/menus', () => ({
  BubbleMenu: () => null,
}))

vi.mock('@tiptap/starter-kit', () => ({ default: {} }))
vi.mock('@tiptap/extension-placeholder', () => ({
  default: { configure: () => ({}) },
}))

vi.mock('../api/pages', () => ({
  updatePage: vi.fn().mockResolvedValue({}),
}))

import PageEditor from './PageEditor'
import { updatePage } from '../api/pages'

describe('PageEditor word/character count', () => {
  beforeEach(() => {
    mockEditor.getText = () => ''
    mockEditor.getJSON = () => ({})
    capturedConfig.current = null
    updatePage.mockClear()
  })

  it('renders 0 words · 0 chars for an empty page', () => {
    render(<PageEditor page={{ id: 1, content: {} }} />)
    expect(screen.getByText('0 words · 0 chars')).toBeInTheDocument()
  })

  it('updates counts when the editor onUpdate fires', () => {
    render(<PageEditor page={{ id: 1, content: {} }} />)
    mockEditor.getText = () => 'hello world foo'
    act(() => {
      capturedConfig.current.onUpdate({ editor: mockEditor })
    })
    expect(screen.getByText('3 words · 15 chars')).toBeInTheDocument()
  })

  it('formats large counts with thousands separators', () => {
    render(<PageEditor page={{ id: 1, content: {} }} />)
    const text = [...Array(131).fill('aaaaa'), ...Array(211).fill('aaaa')].join(' ')
    expect(text).toHaveLength(1840)
    expect(text.split(/\s+/)).toHaveLength(342)
    mockEditor.getText = () => text
    act(() => {
      capturedConfig.current.onUpdate({ editor: mockEditor })
    })
    expect(
      screen.getByText(/342\s+words\s+·\s+1[,.\s]?840\s+chars/)
    ).toBeInTheDocument()
  })
})

describe('PageEditor auto-save', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mockEditor.getText = () => ''
    mockEditor.getJSON = () => ({})
    capturedConfig.current = null
    updatePage.mockReset()
    updatePage.mockResolvedValue({})
  })

  afterEach(() => {
    cleanup()
    vi.useRealTimers()
  })

  const fireTyping = (json) => {
    mockEditor.getJSON = () => json
    act(() => {
      capturedConfig.current.onUpdate({ editor: mockEditor })
    })
  }

  it('debounces rapid typing to a single save with the latest content', async () => {
    render(<PageEditor page={{ id: 1, content: {} }} />)

    fireTyping({ v: 1 })
    act(() => { vi.advanceTimersByTime(100) })
    fireTyping({ v: 2 })
    act(() => { vi.advanceTimersByTime(100) })
    fireTyping({ v: 3 })
    act(() => { vi.advanceTimersByTime(100) })
    fireTyping({ v: 4 })
    act(() => { vi.advanceTimersByTime(100) })
    fireTyping({ v: 5 })

    // 999ms after the last keystroke — debounce should NOT have fired yet
    act(() => { vi.advanceTimersByTime(999) })
    expect(updatePage).not.toHaveBeenCalled()

    // 1000ms after the last keystroke — debounce fires once
    await act(async () => { await vi.advanceTimersByTimeAsync(1) })
    expect(updatePage).toHaveBeenCalledTimes(1)
    expect(updatePage).toHaveBeenCalledWith(1, { content: { v: 5 } })
  })

  it('resets the debounce window on each new keystroke', async () => {
    render(<PageEditor page={{ id: 1, content: {} }} />)

    fireTyping({ v: 'a' })
    act(() => { vi.advanceTimersByTime(500) })
    expect(updatePage).not.toHaveBeenCalled()

    fireTyping({ v: 'b' })
    // 999ms after the SECOND keystroke (1499ms total) — still not fired
    act(() => { vi.advanceTimersByTime(999) })
    expect(updatePage).not.toHaveBeenCalled()

    // 1000ms after the second keystroke — now fires
    await act(async () => { await vi.advanceTimersByTimeAsync(1) })
    expect(updatePage).toHaveBeenCalledTimes(1)
    expect(updatePage).toHaveBeenCalledWith(1, { content: { v: 'b' } })
  })

  it('flushes the pending save when the editor unmounts mid-debounce', () => {
    const { unmount } = render(<PageEditor page={{ id: 1, content: {} }} />)

    fireTyping({ unsaved: true })
    act(() => { vi.advanceTimersByTime(500) })
    expect(updatePage).not.toHaveBeenCalled()

    act(() => { unmount() })
    expect(updatePage).toHaveBeenCalledTimes(1)
    expect(updatePage).toHaveBeenCalledWith(1, { content: { unsaved: true } })
  })

  it('does not save on unmount when there is no pending edit', () => {
    const { unmount } = render(<PageEditor page={{ id: 1, content: {} }} />)
    act(() => { unmount() })
    expect(updatePage).not.toHaveBeenCalled()
  })

  it('does not double-save when the debounce already flushed before unmount', async () => {
    const { unmount } = render(<PageEditor page={{ id: 1, content: {} }} />)

    fireTyping({ v: 'final' })
    await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
    expect(updatePage).toHaveBeenCalledTimes(1)

    act(() => { unmount() })
    expect(updatePage).toHaveBeenCalledTimes(1)
  })

  it('flushes the pending save with the OLD page id when page swaps in place', () => {
    // Defensive: production wraps PageEditor in `key={page.id}` (forced remount), but if a
    // future caller drops that key, an in-place page.id swap must still PATCH the old page.
    const { rerender, unmount } = render(<PageEditor page={{ id: 1, content: {} }} />)

    fireTyping({ pageOne: true })
    act(() => { vi.advanceTimersByTime(500) })
    expect(updatePage).not.toHaveBeenCalled()

    act(() => { rerender(<PageEditor page={{ id: 2, content: {} }} />) })

    expect(updatePage).toHaveBeenCalledTimes(1)
    expect(updatePage).toHaveBeenCalledWith(1, { content: { pageOne: true } })

    act(() => { unmount() })
  })

  it('does not double-fire when a save is in flight at unmount time', async () => {
    let resolveSave
    updatePage.mockImplementationOnce(
      () => new Promise((resolve) => { resolveSave = resolve })
    )

    const { unmount } = render(<PageEditor page={{ id: 1, content: {} }} />)

    fireTyping({ v: 'in-flight' })
    await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
    expect(updatePage).toHaveBeenCalledTimes(1)

    // unmount while the PATCH promise is unresolved — must not crash and must not re-fire
    act(() => { unmount() })
    expect(updatePage).toHaveBeenCalledTimes(1)

    await act(async () => {
      resolveSave({})
      await Promise.resolve()
    })
    expect(updatePage).toHaveBeenCalledTimes(1)
  })

  it('does not save on initial mount under StrictMode (double-effect)', () => {
    const { unmount } = render(
      <StrictMode>
        <PageEditor page={{ id: 1, content: {} }} />
      </StrictMode>
    )
    expect(updatePage).not.toHaveBeenCalled()
    act(() => { unmount() })
    expect(updatePage).not.toHaveBeenCalled()
  })
})
