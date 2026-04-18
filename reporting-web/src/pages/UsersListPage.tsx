import { useEffect, useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';

import { listUsersRequest, updateUserRequest } from '@/api';
import { PageHeader } from '@/components/PageHeader';
import type { UserItem } from '@/types';

export const UsersListPage = () => {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadUsers = async () => {
    const data = await listUsersRequest();
    setUsers(data);
  };

  useEffect(() => {
    const run = async () => {
      try {
        setError(null);
        await loadUsers();
      } catch (requestError) {
        if (axios.isAxiosError(requestError)) {
          setError(requestError.response?.data?.message ?? 'No se pudieron cargar usuarios.');
        } else {
          setError('No se pudieron cargar usuarios.');
        }
      }
    };

    void run();
  }, []);

  const handleToggleActive = async (user: UserItem) => {
    try {
      setError(null);
      setSuccess(null);
      await updateUserRequest(user.id, { activo: !user.activo });
      await loadUsers();
      setSuccess(`Usuario ${!user.activo ? 'activado' : 'desactivado'} correctamente.`);
    } catch (requestError) {
      if (axios.isAxiosError(requestError)) {
        setError(requestError.response?.data?.message ?? 'No se pudo cambiar el estado del usuario.');
      } else {
        setError('No se pudo cambiar el estado del usuario.');
      }
    }
  };

  return (
    <section>
      <PageHeader
        title="Usuarios"
        subtitle="Listado y administración de usuarios."
        actions={
          <Link to="/usuarios/nuevo" className="button-link">
            Nuevo usuario
          </Link>
        }
      />

      {error && <p className="message error">{error}</p>}
      {success && <p className="message success">{success}</p>}

      <div className="card">
        {users.length === 0 ? (
          <p className="empty-state">No hay usuarios cargados.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Email</th>
                <th>Estado</th>
                <th>Roles</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td>{user.nombre}</td>
                  <td>{user.email}</td>
                  <td>{user.activo ? 'Activo' : 'Inactivo'}</td>
                  <td>{user.roles.length > 0 ? user.roles.join(', ') : '-'}</td>
                  <td>
                    <div className="table-actions">
                      <Link to={`/usuarios/${user.id}/editar`} className="button-link secondary">
                        Editar
                      </Link>
                      <button type="button" className="secondary" onClick={() => void handleToggleActive(user)}>
                        {user.activo ? 'Desactivar' : 'Activar'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
};
