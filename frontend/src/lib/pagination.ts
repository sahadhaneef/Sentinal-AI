/** Cursor tokens are opaque. Store previous tokens in the URL, never subtract offsets. */
export function pageParams(
  params: URLSearchParams,
  direction: 'next' | 'previous',
  nextCursor?: string | null,
) {
  const next = new URLSearchParams(params),
    trail = params.getAll('from');
  if (direction === 'next' && nextCursor) {
    trail.push(params.get('cursor') || '');
    next.set('cursor', nextCursor);
  } else if (direction === 'previous' && trail.length) {
    const previous = trail.pop();
    if (previous) next.set('cursor', previous);
    else next.delete('cursor');
  }
  next.delete('from');
  trail.forEach((token) => next.append('from', token));
  return next;
}
export function filterParams(params: URLSearchParams, key: string, value: string) {
  const next = new URLSearchParams(params);
  if (value) next.set(key, value);
  else next.delete(key);
  next.delete('cursor');
  next.delete('from');
  return next;
}
