import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';

import { createRoleRequest, listRolesRequest, updateRoleRequest } from '@/api';
import { PageHeader } from '@/components/PageHeader';
import type { RoleItem } from '@/types';

const emptyRoleForm = { nombre: '', descripcion: '' };

export const RolesPage = () => {
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null);
  const [form, setForm] = useState(emptyRoleForm);
  const [newRole, setNewRole] = useState(emptyRoleForm);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const selectedRole = useMemo(() => roles.find((role) => role.id === selectedRoleId) ?? null, [roles, selectedRoleId]);

  const resetMessages = () => {
    setError(null);
    setSuccess(null);
  };

  const selectRole = (role: RoleItem) => {
    setSelectedRoleId(role.id);
    setForm({ nombre: role.nombre, descripcion: role.descripcion ?? '' });
  };

  const loadRoles = async (keepSelectedId?: number | null) => {
    const data = await listRolesRequest();
    setRoles(data);

    if (data.length === 0) {
      setSelectedRoleId(null);
      setForm(emptyRoleForm);
      return;
    }

    const selected = data.find((item) => item.id === (keepSelectedId ?? selectedRoleId ?? undefined)) ?? data[0];
    selectRole(selected);
  };

  useEffect(() => {
    const run = async () => {
      try {
        resetMessages();
        await loadRoles();
      } catch (requestError) {
        if (axios.isAxiosError(requestError)) {
          setError(requestError.response?.data?.message ?? 'No se pudieron cargar roles.');
        } else {
          setError('No se pudieron cargar roles.');
        }
      }
    };

    void run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreate = async () => {
    try {
      resetMessages();
      await createRoleRequest({ nombre: newRole.nombre, descripcion: newRole.descripcion });
      setNewRole(emptyRoleForm);
      await loadRoles();
      setSuccess('Rol creado correctamente.');
    } catch (requestError) {
      if (axios.isAxiosError(requestError)) {
        setError(requestError.response?.data?.message ?? 'No se pudo crear rol.');
      } else {
        setError('No se pudo crear rol.');
      }
    }
  };

  const handleUpdate = async () => {
    if (!selectedRoleId) return;

    try {
      resetMessages();
      await updateRoleRequest(selectedRoleId, form);
      await loadRoles(selectedRoleId);
      setSuccess('Rol actualizado correctamente.');
    } catch (requestError) {
      if (axios.isAxiosError(requestError)) {
        setError(requestError.response?.data?.message ?? 'No se pudo editar rol.');
      } else {
        setError('No se pudo editar rol.');
      }
    }
  };

  return (
    <section>
      <PageHeader title="Roles" subtitle="ABM de roles listo para vincular permisos por reporte." />

      {error && <p style={{ color: '#b91c1c' }}>{error}</p>}
      {success && <p style={{ color: '#047857' }}>{success}</p>}

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3 style={{ marginTop: 0 }}>Listado de roles</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left' }}>Nombre</th>
              <th style={{ textAlign: 'left' }}>Descripción</th>
              <th style={{ textAlign: 'left' }}>Permisos por reporte</th>
              <th style={{ textAlign: 'left' }}>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {roles.map((role) => (
              <tr key={role.id}>
                <td>{role.nombre}</td>
                <td>{role.descripcion || '-'}</td>
                <td>Pendiente de integrar</td>
                <td>
                  <button onClick={() => selectRole(role)}>Editar</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3 style={{ marginTop: 0 }}>Crear rol</h3>
        <div style={{ display: 'grid', gap: '0.5rem', gridTemplateColumns: '1fr 2fr auto' }}>
          <input placeholder="Nombre" value={newRole.nombre} onChange={(e) => setNewRole((v) => ({ ...v, nombre: e.target.value }))} />
          <input
            placeholder="Descripción"
            value={newRole.descripcion}
            onChange={(e) => setNewRole((v) => ({ ...v, descripcion: e.target.value }))}
          />
          <button onClick={() => void handleCreate()}>Crear</button>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Editar rol</h3>

        {!selectedRole && <p>No hay roles cargados.</p>}

        {selectedRole && (
          <div style={{ display: 'grid', gap: '0.5rem' }}>
            <input value={form.nombre} onChange={(e) => setForm((v) => ({ ...v, nombre: e.target.value }))} placeholder="Nombre" />
            <input
              value={form.descripcion}
              onChange={(e) => setForm((v) => ({ ...v, descripcion: e.target.value }))}
              placeholder="Descripción"
            />
            <button onClick={() => void handleUpdate()}>Guardar cambios</button>
          </div>
        )}
      </div>
    </section>
  );
};
