export function parseUtc(value) {
  if (!value) return null;
  const hasZone = /(Z|[+-]\d{2}:\d{2})$/.test(value);
  return new Date(hasZone ? value : `${value}Z`);
}

export function formatDateTime(value) {
  const date = parseUtc(value);
  return date ? date.toLocaleString() : "";
}