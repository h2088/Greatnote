import { render, screen, act } from '@testing-library/react'
import { vi } from 'vitest'

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

describe('PageEditor word/character count', () => {
  beforeEach(() => {
    mockEditor.getText = () => ''
    capturedConfig.current = null
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
