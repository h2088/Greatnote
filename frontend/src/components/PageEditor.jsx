import { useEffect, useRef, useCallback, useState } from 'react'
import { Node } from '@tiptap/core'
import { useEditor, EditorContent } from '@tiptap/react'
import { BubbleMenu } from '@tiptap/react/menus'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import { updatePage, aiEditPage } from '../api/pages'
import AutoSaveIndicator from './AutoSaveIndicator'

const RemoteImage = Node.create({
  name: 'image',
  group: 'block',
  draggable: true,
  selectable: true,
  addAttributes() {
    return {
      src: { default: null },
      alt: { default: '' },
      title: { default: '' },
    }
  },
  parseHTML() {
    return [{ tag: 'img[src]' }]
  },
  renderHTML({ HTMLAttributes }) {
    return ['img', HTMLAttributes]
  },
})

const BUBBLE_BUTTONS = [
  { label: 'B', title: 'Bold (Ctrl+B)', action: (e) => e.chain().focus().toggleBold().run(), active: (e) => e.isActive('bold') },
  { label: 'I', title: 'Italic (Ctrl+I)', action: (e) => e.chain().focus().toggleItalic().run(), active: (e) => e.isActive('italic') },
  { label: 'S', title: 'Strike (Ctrl+Shift+S)', action: (e) => e.chain().focus().toggleStrike().run(), active: (e) => e.isActive('strike') },
  { divider: true },
  { label: 'H1', title: 'Heading 1 (Ctrl+Alt+1)', action: (e) => e.chain().focus().toggleHeading({ level: 1 }).run(), active: (e) => e.isActive('heading', { level: 1 }) },
  { label: 'H2', title: 'Heading 2 (Ctrl+Alt+2)', action: (e) => e.chain().focus().toggleHeading({ level: 2 }).run(), active: (e) => e.isActive('heading', { level: 2 }) },
  { label: 'H3', title: 'Heading 3 (Ctrl+Alt+3)', action: (e) => e.chain().focus().toggleHeading({ level: 3 }).run(), active: (e) => e.isActive('heading', { level: 3 }) },
  { divider: true },
  { label: 'UL', title: 'Bullet list (Ctrl+Shift+8)', action: (e) => e.chain().focus().toggleBulletList().run(), active: (e) => e.isActive('bulletList') },
  { label: '1.', title: 'Ordered list (Ctrl+Shift+7)', action: (e) => e.chain().focus().toggleOrderedList().run(), active: (e) => e.isActive('orderedList') },
  { divider: true },
  { label: 'BQ', title: 'Blockquote (Ctrl+Shift+B)', action: (e) => e.chain().focus().toggleBlockquote().run(), active: (e) => e.isActive('blockquote') },
  { label: '</>', title: 'Code block (Ctrl+Alt+C)', action: (e) => e.chain().focus().toggleCodeBlock().run(), active: (e) => e.isActive('codeBlock') },
]

const AI_ACTIONS = [
  { label: 'Improve', action: 'improve' },
  { label: 'Shorter', action: 'shorter' },
  { label: 'Longer', action: 'longer' },
  { label: 'Fix Grammar', action: 'grammar' },
  { label: 'Professional', action: 'professional' },
  { label: 'Casual', action: 'casual' },
]

const keepEditorSelection = (event) => {
  event.preventDefault()
}

export default function PageEditor({ page }) {
  const [saveStatus, setSaveStatus] = useState(null)
  const [wordCount, setWordCount] = useState(0)
  const [charCount, setCharCount] = useState(0)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiError, setAiError] = useState('')
  const [hasTextSelection, setHasTextSelection] = useState(false)
  const saveTimer = useRef(null)
  const pendingContent = useRef(null)
  const editorRef = useRef(null)

  const save = useCallback(
    async (content) => {
      setSaveStatus('saving')
      try {
        await updatePage(page.id, { content })
        setSaveStatus('saved')
        setTimeout(() => setSaveStatus(null), 2000)
      } catch {
        setSaveStatus('error')
      }
    },
    [page.id]
  )

  const flushPendingSave = useCallback(() => {
    if (saveTimer.current) {
      clearTimeout(saveTimer.current)
      saveTimer.current = null
    }
    if (pendingContent.current !== null) {
      const content = pendingContent.current
      pendingContent.current = null
      save(content)
    }
  }, [save])

  useEffect(() => () => flushPendingSave(), [flushPendingSave])

  const handleAiEdit = useCallback(
    async (action) => {
      const editor = editorRef.current
      if (!editor || aiLoading) return

      const { from, to } = editor.state.selection
      if (from === to) return

      const selectedText = editor.state.doc.textBetween(from, to)
      if (!selectedText.trim()) return

      setAiError('')
      setAiLoading(true)
      try {
        const { data } = await aiEditPage(page.id, selectedText, action)
        editor.chain().focus().insertContentAt({ from, to }, data.text).run()
      } catch (error) {
        setAiError(error?.response?.data?.detail || 'AI editing failed. Check the model/API configuration and try again.')
      } finally {
        setAiLoading(false)
      }
    },
    [page.id, aiLoading]
  )

  const handleKeyDown = useCallback((_view, event) => {
    const editor = editorRef.current
    if (!editor) return false

    const mod = event.ctrlKey || event.metaKey

    if (mod && event.altKey) {
      if (event.key === '1') {
        editor.chain().focus().toggleHeading({ level: 1 }).run()
        return true
      }
      if (event.key === '2') {
        editor.chain().focus().toggleHeading({ level: 2 }).run()
        return true
      }
      if (event.key === '3') {
        editor.chain().focus().toggleHeading({ level: 3 }).run()
        return true
      }
      if (event.key === 'c' || event.key === 'C') {
        editor.chain().focus().toggleCodeBlock().run()
        return true
      }
    }

    if (mod && event.shiftKey) {
      if (event.key === '8') {
        editor.chain().focus().toggleBulletList().run()
        return true
      }
      if (event.key === '7') {
        editor.chain().focus().toggleOrderedList().run()
        return true
      }
      if (event.key === 'b' || event.key === 'B') {
        editor.chain().focus().toggleBlockquote().run()
        return true
      }
      if (event.key === 's' || event.key === 'S') {
        editor.chain().focus().toggleStrike().run()
        return true
      }
    }

    return false
  }, [])

  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({ placeholder: 'Start writing...' }),
      RemoteImage,
    ],
    content: page.content && Object.keys(page.content).length > 0 ? page.content : '',
    editorProps: {
      handleKeyDown,
    },
    onUpdate: ({ editor: currentEditor }) => {
      const text = currentEditor.getText()
      const words = text.trim() === '' ? 0 : text.trim().split(/\s+/).length
      setWordCount(words)
      setCharCount(text.length)
      pendingContent.current = currentEditor.getJSON()
      if (saveTimer.current) clearTimeout(saveTimer.current)
      saveTimer.current = setTimeout(() => {
        saveTimer.current = null
        const content = pendingContent.current
        pendingContent.current = null
        save(content)
      }, 1000)
    },
  })

  useEffect(() => {
    editorRef.current = editor
  }, [editor])

  useEffect(() => {
    if (editor && page) {
      setAiError('')
      const newContent = page.content && Object.keys(page.content).length > 0 ? page.content : ''
      if (JSON.stringify(editor.getJSON()) !== JSON.stringify(newContent)) {
        editor.commands.setContent(newContent, false)
      }
      const text = editor.getText()
      const words = text.trim() === '' ? 0 : text.trim().split(/\s+/).length
      const chars = text.length
      const timeoutId = setTimeout(() => {
        setWordCount(words)
        setCharCount(chars)
      }, 0)
      return () => clearTimeout(timeoutId)
    }
    return undefined
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page.id])

  useEffect(() => {
    if (!editor) return undefined
    const update = () => setHasTextSelection(!editor.state.selection.empty)
    editor.on('selectionUpdate', update)
    update()
    return () => {
      editor.off('selectionUpdate', update)
    }
  }, [editor])

  return (
    <div className="relative flex h-full flex-col">
      <div className="absolute right-4 top-3 z-10">
        <AutoSaveIndicator status={saveStatus} />
      </div>

      {editor && (
        <BubbleMenu
          editor={editor}
          tippyOptions={{ duration: 150, placement: 'top' }}
          className="flex items-center gap-0.5 rounded-lg bg-gray-800 px-2 py-1.5 shadow-lg"
        >
          {BUBBLE_BUTTONS.map((btn, i) => (
            btn.divider ? (
              <div key={`div-${i}`} className="mx-0.5 h-5 w-px bg-gray-600" />
            ) : (
              <button
                key={btn.title}
                title={btn.title}
                onMouseDown={keepEditorSelection}
                onClick={() => btn.action(editor)}
                disabled={aiLoading}
                className={`rounded px-2 py-1 font-mono text-sm transition-colors ${
                  btn.active(editor)
                    ? 'bg-indigo-500 text-white'
                    : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                } ${aiLoading ? 'cursor-not-allowed opacity-50' : ''}`}
              >
                {btn.label}
              </button>
            )
          ))}

          <div className="mx-0.5 h-5 w-px bg-gray-600" />
          <span
            title={hasTextSelection ? 'AI editing options' : 'Select text to enable AI editing'}
            className={`rounded px-1 text-[10px] font-bold ${
              hasTextSelection ? 'text-emerald-400' : 'text-gray-500'
            }`}
          >
            AI
          </span>

          {hasTextSelection ? (
            <>
              {AI_ACTIONS.map((btn) => (
                <button
                  key={btn.action}
                  title={btn.label}
                  onMouseDown={keepEditorSelection}
                  onClick={() => handleAiEdit(btn.action)}
                  disabled={aiLoading}
                  className={`rounded px-2 py-1 text-xs font-medium text-emerald-300 transition-colors hover:bg-gray-700 hover:text-emerald-200 ${
                    aiLoading ? 'cursor-not-allowed opacity-50' : ''
                  }`}
                >
                  {aiLoading ? '...' : btn.label}
                </button>
              ))}
            </>
          ) : (
            <span className="px-1 text-[10px] text-gray-500">select text</span>
          )}
        </BubbleMenu>
      )}

      <div className="flex-1 overflow-y-auto px-8 py-6">
        <EditorContent editor={editor} className="tiptap prose min-h-full max-w-none" />
      </div>

      {aiError ? (
        <div className="border-t border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-800">
          {aiError}
        </div>
      ) : null}

      <div className="flex items-center justify-between border-t border-gray-100 bg-gray-50 px-4 py-2">
        <span className="text-xs text-gray-400">
          Ctrl+Alt+1-3 headings | Ctrl+Shift+7/8 lists | Ctrl+Shift+B blockquote | Ctrl+Alt+C code
        </span>
        <span className="text-xs text-gray-400">
          {wordCount.toLocaleString()} words | {charCount.toLocaleString()} chars
        </span>
      </div>
    </div>
  )
}
