import type { ReactNode } from 'react';

type PageHeaderProps = {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
};

export const PageHeader = ({ title, subtitle, actions }: PageHeaderProps) => (
  <header className="page-header">
    <div>
      <h2>{title}</h2>
      {subtitle && <p>{subtitle}</p>}
    </div>
    {actions}
  </header>
);
