import type { ReactNode } from 'react';

type PageHeaderProps = {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
};

export const PageHeader = ({ title, subtitle, actions }: PageHeaderProps) => (
  <header style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
    <div>
      <h2 style={{ margin: 0 }}>{title}</h2>
      {subtitle && <p style={{ margin: '0.25rem 0 0', color: '#6b7280' }}>{subtitle}</p>}
    </div>
    {actions}
  </header>
);
