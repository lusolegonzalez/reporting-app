const ISO_DATE_RE = /^(\d{4})-(\d{2})-(\d{2})(?:[T ].*)?$/;

/**
 * Convierte una fecha ISO (`yyyy-MM-dd` o ISO datetime) a `dd/MM/yyyy` para
 * mostrar al usuario. Parsea manualmente para evitar corrimientos de timezone
 * que ocurririan con `new Date(iso)` cuando el string no trae offset.
 *
 * Si el valor no matchea, se devuelve tal cual.
 */
export const formatDateDisplay = (value: unknown): string => {
  if (value === null || value === undefined || value === '') return '-';
  if (typeof value !== 'string') return String(value);
  const m = ISO_DATE_RE.exec(value);
  if (!m) return value;
  const [, year, month, day] = m;
  return `${day}/${month}/${year}`;
};
