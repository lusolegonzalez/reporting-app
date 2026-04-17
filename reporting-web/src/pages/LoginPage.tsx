import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';

export const LoginPage = () => {
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    login();
    navigate('/dashboard');
  };

  return (
    <section className="login-container">
      <div className="login-box">
        <h1 style={{ marginTop: 0 }}>Login</h1>
        <p style={{ color: '#6b7280' }}>Placeholder para la autenticación inicial.</p>

        <form onSubmit={handleSubmit}>
          <input type="email" placeholder="Email" required />
          <input type="password" placeholder="Password" required />
          <button type="submit">Ingresar</button>
        </form>
      </div>
    </section>
  );
};
