import { Router } from 'express';
import rateLimit from 'express-rate-limit';
import { register, login, me, logout, csrfToken } from './auth.controller';
import { authenticate } from './auth.middleware';
import { asyncHandler } from '../../shared/utils/async-handler';

const AUTH_RATE_LIMIT_WINDOW_MS = 10 * 60 * 1000;
const AUTH_RATE_LIMIT_MAX_REQUESTS = 20;
const AUTH_SESSION_RATE_LIMIT_WINDOW_MS = 10 * 60 * 1000;
const AUTH_SESSION_RATE_LIMIT_MAX_REQUESTS = 120;

const authRateLimit = rateLimit({
  windowMs: AUTH_RATE_LIMIT_WINDOW_MS,
  max: AUTH_RATE_LIMIT_MAX_REQUESTS,
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    success: false,
    data: null,
    error: {
      message: 'Too many authentication attempts, please try again later',
    },
  },
});

const authSessionRateLimit = rateLimit({
  windowMs: AUTH_SESSION_RATE_LIMIT_WINDOW_MS,
  max: AUTH_SESSION_RATE_LIMIT_MAX_REQUESTS,
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    success: false,
    data: null,
    error: {
      message: 'Too many authenticated session requests, please try again later',
    },
  },
});

const router = Router();

router.get('/csrf-token', authSessionRateLimit, csrfToken);
router.post('/register', authRateLimit, asyncHandler(register));
router.post('/login', authRateLimit, asyncHandler(login));
router.get('/me', authSessionRateLimit, authenticate, asyncHandler(me));
router.post('/logout', authSessionRateLimit, authenticate, logout);

export { router as authRoutes };
