import { Router } from 'express';
import { getUsers, getUser, updateUser, deleteUser } from './user.controller';
import { authenticate, authorize } from '../auth/auth.middleware';
import { asyncHandler } from '../../shared/utils/async-handler';

const router = Router();

router.use(authenticate);

router.get('/', authorize('admin'), asyncHandler(getUsers));
router.get('/:id', asyncHandler(getUser));
router.put('/:id', asyncHandler(updateUser));
router.delete('/:id', asyncHandler(deleteUser));

export { router as userRoutes };
