export default function NoteItem({ note, isSelected, onClick, onDelete }) {
  return (
    <div
      className={`note-item ${isSelected ? 'selected' : ''}`}
      onClick={onClick}
    >
      <div className="note-item-title">{note.title || 'Untitled'}</div>
      <div className="note-item-preview">
        {note.content.slice(0, 60).replace(/\n/g, ' ') || ' '}
      </div>
      <button
        className="note-item-delete"
        onClick={(e) => {
          e.stopPropagation()
          onDelete(note.id)
        }}
      >
        ×
      </button>
    </div>
  )
}
