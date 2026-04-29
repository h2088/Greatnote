import { useState } from 'react'
import NoteItem from './NoteItem.jsx'

export default function NoteList({ notes, selectedNoteId, onSelect, onDelete, onCreate }) {
  const [search, setSearch] = useState('')

  const filtered = search
    ? notes.filter(n =>
        n.title.toLowerCase().includes(search.toLowerCase()) ||
        n.content.toLowerCase().includes(search.toLowerCase())
      )
    : notes

  return (
    <div className="note-list">
      <div className="note-list-header">
        <input
          type="text"
          className="search-input"
          placeholder="Search notes..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <button className="new-note-btn" onClick={onCreate}>
          + New
        </button>
      </div>
      <div className="note-list-items">
        {filtered.map(note => (
          <NoteItem
            key={note.id}
            note={note}
            isSelected={note.id === selectedNoteId}
            onClick={() => onSelect(note.id)}
            onDelete={onDelete}
          />
        ))}
        {filtered.length === 0 && (
          <div className="empty-state">No notes found</div>
        )}
      </div>
    </div>
  )
}
