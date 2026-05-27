import React from 'react';
import { Link, Outlet, useLocation } from 'react-router';
import { Calendar, Users, ClipboardList, LayoutDashboard, UserCog, Eye, LogOut, User } from 'lucide-react';
import { cn } from './ui/utils';
import { useAuth } from '../context/AuthContext';
import { Button } from './ui/button';

export function Layout() {
  const location = useLocation();
  const { user, logout } = useAuth();

  const allNavItems = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, roles: ['admin'] },
    { path: '/employees', label: 'Mitarbeiter', icon: Users, roles: ['admin'] },
    { path: '/roles', label: 'Rollen', icon: UserCog, roles: ['admin'] },
    { path: '/requests', label: 'Wünsche', icon: ClipboardList, roles: ['admin', 'employee'] },
    { path: '/schedule', label: 'Schichtplan', icon: Calendar, roles: ['admin'] },
    { path: '/employee-view', label: 'Mitarbeiteransicht', icon: Eye, roles: ['admin', 'employee'] },
  ];

  // Filter navigation items based on user role
  const navItems = allNavItems.filter(item =>
    user && item.roles.includes(user.role)
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Calendar className="h-8 w-8 text-blue-600" />
              <h1 className="font-semibold text-xl">MVIT PlanBar</h1>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 text-sm text-gray-700">
                <User className="h-4 w-4" />
                <span>{user?.name}</span>
                <span className="text-xs text-gray-500">
                  ({user?.role === 'admin' ? 'Administrator' : 'Mitarbeiter'})
                </span>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={logout}
              >
                <LogOut className="h-4 w-4 mr-2" />
                Abmelden
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-6">
        <div className="flex gap-6">
          <nav className="w-64 flex-shrink-0">
            <div className="bg-white rounded-lg shadow-sm p-2">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={cn(
                      'flex items-center gap-3 px-4 py-3 rounded-md transition-colors',
                      isActive
                        ? 'bg-blue-50 text-blue-700'
                        : 'text-gray-700 hover:bg-gray-50'
                    )}
                  >
                    <Icon className="h-5 w-5" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </nav>

          <main className="flex-1">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}