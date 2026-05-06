import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { getSharedWithMe, getPage } from '../api/pages'
import { useAuth } from '../contexts/AuthContext'

function ReadOnlyEditor({ content }) {
  const editor = useEditor({
    extensions: [StarterKit],
    content: content && Object.keys(content).length > 0 ? content : '',
    editable: false,
  })

  return <EditorContent editor={editor} className="tiptap prose max-w-none" />
}

function PageViewer({ page, onBack }) {
  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-3xl mx-auto px-6 py-12">
        <button
          onClick={onBack}
          className="text-sm text-indigo-600 hover:underline mb-6"
        >
          ← Back to shared pages
        </button>
        <div className="mb-2 text-xs text-gray-400 uppercase tracking-wide">
          {page.notebook_title}
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">{page.title}</h1>
        <p className="text-xs text-gray-400 mb-8">
          Last updated {new Date(page.updated_at).toLocaleDateString()}
        </p>
        <ReadOnlyEditor content={page.content} />
      </div>
    </div>
  )
}

export default function SharedWithMePage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [viewingPage, setViewingPage] = useState(null)

  const { data: pages = [], isLoading } = useQuery({
    queryKey: ['shared-with-me'],
    queryFn: () => getSharedWithMe().then((r) => r.data),
  })

  const handleViewPage = async (page) => {
    try {
      const response = await getPage(page.id)
      setViewingPage(response.data)
    } catch {
      // If the page is no longer accessible, ignore
    }
  }

  if (viewingPage) {
    return <PageViewer page={viewingPage} onBack={() => setViewingPage(null)} />
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="text-sm text-gray-500 hover:text-gray-800"
          >
            ← Back to notebooks
          </button>
        </div>
        <span className="text-sm text-gray-500">{user?.username}</span>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Shared with me</h1>

        {isLoading ? (
          <p className="text-gray-400">Loading...</p>
        ) : pages.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-4xl mb-3">📭</div>
            <p className="text-gray-500">No pages have been shared with you yet.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {pages.map((page) => (
              <button
                key={page.id}
                onClick={() => handleViewPage(page)}
                className="w-full text-left bg-white rounded-xl border border-gray-200 p-4 hover:shadow-md hover:border-indigo-200 transition-all"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-medium text-gray-900">{page.title}</h3>
                    <p className="text-sm text-gray-500 mt-0.5">
                      From <span className="text-gray-700">{page.owner}</span> · {page.notebook_title}
                    </p>
                  </div>
                  <span className="text-xs text-gray-400">
                    {page.shared_at && new Date(page.shared_at).toLocaleDateString()}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
