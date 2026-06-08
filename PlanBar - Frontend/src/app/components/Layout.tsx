import React, { useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router';
import { Calendar, Users, ClipboardList, LayoutDashboard, UserCog, Eye, LogOut, User, UserPlus, Menu, X, MessageSquare } from 'lucide-react';
import { cn } from './ui/utils';
import { useAuth } from '../context/AuthContext';
import { Button } from './ui/button';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from './ui/sheet';
import { useIsMobile } from './ui/use-mobile';

function NavContent({ navItems, onNavigate }: { navItems: { path: string; label: string; icon: React.ComponentType; }[]; onNavigate?: () => void }) {
  const location = useLocation();
  return (
    <div className="bg-white rounded-lg shadow-sm p-2">
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = location.pathname === item.path;
        return (
          <Link
            key={item.path}
            to={item.path}
            onClick={onNavigate}
            className={cn(
              'flex items-center gap-3 px-4 py-3 rounded-md transition-colors',
              isActive
                ? 'bg-blue-50 text-blue-700'
                : 'text-gray-700 hover:bg-gray-50'
            )}
            aria-current={isActive ? 'page' : undefined}
          >
            <Icon className="h-5 w-5" />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </div>
  );
}

export function Layout() {
  const { user, logout } = useAuth();
  const isMobile = useIsMobile();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const allNavItems = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, roles: ['admin'] },
    { path: '/employees', label: 'Mitarbeiter', icon: Users, roles: ['admin'] },
    { path: '/roles', label: 'Rollen', icon: UserCog, roles: ['admin'] },
    { path: '/users', label: 'Benutzer', icon: UserPlus, roles: ['admin'] },
    { path: '/requests', label: 'Wünsche', icon: ClipboardList, roles: ['admin', 'employee'] },
    { path: '/schedule', label: 'Schichtplan', icon: Calendar, roles: ['admin'] },
    { path: '/employee-view', label: 'Mitarbeiteransicht', icon: Eye, roles: ['admin', 'employee'] },
    { path: '/pinboard', label: 'Pinnwand', icon: MessageSquare, roles: ['admin', 'employee'] },
  ];

  const navItems = allNavItems.filter(item =>
    user && item.roles.includes(user.role)
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3 min-w-0">
              {isMobile && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setSidebarOpen(true)}
                  aria-label="Navigation öffnen"
                >
                  <Menu className="h-6 w-6" />
                </Button>
              )}
              <Calendar className="h-8 w-8 text-blue-600 shrink-0" />
              <h1 className="font-semibold text-xl truncate">MVIT PlanBar</h1>
            </div>
            <div className="flex items-center gap-2 sm:gap-4 shrink-0">
              <div className="hidden sm:flex items-center gap-2 text-sm text-gray-700">
                <User className="h-4 w-4" />
                <span className="truncate max-w-[120px]">{user?.name}</span>
                <span className="text-xs text-gray-500">
                  ({user?.role === 'admin' ? 'Administrator' : 'Mitarbeiter'})
                </span>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={logout}
              >
                <LogOut className="h-4 w-4 sm:mr-2" />
                <span className="hidden sm:inline">Abmelden</span>
              </Button>
            </div>
          </div>
        </div>
      </header>

      {isMobile && (
        <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
          <SheetContent side="left" className="w-72 p-0">
            <SheetHeader className="border-b px-4 py-4">
              <div className="flex items-center justify-between">
                <SheetTitle className="flex items-center gap-3">
                  <Calendar className="h-7 w-7 text-blue-600" />
                  <span className="text-lg font-semibold">MVIT PlanBar</span>
                </SheetTitle>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setSidebarOpen(false)}
                  aria-label="Navigation schließen"
                >
                  <X className="h-5 w-5" />
                </Button>
              </div>
            </SheetHeader>
            <div className="p-4">
              <NavContent navItems={navItems} onNavigate={() => setSidebarOpen(false)} />
            </div>
          </SheetContent>
        </Sheet>
      )}

      <div className="container mx-auto px-4 py-6">
        <div className="flex gap-6">
          <nav className="hidden md:block w-64 flex-shrink-0">
            <NavContent navItems={navItems} />
          </nav>

          <main className="flex-1 min-w-0">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}