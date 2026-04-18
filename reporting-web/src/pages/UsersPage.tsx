import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';

import { assignUserRolesRequest, createUserRequest, listRolesRequest, listUsersRequest, updateUserRequest } from '@/api';
import { PageHeader } from '@/components/PageHeader';
import type { RoleItem, UserItem } from '@/types';

const emptyUserForm = { nombre: '', email: '', password: '', activo: true };

export const UsersPage = () => {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);

  const [newUser, setNewUser] = useState(emptyUserForm);
  const [editUser, setEditUser] = useState(emptyUserForm);
  const [selectedRoleIds, setSelectedRoleIds] = useState<number[]>([]);

  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const selectedUser = useMemo(() => users.find((user) => user.id === selectedUserId) ?? null, [selectedUserId, users]);

  const resetMessages = () => {
    setError(null);
    setSuccess(null);
  };

  const selectUser = (user: UserItem, allRoles: RoleItem[]) => {
    setSelectedUserId(user.id);
    setEditUser({ nombre: user.nombre, email: user.email, password: '', activo: user.activo });

    const roleIds = allRoles.filter((role) => user.roles.includes(role.nombre)).map((role) => role.id);
    setSelectedRoleIds(roleIds);
  };

  const loadData = async (keepSelectedId?: number | null) => {
    const [loadedUsers, loadedRoles] = await Promise.all([listUsersRequest(), listRolesRequest()]);

    setUsers(loadedUsers);
    setRoles(loadedRoles);

    if (loadedUsers.length === 0) {
      setSelectedUserId(null);
      setEditUser(emptyUserForm);
      setSelectedRoleIds([]);
      return;
    }

    const preferredUser =
      loadedUsers.find((user) => user.id === (keepSelectedId ?? selectedUserId ?? undefined)) ?? loadedUsers[0];

    selectUser(preferredUser, loadedRoles);
  };

  useEffect(() => {
    const run = async () => {
      try {
        resetMessages();
        await loadData();
      } catch (requestError) {
        if (axios.isAxiosError(requestError)) {
          setError(requestError.response?.data?.message ?? 'No se pudieron cargar usuarios y roles.');
        } else {
          setError('No se pudieron cargar usuarios y roles.');
        }
      }
    };

    void run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreate = async () => {
    try {
      resetMessages();
      await createUserRequest(newUser);
      setNewUser(emptyUserForm);
      await loadData();
      setSuccess('Usuario creado correctamente.');
    } catch (requestError) {
      if (axios.isAxiosError(requestError)) {
        setError(requestError.response?.data?.message ?? 'No se pudo crear el usuario.');
      } else {
        setError('No se pudo crear el usuario.');
      }
    }
  };

  const handleSaveUser = async () => {
    if (!selectedUser) return;

    try {
      resetMessages();

      await updateUserRequest(selectedUser.id, editUser.password ? editUser : { ...editUser, password: undefined });
      await assignUserRolesRequest(selectedUser.id, selectedRoleIds);

      await loadData(selectedUser.id);
      setSuccess('Usuario actualizado correctamente.');
    } catch (requestError) {
      if (axios.isAxiosError(requestError)) {
        setError(requestError.response?.data?.message ?? 'No se pudo actualizar el usuario.');
      } else {
        setError('No se pudo actualizar el usuario.');
      }
    }
  };

  const handleToggleActive = async (user: UserItem) => {
    try {
      resetMessages();
      await updateUserRequest(user.id, { activo: !user.activo });
      await loadData(user.id);
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
      <PageHeader title="Usuarios" subtitle="ABM de usuarios y asignación de roles." />

      {error && <p style={{ color: '#b91c1c' }}>{error}</p>}
      {success && <p style={{ color: '#047857' }}>{success}</p>}

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3 style={{ marginTop: 0 }}>Listado de usuarios</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left' }}>Nombre</th>
              <th style={{ textAlign: 'left' }}>Email</th>
              <th style={{ textAlign: 'left' }}>Estado</th>
              <th style={{ textAlign: 'left' }}>Roles</th>
              <th style={{ textAlign: 'left' }}>Acciones</th>
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
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button onClick={() => selectUser(user, roles)}>Editar</button>
                    <button onClick={() => void handleToggleActive(user)}>{user.activo ? 'Desactivar' : 'Activar'}</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3 style={{ marginTop: 0 }}>Crear usuario</h3>
        <div style={{ display: 'grid', gap: '0.5rem', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))' }}>
          <input placeholder="Nombre" value={newUser.nombre} onChange={(e) => setNewUser((v) => ({ ...v, nombre: e.target.value }))} />
          <input placeholder="Email" value={newUser.email} onChange={(e) => setNewUser((v) => ({ ...v, email: e.target.value }))} />
          <input
            placeholder="Password"
            type="password"
            value={newUser.password}
            onChange={(e) => setNewUser((v) => ({ ...v, password: e.target.value }))}
          />
          <button onClick={() => void handleCreate()}>Crear</button>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Editar usuario</h3>

        {!selectedUser && <p>No hay usuarios cargados.</p>}

        {selectedUser && (
          <div style={{ display: 'grid', gap: '0.5rem' }}>
            <input value={editUser.nombre} onChange={(e) => setEditUser((v) => ({ ...v, nombre: e.target.value }))} placeholder="Nombre" />
            <input value={editUser.email} onChange={(e) => setEditUser((v) => ({ ...v, email: e.target.value }))} placeholder="Email" />
            <input
              value={editUser.password}
              onChange={(e) => setEditUser((v) => ({ ...v, password: e.target.value }))}
              placeholder="Nuevo password (opcional)"
              type="password"
            />

            <label>
              <input
                type="checkbox"
                checked={editUser.activo}
                onChange={(e) => setEditUser((v) => ({ ...v, activo: e.target.checked }))}
                style={{ marginRight: '0.5rem' }}
              />
              Usuario activo
            </label>

            <strong>Roles asignados</strong>
            <div style={{ display: 'grid', gap: '0.3rem' }}>
              {roles.map((role) => (
                <label key={role.id}>
                  <input
                    type="checkbox"
                    checked={selectedRoleIds.includes(role.id)}
                    onChange={(e) => {
                      setSelectedRoleIds((current) =>
                        e.target.checked ? [...current, role.id] : current.filter((value) => value !== role.id),
                      );
                    }}
                    style={{ marginRight: '0.5rem' }}
                  />
                  {role.nombre}
                </label>
              ))}
            </div>

            <button onClick={() => void handleSaveUser()}>Guardar cambios</button>
          </div>
        )}
      </div>
    </section>
  );
};
