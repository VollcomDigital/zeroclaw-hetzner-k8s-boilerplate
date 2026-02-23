import csrf from 'csurf';
import { RequestHandler } from 'express';
import { env } from '../../config/env';

const CSRF_COOKIE_NAME = 'csrf_secret';

export const csrfProtection: RequestHandler = csrf({
  cookie: {
    key: CSRF_COOKIE_NAME,
    httpOnly: true,
    secure: env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
  },
});
