import { useEffect, useRef, useState } from 'react'

export default function NoteEditor({ note, onChange }) {
  const [title, setTitle] = useState(note.title)
  const [content, setContent] = useState(note.content)
  const titleRef = useRef(null)

  useEffect(() => {
    setTitle(note.title)
    setContent(note.content)
  }, [note.id])

  useEffect(() => {
    const timer = setTimeout(() => {
      onChange(note.id, { title, content })
    }, 1000)
    return () => clearTimeout(timer)
  }, [title, content])

  const handleBlur = () => {
    onChange(note.id, { title, content })
  }

  return (
    <div className="note-editor">
      <input
        ref={titleRef}
        className="note-title-input"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        onBlur={handleBlur}
        placeholder="Note title"
      />
      <textarea
        className="note-body-textarea"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        onBlur={handleBlur}
        placeholder="Start writing..."
      />
    </div>
  )
}
