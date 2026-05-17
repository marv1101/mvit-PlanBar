import { createBrowserRouter } from 'react-router';
import { Layout } from './components/Layout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Home } from './pages/Home';
import { Dashboard } from './pages/Dashboard';
import { Employees } from './pages/Employees';
import { Requests } from './pages/Requests';
import { Schedule } from './pages/Schedule';
import { Roles } from './pages/Roles';
import { EmployeeView } from './pages/EmployeeView';

export const router = createBrowserRouter([
  {
    path: '/',
    Component: Layout,
    children: [
      {
        index: true,
        Component: Home,
      },
      {
        path: 'dashboard',
        element: (
          <ProtectedRoute allowedRoles={['admin']}>
            <Dashboard />
          </ProtectedRoute>
        ),
      },
      {
        path: 'employees',
        element: (
          <ProtectedRoute allowedRoles={['admin']}>
            <Employees />
          </ProtectedRoute>
        ),
      },
      {
        path: 'roles',
        element: (
          <ProtectedRoute allowedRoles={['admin']}>
            <Roles />
          </ProtectedRoute>
        ),
      },
      {
        path: 'requests',
        element: (
          <ProtectedRoute allowedRoles={['admin', 'employee']}>
            <Requests />
          </ProtectedRoute>
        ),
      },
      {
        path: 'schedule',
        element: (
          <ProtectedRoute allowedRoles={['admin']}>
            <Schedule />
          </ProtectedRoute>
        ),
      },
      {
        path: 'employee-view',
        element: (
          <ProtectedRoute allowedRoles={['admin', 'employee']}>
            <EmployeeView />
          </ProtectedRoute>
        ),
      },
    ],
  },
]);