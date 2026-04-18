import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { Link, useNavigate, useParams } from 'react-router-dom';

import {
  assignUserRolesRequest,
  createUserRequest,
  listRolesRequest,
  listUsersRequest,
  updateUserRequest,
} from '@/api';
import { PageHeader } from '@/components/PageHeader';
import type { RoleItem, UserItem } from '@/types';

type UserFormState = {
  nombre: string;
  email: string;
  password: string;
  activo: boolean;
};

const emptyForm: UserFormState = { nombre: '', email: '', password: '', activo: true };

export const UserFormPage = () => {
  const { id } = useParams();
  const isEdit = Boolean(id);
  const navigate = useNavigate();

  const [users, setUsers] = useState<UserItem[]>([]);
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [form, setForm] = useState<UserFormState>(emptyForm);
  const [selectedRoleIds, setSelectedRoleIds] = useState<number[]>([]);
  const [isLoading, setIsLoading] = useState(isEdit);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const userId = Number(id);

  const selectedUser = useMemo(() => users.find((user) => user.id === userId) ?? null, [users, userId]);

  useEffect(() => {
    const run = async () => {
      try {
        setError(null);
        const [loadedRoles, loadedUsers] = await Promise.all([
          listRolesRequest(),
          isEdit ? listUsersRequest() : Promise.resolve<UserItem[]>([]),
        ]);

        setRoles(loadedRoles);
        setUsers(loadedUsers);

        if (isEdit) {
          const user = loadedUsers.find((item) => item.id === userId);
          if (!user) {
            setError('No se encontró el usuario solicitado.');
            return;
          }

          setForm({ nombre: user.nombre, email: user.email, password: '', activo: user.activo });
          const roleIds = loadedRoles.filter((role) => user.roles.includes(role.nombre)).map((role) => role.id);
          setSelectedRoleIds(roleIds);
        }
      } catch (requestError) {
        if (axios.isAxiosError(requestError)) {
          setError(requestError.response?.data?.message ?? 'No se pudo cargar la información del formulario.');
        } else {
          setError('No se pudo cargar la información del formulario.');
        }
      } finally {
        setIsLoading(false);
      }
    };

    void run();
  }, [isEdit, userId]);

  const validate = () => {
    if (!form.nombre.trim()) return 'El nombre es obligatorio.';
    if (!form.email.trim()) return 'El email es obligatorio.';
    if (!isEdit && !form.password.trim()) return 'La contraseña es obligatoria para crear un usuario.';
    return null;
  };

  const handleSubmit = async () => {
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);

      if (isEdit && selectedUser) {
        await updateUserRequest(selectedUser.id, {
          nombre: form.nombre,
          email: form.email,
          activo: form.activo,
          password: form.password ? form.password : undefined,
        });
        await assignUserRolesRequest(selectedUser.id, selectedRoleIds);
      }

      if (!isEdit) {
        const created = await createUserRequest(form);
        await assignUserRolesRequest(created.id, selectedRoleIds);
      }

      navigate('/usuarios');
    } catch (requestError) {
      if (axios.isAxiosError(requestError)) {
        setError(requestError.response?.data?.message ?? 'No se pudo guardar el usuario.');
      } else {
        setError('No se pudo guardar el usuario.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section>
      <PageHeader
        title={isEdit ? 'Editar usuario' : 'Nuevo usuario'}
        subtitle={isEdit ? 'Actualizá datos y roles del usuario.' : 'Completá los datos para crear un usuario.'}
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
              Email
              <input type="email" value={form.email} onChange={(e) => setForm((current) => ({ ...current, email: e.target.value }))} />
            </label>
            <label>
              {isEdit ? 'Nueva contraseña (opcional)' : 'Contraseña'}
              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm((current) => ({ ...current, password: e.target.value }))}
              />
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={form.activo}
                onChange={(e) => setForm((current) => ({ ...current, activo: e.target.checked }))}
              />
              Usuario activo
            </label>
          </div>

          <div>
            <strong>Roles asignados</strong>
            {roles.length === 0 ? (
              <p className="empty-state">No hay roles disponibles para asignar.</p>
            ) : (
              <div className="checkbox-grid">
                {roles.map((role) => (
                  <label key={role.id} className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={selectedRoleIds.includes(role.id)}
                      onChange={(e) => {
                        setSelectedRoleIds((current) =>
                          e.target.checked ? [...current, role.id] : current.filter((value) => value !== role.id),
                        );
                      }}
                    />
                    {role.nombre}
                  </label>
                ))}
              </div>
            )}
          </div>

          <div className="form-actions">
            <button type="button" onClick={() => void handleSubmit()} disabled={isSubmitting}>
              {isSubmitting ? 'Guardando...' : 'Guardar'}
            </button>
            <Link to="/usuarios" className="button-link secondary">
              Cancelar
            </Link>
          </div>
        </div>
      )}
    </section>
  );
};
