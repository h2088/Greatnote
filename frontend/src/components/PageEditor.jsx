import { useEffect, useState } from 'react'

export default function PageEditor({ page, onChange }) {
  const [title, setTitle] = useState(page.title)
  const [content, setContent] = useState(page.content)

  useEffect(() => {
    setTitle(page.title)
    setContent(page.content)
  }, [page.id])

  useEffect(() => {
    const timer = setTimeout(() => {
      onChange(page.id, { title, content })
    }, 1000)
    return () => clearTimeout(timer)
  }, [title, content])

  const handleBlur = () => {
    onChange(page.id, { title, content })
  }

  return (
    <div className="page-editor">
      <input
        className="page-title-input"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        onBlur={handleBlur}
        placeholder="Page title"
      />
      <textarea
        className="page-body-textarea"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        onBlur={handleBlur}
        placeholder="Start writing..."
      />
    </div>
  )
}
