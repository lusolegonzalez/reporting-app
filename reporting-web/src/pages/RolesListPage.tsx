import { useEffect, useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';

import { listRolesRequest } from '@/api';
import { PageHeader } from '@/components/PageHeader';
import type { RoleItem } from '@/types';

export const RolesListPage = () => {
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        setError(null);
        const data = await listRolesRequest();
        setRoles(data);
      } catch (requestError) {
        if (axios.isAxiosError(requestError)) {
          setError(requestError.response?.data?.message ?? 'No se pudieron cargar roles.');
        } else {
          setError('No se pudieron cargar roles.');
        }
      }
    };

    void run();
  }, []);

  return (
    <section>
      <PageHeader
        title="Roles"
        subtitle="Listado y mantenimiento de roles."
        actions={
          <Link to="/roles/nuevo" className="button-link">
            Nuevo rol
          </Link>
        }
      />

      {error && <p className="message error">{error}</p>}

      <div className="card">
        {roles.length === 0 ? (
          <p className="empty-state">No hay roles cargados.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Descripción</th>
                <th>Permisos por reporte</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {roles.map((role) => (
                <tr key={role.id}>
                  <td>{role.nombre}</td>
                  <td>{role.descripcion || '-'}</td>
                  <td>Pendiente de integrar</td>
                  <td>
                    <Link to={`/roles/${role.id}/editar`} className="button-link secondary">
                      Editar
                    </Link>
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
