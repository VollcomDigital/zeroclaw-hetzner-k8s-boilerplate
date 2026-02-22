import { Router } from 'express';
import rateLimit from 'express-rate-limit';
import { register, login, me, logout } from './auth.controller';
import { authenticate } from './auth.middleware';
import { asyncHandler } from '../../shared/utils/async-handler';

const AUTH_RATE_LIMIT_WINDOW_MS = 10 * 60 * 1000;
const AUTH_RATE_LIMIT_MAX_REQUESTS = 20;

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

const router = Router();

router.post('/register', authRateLimit, asyncHandler(register));
router.post('/login', authRateLimit, asyncHandler(login));
router.get('/me', authenticate, asyncHandler(me));
router.post('/logout', authenticate, logout);

export { router as authRoutes };
