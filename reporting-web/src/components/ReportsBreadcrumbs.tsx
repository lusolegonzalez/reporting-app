import { Link } from 'react-router-dom';

type BreadcrumbItem = {
  label: string;
  to?: string;
};

type ReportsBreadcrumbsProps = {
  items: BreadcrumbItem[];
};

export const ReportsBreadcrumbs = ({ items }: ReportsBreadcrumbsProps) => (
  <nav className="breadcrumbs" aria-label="Navegación de reportes">
    {items.map((item, index) => (
      <span key={`${item.label}-${index}`}>
        {item.to ? <Link to={item.to}>{item.label}</Link> : <strong>{item.label}</strong>}
        {index < items.length - 1 && <span className="separator">/</span>}
      </span>
    ))}
  </nav>
);
