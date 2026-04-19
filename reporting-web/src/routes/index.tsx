import { Navigate, createBrowserRouter } from 'react-router-dom';
import { MainLayout } from '@/layouts/MainLayout';
import { DashboardPage } from '@/pages/DashboardPage';
import { LoginPage } from '@/pages/LoginPage';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { ReportDetailPage } from '@/pages/ReportDetailPage';
import { ReportFormPage } from '@/pages/ReportFormPage';
import { ReportsListPage } from '@/pages/ReportsListPage';
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
          { path: '/reports', element: <Navigate to='/reportes' replace /> },
          { path: '/reportes', element: <ReportsListPage /> },
          { path: '/reportes/nuevo', element: <ReportFormPage /> },
          { path: '/reportes/:id/editar', element: <ReportFormPage /> },
          { path: '/reportes/:id', element: <ReportDetailPage /> },
        ],
      },
    ],
  },
  {
    path: '*',
    element: <NotFoundPage />,
  },
]);
