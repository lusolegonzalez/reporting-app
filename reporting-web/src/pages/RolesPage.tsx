import { useEffect, useState } from 'react';
import axios from 'axios';

import { createRoleRequest, listRolesRequest, updateRoleRequest } from '@/api';
import { PageHeader } from '@/components/PageHeader';
import type { RoleItem } from '@/types';

export const RolesPage = () => {
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null);
  const [form, setForm] = useState({ nombre: '', descripcion: '' });
  const [newRole, setNewRole] = useState({ nombre: '', descripcion: '' });
  const [error, setError] = useState<string | null>(null);

  const loadRoles = async () => {
    const data = await listRolesRequest();
    setRoles(data);
    if (data.length > 0) {
      const selected = data.find((item) => item.id === selectedRoleId) ?? data[0];
      setSelectedRoleId(selected.id);
      setForm({ nombre: selected.nombre, descripcion: selected.descripcion ?? '' });
    }
  };

  useEffect(() => {
    void loadRoles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreate = async () => {
    try {
      await createRoleRequest({ nombre: newRole.nombre, descripcion: newRole.descripcion });
      setNewRole({ nombre: '', descripcion: '' });
      setError(null);
      await loadRoles();
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
      await updateRoleRequest(selectedRoleId, form);
      setError(null);
      await loadRoles();
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
      <PageHeader title="Roles y permisos" subtitle="CRUD básico de roles." />
      {error && <p style={{ color: '#b91c1c' }}>{error}</p>}

      <div className="card" style={{ marginBottom: '1rem' }}>
        <h3 style={{ marginTop: 0 }}>Crear rol</h3>
        <div style={{ display: 'grid', gap: '0.5rem', gridTemplateColumns: '1fr 2fr auto' }}>
          <input
            placeholder="Nombre"
            value={newRole.nombre}
            onChange={(e) => setNewRole((v) => ({ ...v, nombre: e.target.value }))}
          />
          <input
            placeholder="Descripción"
            value={newRole.descripcion}
            onChange={(e) => setNewRole((v) => ({ ...v, descripcion: e.target.value }))}
          />
          <button onClick={handleCreate}>Crear</button>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Editar rol</h3>
        <div style={{ display: 'grid', gap: '0.5rem', gridTemplateColumns: '240px 1fr', alignItems: 'start' }}>
          <select
            size={8}
            value={selectedRoleId ?? ''}
            onChange={(e) => {
              const id = Number(e.target.value);
              const role = roles.find((item) => item.id === id);
              if (!role) return;
              setSelectedRoleId(id);
              setForm({ nombre: role.nombre, descripcion: role.descripcion ?? '' });
            }}
          >
            {roles.map((role) => (
              <option key={role.id} value={role.id}>
                {role.nombre}
              </option>
            ))}
          </select>

          <div style={{ display: 'grid', gap: '0.5rem' }}>
            <input value={form.nombre} onChange={(e) => setForm((v) => ({ ...v, nombre: e.target.value }))} placeholder="Nombre" />
            <input
              value={form.descripcion}
              onChange={(e) => setForm((v) => ({ ...v, descripcion: e.target.value }))}
              placeholder="Descripción"
            />
            <button onClick={handleUpdate}>Guardar cambios</button>
          </div>
        </div>
      </div>
    </section>
  );
};
