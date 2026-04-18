import { useEffect, useState } from 'react';
import axios from 'axios';

import { assignUserRolesRequest, createUserRequest, listRolesRequest, listUsersRequest, updateUserRequest } from '@/api';
import { PageHeader } from '@/components/PageHeader';
import type { RoleItem, UserItem } from '@/types';

export const UsersPage = () => {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [newUser, setNewUser] = useState({ nombre: '', email: '', password: '', activo: true });
  const [editUser, setEditUser] = useState({ nombre: '', email: '', password: '', activo: true });
  const [selectedRoleIds, setSelectedRoleIds] = useState<number[]>([]);

  const loadData = async () => {
    const [loadedUsers, loadedRoles] = await Promise.all([listUsersRequest(), listRolesRequest()]);
    setUsers(loadedUsers);
    setRoles(loadedRoles);

    if (loadedUsers.length > 0) {
      const selected = loadedUsers.find((user) => user.id === selectedUserId) ?? loadedUsers[0];
      setSelectedUserId(selected.id);
      setEditUser({ nombre: selected.nombre, email: selected.email, password: '', activo: selected.activo });
      const selectedRoles = loadedRoles.filter((role) => selected.roles.includes(role.nombre)).map((role) => role.id);
      setSelectedRoleIds(selectedRoles);
    }
  };

  useEffect(() => {
    const run = async () => {
      try {
        setError(null);
        await loadData();
      } catch (requestError) {
        if (axios.isAxiosError(requestError)) {
          setError(requestError.response?.data?.message ?? 'No se pudieron cargar usuarios/roles.');
        } else {
          setError('No se pudieron cargar usuarios/roles.');
        }
      }
    };

    void run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectedUser = users.find((user) => user.id === selectedUserId) ?? null;

  const handleCreate = async () => {
    try {
      setError(null);
      await createUserRequest(newUser);
      setNewUser({ nombre: '', email: '', password: '', activo: true });
      await loadData();
    } catch (requestError) {
      if (axios.isAxiosError(requestError)) {
        setError(requestError.response?.data?.message ?? 'No se pudo crear usuario.');
      } else {
        setError('No se pudo crear usuario.');
      }
    }
  };

  const handleSaveUser = async () => {
    if (!selectedUser) return;

    try {
      setError(null);
      await updateUserRequest(selectedUser.id, editUser.password ? editUser : { ...editUser, password: undefined });
      await assignUserRolesRequest(selectedUser.id, selectedRoleIds);
      await loadData();
    } catch (requestError) {
      if (axios.isAxiosError(requestError)) {
        setError(requestError.response?.data?.message ?? 'No se pudo actualizar usuario.');
      } else {
        setError('No se pudo actualizar usuario.');
      }
    }
  };

  return (
    <section>
      <PageHeader title="Usuarios" subtitle="CRUD básico y asignación de roles." />
      {error && <p style={{ color: '#b91c1c' }}>{error}</p>}

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
          <button onClick={handleCreate}>Crear</button>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Editar usuario</h3>
        <div style={{ display: 'grid', gap: '0.5rem', gridTemplateColumns: '240px 1fr', alignItems: 'start' }}>
          <select
            size={8}
            value={selectedUserId ?? ''}
            onChange={(e) => {
              const id = Number(e.target.value);
              const user = users.find((item) => item.id === id);
              if (!user) return;
              setSelectedUserId(id);
              setEditUser({ nombre: user.nombre, email: user.email, password: '', activo: user.activo });
              const roleIds = roles.filter((role) => user.roles.includes(role.nombre)).map((role) => role.id);
              setSelectedRoleIds(roleIds);
            }}
          >
            {users.map((user) => (
              <option key={user.id} value={user.id}>
                {user.nombre} ({user.email})
              </option>
            ))}
          </select>

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

              <strong>Roles</strong>
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

              <button onClick={handleSaveUser}>Guardar cambios</button>
            </div>
          )}
        </div>
      </div>
    </section>
  );
};
