import { useEffect, useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import type { AuthUser } from '@/types/auth';

const navItems = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/users', label: 'Usuarios' },
  { to: '/reports', label: 'Reportes' },
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
        <h1>Reporting Web</h1>
        {user && (
          <div style={{ marginBottom: '1rem', fontSize: '0.9rem' }}>
            <div>{user.nombre}</div>
            <div style={{ color: '#6b7280' }}>{user.email}</div>
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
        <button onClick={handleLogout} style={{ marginTop: '1rem', width: '100%' }}>
          Cerrar sesión
        </button>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
};
