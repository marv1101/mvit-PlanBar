import { Navigate } from 'react-router';
import { useAuth } from '../context/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles: ('admin' | 'employee')[];
}

export function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/" replace />;
  }

  if (!allowedRoles.includes(user.role)) {
    // Redirect to first allowed page based on role
    if (user.role === 'employee') {
      return <Navigate to="/employee-view" replace />;
    }
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
