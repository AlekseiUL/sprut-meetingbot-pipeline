// Structured credentials, HTTP request/response payloads and browser content must not enter logs.
export function redact(value: unknown, seen = new WeakSet<object>()): unknown {
  if (typeof value === 'string') return value
    .replace(/https?:\/\/[^\s"'<>]+/gi, '[URL]')
    .replace(/Bearer\s+[^\s"']+/gi, 'Bearer [REDACTED]')
    .replace(/((?:token|password|secret|api[_-]?key)\s*[:=]\s*)[^\s,;]+/gi, '$1[REDACTED]');
  if (!value || typeof value !== 'object') return value;
  if (seen.has(value)) return '[Circular]';
  seen.add(value);
  if (value instanceof Error) return { name: value.name, message: '[error details omitted]' };
  if (Array.isArray(value)) return value.map(item => redact(item, seen));
  return Object.fromEntries(Object.entries(value).map(([key, item]) => [key,
    /token|authorization|cookie|password|secret|api.?key|config|request|response|headers|data/i.test(key)
      ? '[REDACTED]' : redact(item, seen)]));
}
