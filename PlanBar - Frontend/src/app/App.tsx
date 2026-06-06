import { useEffect } from 'react';
import { RouterProvider } from 'react-router';
import { router } from './routes';
import { AppProvider } from './context/AppContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { TeamProvider } from './context/TeamContext';
import { QueryProvider } from './providers/QueryProvider';
import { Toaster } from './components/ui/sonner';
import { Login } from './pages/Login';
import { ChangePasswordDialog } from './components/ChangePasswordDialog';
import { ErrorBoundary } from './components/ErrorBoundary';
import { initPushState } from './services/pushService';
import { CookieConsent } from '../components/CookieConsent';

function AppContent() {
  const { user, isLoading, mustChangePassword } = useAuth();

  useEffect(() => {
    if (user) {
      initPushState();
    }
  }, [user]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Laden...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Login />;
  }

  return (
    <QueryProvider>
      <TeamProvider>
        <AppProvider>
          {mustChangePassword && <ChangePasswordDialog />}
          <RouterProvider router={router} />
          <Toaster />
          <CookieConsent />
        </AppProvider>
      </TeamProvider>
    </QueryProvider>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ErrorBoundary>
  );
}
