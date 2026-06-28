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
const Users = lazy(() => import('./pages/Users').then(m => ({ default: m.Users })));
const EmployeeView = lazy(() => import('./pages/EmployeeView').then(m => ({ default: m.EmployeeView })));
const PinboardPage = lazy(() => import('./pages/PinboardPage').then(m => ({ default: m.PinboardPage })));
const TimeAccounts = lazy(() => import('./pages/TimeAccounts').then(m => ({ default: m.TimeAccounts })));
const PrivacyPolicy = lazy(() => import('./pages/PrivacyPolicy').then(m => ({ default: m.PrivacyPolicy })));

function LazyPage({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary>
      <Suspense fallback={<FullPageSpinner />}>{children}</Suspense>
    </ErrorBoundary>
  );
}

export const router = createBrowserRouter([
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
        path: 'employees',
        element: (
          <ProtectedRoute allowedRoles={['admin']}>
            <LazyPage><Employees /></LazyPage>
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
          <ProtectedRoute allowedRoles={['admin', 'employee']}>
            <LazyPage><Requests /></LazyPage>
          </ProtectedRoute>
        ),
      },
      {
        path: 'schedule',
        element: (
          <ProtectedRoute allowedRoles={['admin']}>
            <LazyPage><Schedule /></LazyPage>
          </ProtectedRoute>
        ),
      },
      {
        path: 'employee-view',
        element: (
          <ProtectedRoute allowedRoles={['admin', 'employee']}>
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