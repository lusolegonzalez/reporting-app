import { Navigate, createBrowserRouter } from 'react-router-dom';
import { MainLayout } from '@/layouts/MainLayout';
import { DashboardPage } from '@/pages/DashboardPage';
import { LoginPage } from '@/pages/LoginPage';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { ReportsPage } from '@/pages/ReportsPage';
import { RoleFormPage } from '@/pages/RoleFormPage';
import { RolesListPage } from '@/pages/RolesListPage';
import { UserFormPage } from '@/pages/UserFormPage';
import { UsersListPage } from '@/pages/UsersListPage';
import { PrivateRoute } from './PrivateRoute';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    element: <PrivateRoute />,
    children: [
      {
        element: <MainLayout />,
        children: [
          { index: true, element: <Navigate to="/dashboard" replace /> },
          { path: '/dashboard', element: <DashboardPage /> },
          { path: '/users', element: <Navigate to="/usuarios" replace /> },
          { path: '/usuarios', element: <UsersListPage /> },
          { path: '/usuarios/nuevo', element: <UserFormPage /> },
          { path: '/usuarios/:id/editar', element: <UserFormPage /> },
          { path: '/roles', element: <RolesListPage /> },
          { path: '/roles/nuevo', element: <RoleFormPage /> },
          { path: '/roles/:id/editar', element: <RoleFormPage /> },
          { path: '/reports', element: <ReportsPage /> },
        ],
      },
    ],
  },
  {
    path: '*',
    element: <NotFoundPage />,
  },
]);
