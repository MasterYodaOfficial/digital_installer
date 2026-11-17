// API DecimalField(max_digits=9, decimal_places=6); keep strings in multipart/JSON.
export function formatCoordinate(value) {
  return value == null ? null : Number(value).toFixed(6);
}
