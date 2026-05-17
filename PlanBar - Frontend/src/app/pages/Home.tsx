import { Navigate } from 'react-router';
import { useAuth } from '../context/AuthContext';

export function Home() {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/" replace />;
  }

  // Redirect based on user role
  if (user.role === 'employee') {
    return <Navigate to="/employee-view" replace />;
  }

  // Admin goes to dashboard
  return <Navigate to="/dashboard" replace />;
}
