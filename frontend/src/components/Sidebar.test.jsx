import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

const { mockUseAuth } = vi.hoisted(() => ({ mockUseAuth: vi.fn() }))

vi.mock('../contexts/AuthContext', () => ({ useAuth: mockUseAuth }))
vi.mock('../api/notebooks', () => ({
  getNotebooks: vi.fn(),
  getNotebook: vi.fn(),
  createNotebook: vi.fn(),
  deleteNotebook: vi.fn(),
  updateNotebook: vi.fn(),
}))
vi.mock('../api/pages', () => ({
  createPage: vi.fn(),
  deletePage: vi.fn(),
  getFavoritePages: vi.fn(),
  toggleFavoritePage: vi.fn(),
}))

const mockInvalidateQueries = vi.fn()

vi.mock('@tanstack/react-query', () => ({
  useQuery: ({ queryKey }) => {
    if (queryKey[0] === 'notebooks') {
      return { data: [{ id: 1, title: 'My Notebook' }] }
    }
    if (queryKey[0] === 'notebook') {
      return { data: { id: 1, title: 'My Notebook', pages: [
        { id: 10, title: 'Page 1', is_favorite: false, notebook: 1 },
        { id: 11, title: 'Fav Page', is_favorite: true, notebook: 1 },
      ]}}
    }
    if (queryKey[0] === 'favorite-pages') {
      return { data: [
        { id: 11, title: 'Fav Page', notebook: 1 },
      ]}
    }
    return { data: null }
  },
  useMutation: ({ onSuccess }) => ({
    mutate: () => {
      if (onSuccess) onSuccess()
    },
  }),
  useQueryClient: () => ({ invalidateQueries: mockInvalidateQueries }),
}))

import Sidebar from './Sidebar'

describe('Sidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuth.mockReturnValue({ user: { username: 'testuser' }, logout: vi.fn() })
  })

  it('renders the Favorites section when there are favorites', () => {
    render(
      <MemoryRouter>
        <Sidebar activeNotebookId="1" activePageId={null} onSelectPage={vi.fn()} />
      </MemoryRouter>
    )
    expect(screen.getByText('Favorites')).toBeInTheDocument()
    // Fav Page appears in both Favorites section and the notebook page list
    expect(screen.getAllByText('Fav Page')).toHaveLength(2)
  })

  it('renders notebook pages with correct favorite state', () => {
    render(
      <MemoryRouter>
        <Sidebar activeNotebookId="1" activePageId={null} onSelectPage={vi.fn()} />
      </MemoryRouter>
    )
    expect(screen.getByText('Page 1')).toBeInTheDocument()
    // Fav Page appears in both Favorites section and the notebook page list
    expect(screen.getAllByText('Fav Page')).toHaveLength(2)
  })

  it('calls onSelectPage when a page is clicked', () => {
    const onSelectPage = vi.fn()
    render(
      <MemoryRouter>
        <Sidebar activeNotebookId="1" activePageId={null} onSelectPage={onSelectPage} />
      </MemoryRouter>
    )
    screen.getByText('Page 1').click()
    expect(onSelectPage).toHaveBeenCalledWith(10)
  })
})
