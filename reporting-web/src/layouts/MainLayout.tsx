import { useEffect, useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import type { AuthUser } from '@/types/auth';

const navItems = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/usuarios', label: 'Usuarios' },
  { to: '/roles', label: 'Roles' },
  { to: '/reportes', label: 'Reportes' },
];

export const MainLayout = () => {
  const { logout, currentUser, fetchCurrentUser } = useAuth();
  const navigate = useNavigate();

  const [user, setUser] = useState<AuthUser | null>(currentUser);

  useEffect(() => {
    const syncCurrentUser = async () => {
      try {
        const me = await fetchCurrentUser();
        setUser(me);
      } catch {
        logout();
        navigate('/login');
      }
    };

    void syncCurrentUser();
  }, [fetchCurrentUser, logout, navigate]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <h1>Reporting</h1>
        {user && (
          <div className="sidebar-user">
            <div>{user.nombre}</div>
            <div>{user.email}</div>
          </div>
        )}
        <ul className="nav-list">
          {navItems.map((item) => (
            <li key={item.to}>
              <NavLink to={item.to} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
        <button type="button" className="secondary" onClick={handleLogout}>
          Cerrar sesión
        </button>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
};
