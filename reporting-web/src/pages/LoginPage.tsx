import type { FormEvent } from 'react';
import { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';

export const LoginPage = () => {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('admin@reporting.local');
  const [password, setPassword] = useState('Admin123*');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (requestError) {
      if (axios.isAxiosError(requestError)) {
        setError(requestError.response?.data?.message ?? 'No se pudo iniciar sesión.');
      } else {
        setError('No se pudo iniciar sesión.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="login-container">
      <div className="login-box">
        <h1 style={{ marginTop: 0 }}>Login</h1>
        <p style={{ color: '#6b7280' }}>Ingresá con el usuario de prueba para comenzar.</p>

        <form onSubmit={handleSubmit}>
          <input type="email" placeholder="Email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Ingresando...' : 'Ingresar'}
          </button>
        </form>

        {error && <p style={{ color: '#b91c1c', marginBottom: 0 }}>{error}</p>}
      </div>
    </section>
  );
};
