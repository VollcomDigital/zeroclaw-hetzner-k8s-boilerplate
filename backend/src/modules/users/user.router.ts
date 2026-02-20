import { Router } from 'express';
import * as userController from './user.controller.js';

const router = Router();

router.get('/', userController.list);
router.get('/:id', userController.getOne);
router.post('/', userController.create);
router.put('/:id', userController.update);
router.delete('/:id', userController.remove);

export const userRouter = router;
