import { Link } from 'react-router-dom';

export const NotFoundPage = () => (
  <section className="card">
    <h2>Página no encontrada</h2>
    <p>La ruta solicitada no existe.</p>
    <Link to="/dashboard">Ir al dashboard</Link>
  </section>
);
