import type { Request, Response, NextFunction } from 'express';
import { timingSafeEqual } from 'crypto';

// Separate dispatch authorization from the downstream upload bearerToken.
export function authorizeDispatch(req: Request, res: Response, next: NextFunction) {
  const expected = process.env.MEETINGBOT_DISPATCH_TOKEN;
  const supplied = req.get('authorization');
  if (!expected || expected.length < 32) return res.status(503).json({ error: 'Dispatch is not configured' });
  const wanted = Buffer.from(`Bearer ${expected}`);
  const actual = Buffer.from(supplied || '');
  if (wanted.length !== actual.length || !timingSafeEqual(wanted, actual)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  next();
}

export function validUserId(value: unknown): value is string {
  return typeof value === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(value);
}

export function validateJoin(req: Request, res: Response, next: NextFunction) {
  try {
    if (!validUserId(req.body?.userId) || typeof req.body?.url !== 'string') throw new Error();
    const url = new URL(req.body.url);
    const provider = req.baseUrl;
    const host = url.hostname;
    const allowed = provider === '/google' ? host === 'meet.google.com'
      : provider === '/microsoft' ? ['teams.microsoft.com', 'teams.live.com'].includes(host)
      : provider === '/zoom' && (host === 'zoom.us' || host.endsWith('.zoom.us'));
    if (!allowed || url.protocol !== 'https:' || url.username || url.password || (url.port && url.port !== '443')) throw new Error();
    next();
  } catch {
    res.status(400).json({ error: 'Invalid meeting URL or userId' });
  }
}
