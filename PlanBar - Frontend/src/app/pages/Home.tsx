import { Navigate } from 'react-router';
import { useAuth } from '../context/AuthContext';

export function Home() {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/" replace />;
  }

  // Redirect based on user role
  if (user.role === 'kiosk') {
    return <Navigate to="/kiosk" replace />;
  }
  if (user.role === 'employee') {
    return <Navigate to="/employee-view" replace />;
  }
  if (user.role === 'planer') {
    return <Navigate to="/schedule" replace />;
  }

  // Admin goes to dashboard
  return <Navigate to="/dashboard" replace />;
}
