import { lazy, Suspense } from 'react';
import { createBrowserRouter, Navigate } from 'react-router';
import { Layout } from './components/Layout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { FullPageSpinner } from './components/FullPageSpinner';
import { ErrorBoundary } from './components/ErrorBoundary';

const Home = lazy(() => import('./pages/Home').then(m => ({ default: m.Home })));
const Dashboard = lazy(() => import('./pages/Dashboard').then(m => ({ default: m.Dashboard })));
const Employees = lazy(() => import('./pages/Employees').then(m => ({ default: m.Employees })));
const Requests = lazy(() => import('./pages/Requests').then(m => ({ default: m.Requests })));
const Schedule = lazy(() => import('./pages/Schedule').then(m => ({ default: m.Schedule })));
const Roles = lazy(() => import('./pages/Roles').then(m => ({ default: m.Roles })));
const Teams = lazy(() => import('./pages/Teams').then(m => ({ default: m.Teams })));
const Users = lazy(() => import('./pages/Users').then(m => ({ default: m.Users })));
const EmployeeView = lazy(() => import('./pages/EmployeeView').then(m => ({ default: m.EmployeeView })));
const PinboardPage = lazy(() => import('./pages/PinboardPage').then(m => ({ default: m.PinboardPage })));
const TimeAccounts = lazy(() => import('./pages/TimeAccounts').then(m => ({ default: m.TimeAccounts })));
const PrivacyPolicy = lazy(() => import('./pages/PrivacyPolicy').then(m => ({ default: m.PrivacyPolicy })));
const SelfService = lazy(() => import('./pages/SelfService').then(m => ({ default: m.SelfService })));
const Kiosk = lazy(() => import('./pages/Kiosk').then(m => ({ default: m.Kiosk })));

function LazyPage({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary>
      <Suspense fallback={<FullPageSpinner />}>{children}</Suspense>
    </ErrorBoundary>
  );
}

export const router = createBrowserRouter([
  {
    // Standalone full-screen kiosk route — OUTSIDE the Layout route so the
    // kiosk display has no sidebar/navigation.
    path: 'kiosk',
    element: <LazyPage><Kiosk /></LazyPage>,
  },
  {
    path: '/',
    Component: Layout,
    children: [
      {
        index: true,
        element: <LazyPage><Home /></LazyPage>,
      },
      {
        path: 'dashboard',
        element: (
          <ProtectedRoute allowedRoles={['admin']}>
            <LazyPage><Dashboard /></LazyPage>
          </ProtectedRoute>
        ),
      },
      {
        path: 'roles',
        element: (
          <ProtectedRoute allowedRoles={['admin']}>
            <LazyPage><Roles /></LazyPage>
          </ProtectedRoute>
        ),
      },
      {
        path: 'teams',
        element: (
          <ProtectedRoute allowedRoles={['admin']}>
            <LazyPage><Teams /></LazyPage>
          </ProtectedRoute>
        ),
      },
      {
        path: 'employees',
        element: (
          <ProtectedRoute allowedRoles={['admin', 'planer']}>
            <LazyPage><Employees /></LazyPage>
          </ProtectedRoute>
        ),
      },
      {
        path: 'users',
        element: (
          <ProtectedRoute allowedRoles={['admin']}>
            <LazyPage><Users /></LazyPage>
          </ProtectedRoute>
        ),
      },
      {
        path: 'requests',
        element: (
          <ProtectedRoute allowedRoles={['admin', 'planer', 'employee']}>
            <LazyPage><Requests /></LazyPage>
          </ProtectedRoute>
        ),
      },
      {
        path: 'schedule',
        element: (
          <ProtectedRoute allowedRoles={['admin', 'planer']}>
            <LazyPage><Schedule /></LazyPage>
          </ProtectedRoute>
        ),
      },
      {
        path: 'employee-view',
        element: (
          <ProtectedRoute allowedRoles={['admin', 'planer', 'employee']}>
            <LazyPage><EmployeeView /></LazyPage>
          </ProtectedRoute>
        ),
      },
      {
        path: 'pinboard',
        element: (
          <ProtectedRoute allowedRoles={['admin', 'employee']}>
            <LazyPage><PinboardPage /></LazyPage>
          </ProtectedRoute>
        ),
      },
      {
        path: 'time-accounts',
        element: (
          <ProtectedRoute allowedRoles={['admin']}>
            <LazyPage><TimeAccounts /></LazyPage>
          </ProtectedRoute>
        ),
      },
      {
        path: 'self-service',
        element: (
          <ProtectedRoute allowedRoles={['admin', 'employee']}>
            <LazyPage><SelfService /></LazyPage>
          </ProtectedRoute>
        ),
      },
      {
        path: 'privacy',
        element: <LazyPage><PrivacyPolicy /></LazyPage>,
      },
      {
        path: '*',
        element: <Navigate to="/" replace />,
      },
    ],
  },
]);