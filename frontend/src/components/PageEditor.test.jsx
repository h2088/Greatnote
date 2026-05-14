import { StrictMode } from 'react'
import { render, screen, act, cleanup } from '@testing-library/react'
import { vi, beforeEach, afterEach } from 'vitest'

const { mockEditor, capturedConfig } = vi.hoisted(() => ({
  mockEditor: {
    _listeners: {},
    getText: () => '',
    getJSON: () => ({}),
    isActive: () => false,
    commands: { setContent: () => {} },
    state: { selection: { empty: true, from: 0, to: 0 } },
    on(event, handler) {
      this._listeners[event] = handler
    },
    off(event) {
      delete this._listeners[event]
    },
  },
  capturedConfig: { current: null },
}))

vi.mock('@tiptap/core', () => ({
  Node: { create: () => ({}) },
}))

vi.mock('@tiptap/react', () => ({
  useEditor: (config) => {
    capturedConfig.current = config
    return mockEditor
  },
  EditorContent: () => null,
}))

vi.mock('@tiptap/react/menus', () => ({
  BubbleMenu: ({ children }) => children,
}))

vi.mock('@tiptap/starter-kit', () => ({ default: {} }))
vi.mock('@tiptap/extension-placeholder', () => ({
  default: { configure: () => ({}) },
}))

vi.mock('../api/pages', () => ({
  updatePage: vi.fn().mockResolvedValue({}),
  aiEditPage: vi.fn().mockResolvedValue({ data: { text: 'AI result' } }),
}))

import PageEditor from './PageEditor'
import { updatePage, aiEditPage } from '../api/pages'

describe('PageEditor word/character count', () => {
  beforeEach(() => {
    mockEditor._listeners = {}
    mockEditor.getText = () => ''
    mockEditor.getJSON = () => ({})
    mockEditor.state.selection = { empty: true, from: 0, to: 0 }
    capturedConfig.current = null
    updatePage.mockClear()
    aiEditPage.mockClear()
  })

  it('renders 0 words | 0 chars for an empty page', () => {
    render(<PageEditor page={{ id: 1, content: {} }} />)
    expect(screen.getByText('0 words | 0 chars')).toBeInTheDocument()
  })

  it('updates counts when the editor onUpdate fires', () => {
    render(<PageEditor page={{ id: 1, content: {} }} />)
    mockEditor.getText = () => 'hello world foo'
    act(() => {
      capturedConfig.current.onUpdate({ editor: mockEditor })
    })
    expect(screen.getByText('3 words | 15 chars')).toBeInTheDocument()
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
      screen.getByText(/342\s+words\s+\|\s+1[,.\s]?840\s+chars/)
    ).toBeInTheDocument()
  })
})

describe('PageEditor auto-save', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mockEditor._listeners = {}
    mockEditor.getText = () => ''
    mockEditor.getJSON = () => ({})
    mockEditor.state.selection = { empty: true, from: 0, to: 0 }
    capturedConfig.current = null
    updatePage.mockReset()
    updatePage.mockResolvedValue({})
    aiEditPage.mockReset()
    aiEditPage.mockResolvedValue({ data: { text: 'AI result' } })
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

    act(() => { vi.advanceTimersByTime(999) })
    expect(updatePage).not.toHaveBeenCalled()

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
    act(() => { vi.advanceTimersByTime(999) })
    expect(updatePage).not.toHaveBeenCalled()

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

  it('flushes the pending save with the old page id when page swaps in place', () => {
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

describe('PageEditor AI editing', () => {
  beforeEach(() => {
    mockEditor._listeners = {}
    mockEditor.getText = () => ''
    mockEditor.getJSON = () => ({})
    mockEditor.state.selection = { empty: true, from: 0, to: 0 }
    mockEditor.chain = () => mockEditor
    mockEditor.focus = () => mockEditor
    mockEditor.insertContentAt = () => mockEditor
    mockEditor.run = () => true
    capturedConfig.current = null
    aiEditPage.mockReset()
    aiEditPage.mockResolvedValue({ data: { text: 'improved text' } })
  })

  it('shows AI action buttons when text is selected', () => {
    mockEditor.state.selection = { empty: false, from: 1, to: 5 }
    render(<PageEditor page={{ id: 1, content: {} }} />)
    expect(screen.getByTitle('Improve')).toBeInTheDocument()
    expect(screen.getByTitle('Shorter')).toBeInTheDocument()
    expect(screen.getByTitle('Longer')).toBeInTheDocument()
  })

  it('does not show AI action buttons when no text is selected', () => {
    mockEditor.state.selection = { empty: true, from: 0, to: 0 }
    render(<PageEditor page={{ id: 1, content: {} }} />)
    expect(screen.queryByTitle('Improve')).not.toBeInTheDocument()
  })

  it('calls aiEditPage and replaces selected text on Improve click', async () => {
    mockEditor.state.selection = { empty: false, from: 1, to: 5 }
    mockEditor.state.doc = { textBetween: () => 'hello' }
    const insertContentAt = vi.fn().mockReturnThis()
    const run = vi.fn()
    mockEditor.chain = () => ({ focus: () => ({ insertContentAt, run }) })

    render(<PageEditor page={{ id: 1, content: {} }} />)

    await act(async () => {
      screen.getByTitle('Improve').click()
      await Promise.resolve()
    })

    expect(aiEditPage).toHaveBeenCalledWith(1, 'hello', 'improve')
    expect(insertContentAt).toHaveBeenCalledWith({ from: 1, to: 5 }, 'improved text')
    expect(run).toHaveBeenCalled()
  })

  it('prevents bubble menu buttons from stealing focus on mousedown', () => {
    mockEditor.state.selection = { empty: false, from: 1, to: 5 }
    render(<PageEditor page={{ id: 1, content: {} }} />)

    const improveButton = screen.getByTitle('Improve')
    const event = new MouseEvent('mousedown', { bubbles: true, cancelable: true })
    improveButton.dispatchEvent(event)

    expect(event.defaultPrevented).toBe(true)
  })

  it('shows the backend error when AI editing fails', async () => {
    mockEditor.state.selection = { empty: false, from: 1, to: 5 }
    mockEditor.state.doc = { textBetween: () => 'hello' }
    aiEditPage.mockRejectedValue({
      response: { data: { detail: 'AI editing is not configured' } },
    })

    render(<PageEditor page={{ id: 1, content: {} }} />)

    await act(async () => {
      screen.getByTitle('Improve').click()
      await Promise.resolve()
    })

    expect(screen.getByText('AI editing is not configured')).toBeInTheDocument()
  })
})
