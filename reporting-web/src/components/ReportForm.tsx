import { Link } from 'react-router-dom';

type ReportFormValues = {
  codigo: string;
  nombre: string;
  descripcion: string;
  activo: boolean;
};

type ReportFormProps = {
  values: ReportFormValues;
  onChange: (updater: (current: ReportFormValues) => ReportFormValues) => void;
  onSubmit: () => void;
  isSubmitting: boolean;
  submitLabel: string;
};

export const ReportForm = ({ values, onChange, onSubmit, isSubmitting, submitLabel }: ReportFormProps) => (
  <div className="card form-card">
    <div className="form-grid">
      <label>
        Código
        <input value={values.codigo} onChange={(e) => onChange((current) => ({ ...current, codigo: e.target.value }))} />
      </label>
      <label>
        Nombre
        <input value={values.nombre} onChange={(e) => onChange((current) => ({ ...current, nombre: e.target.value }))} />
      </label>
      <label>
        Descripción breve
        <input value={values.descripcion} onChange={(e) => onChange((current) => ({ ...current, descripcion: e.target.value }))} />
      </label>
      <label className="checkbox-label">
        <input
          type="checkbox"
          checked={values.activo}
          onChange={(e) => onChange((current) => ({ ...current, activo: e.target.checked }))}
        />
        Reporte activo
      </label>
    </div>

    <div className="form-actions">
      <button type="button" onClick={onSubmit} disabled={isSubmitting}>
        {isSubmitting ? 'Guardando...' : submitLabel}
      </button>
      <Link to="/reportes" className="button-link secondary">
        Cancelar
      </Link>
    </div>
  </div>
);
