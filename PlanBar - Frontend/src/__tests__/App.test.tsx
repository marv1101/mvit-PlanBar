import { render, screen, waitFor } from '@testing-library/react'
import App from '../app/App'

// Mock axios to simulate no authenticated user (GET /api/v1/users/me fails)
vi.mock('axios', () => ({
  default: {
    get: vi.fn().mockRejectedValue({ response: { status: 401 } }),
    post: vi.fn().mockRejectedValue({ response: { status: 401 } }),
    create: vi.fn().mockReturnThis(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}))

describe('App', () => {
  it('renders without crashing and shows login page when not authenticated', async () => {
    render(<App />)

    // The App should render and, after the auth check fails, show the Login form
    await waitFor(() => {
      expect(screen.getByLabelText('E-Mail')).toBeInTheDocument()
    })

    expect(screen.getByText('Anmelden')).toBeInTheDocument()
  })
})
