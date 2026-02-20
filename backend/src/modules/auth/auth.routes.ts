import { Router } from 'express';
import { register, login, me } from './auth.controller';
import { authenticate } from './auth.middleware';
import { asyncHandler } from '../../shared/utils/async-handler';

const router = Router();

router.post('/register', asyncHandler(register));
router.post('/login', asyncHandler(login));
router.get('/me', authenticate, asyncHandler(me));

export { router as authRoutes };
