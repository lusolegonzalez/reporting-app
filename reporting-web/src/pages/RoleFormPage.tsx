import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { createRoleRequest, listRolesRequest, updateRoleRequest } from '@/api';
import { PageHeader } from '@/components/PageHeader';
import type { RoleItem } from '@/types';

const emptyRoleForm = { nombre: '', descripcion: '' };

export const RoleFormPage = () => {
  const { id } = useParams();
  const isEdit = Boolean(id);
  const roleId = Number(id);
  const navigate = useNavigate();

  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [form, setForm] = useState(emptyRoleForm);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(isEdit);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const selectedRole = useMemo(() => roles.find((role) => role.id === roleId) ?? null, [roles, roleId]);

  useEffect(() => {
    if (!isEdit) {
      setIsLoading(false);
      return;
    }

    const run = async () => {
      try {
        setError(null);
        const loadedRoles = await listRolesRequest();
        setRoles(loadedRoles);
        const role = loadedRoles.find((item) => item.id === roleId);

        if (!role) {
          setError('No se encontró el rol solicitado.');
          return;
        }

        setForm({ nombre: role.nombre, descripcion: role.descripcion ?? '' });
      } catch (requestError) {
        if (axios.isAxiosError(requestError)) {
          setError(requestError.response?.data?.message ?? 'No se pudo cargar el rol.');
        } else {
          setError('No se pudo cargar el rol.');
        }
      } finally {
        setIsLoading(false);
      }
    };

    void run();
  }, [isEdit, roleId]);

  const handleSubmit = async () => {
    if (!form.nombre.trim()) {
      setError('El nombre del rol es obligatorio.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);

      if (isEdit && selectedRole) {
        await updateRoleRequest(selectedRole.id, form);
      }

      if (!isEdit) {
        await createRoleRequest(form);
      }

      navigate('/roles');
    } catch (requestError) {
      if (axios.isAxiosError(requestError)) {
        setError(requestError.response?.data?.message ?? 'No se pudo guardar el rol.');
      } else {
        setError('No se pudo guardar el rol.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section>
      <PageHeader
        title={isEdit ? 'Editar rol' : 'Nuevo rol'}
        subtitle={isEdit ? 'Actualizá los datos del rol.' : 'Completá los datos para crear un rol.'}
      />

      {error && <p className="message error">{error}</p>}

      {isLoading ? (
        <div className="card">
          <p>Cargando...</p>
        </div>
      ) : (
        <div className="card form-card">
          <div className="form-grid">
            <label>
              Nombre
              <input value={form.nombre} onChange={(e) => setForm((current) => ({ ...current, nombre: e.target.value }))} />
            </label>
            <label>
              Descripción
              <input
                value={form.descripcion}
                onChange={(e) => setForm((current) => ({ ...current, descripcion: e.target.value }))}
              />
            </label>
          </div>

          <div className="form-actions">
            <button type="button" onClick={() => void handleSubmit()} disabled={isSubmitting}>
              {isSubmitting ? 'Guardando...' : 'Guardar'}
            </button>
            <Link to="/roles" className="button-link secondary">
              Cancelar
            </Link>
          </div>
        </div>
      )}
    </section>
  );
};
