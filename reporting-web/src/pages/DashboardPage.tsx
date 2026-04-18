import { useEffect, useState } from 'react';

import { apiClient } from '@/api/client';
import { PageHeader } from '@/components/PageHeader';
import { storage } from '@/utils/storage';

type HealthStatus = {
  service: string;
  status: string;
};

export const DashboardPage = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  const user = storage.getUser();

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await apiClient.get<HealthStatus>('/health');
        setHealth(response.data);
        setHealthError(null);
      } catch {
        setHealth(null);
        setHealthError('No se pudo conectar al backend en /api/health.');
      }
    };

    void checkHealth();
  }, []);

  return (
    <section>
      <PageHeader title="Dashboard" subtitle="Vista general del sistema (placeholder)." />
      <div className="card">
        {user && (
          <p>
            Sesión iniciada: <strong>{user.nombre}</strong> ({user.email})
          </p>
        )}
        <p>Acá se mostrarán métricas y accesos rápidos en próximas iteraciones.</p>
        {health && (
          <p>
            Backend: <strong>{health.service}</strong> - estado <strong>{health.status}</strong>
          </p>
        )}
        {healthError && <p>{healthError}</p>}
      </div>
    </section>
  );
};
