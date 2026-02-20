import type { Request, Response } from 'express';
import { sendSuccess } from '../../common/utils/response.js';
import * as userService from './user.service.js';

export async function list(_req: Request, res: Response): Promise<void> {
  const users = await userService.findAll();
  sendSuccess(res, users);
}

export async function getOne(req: Request, res: Response): Promise<void> {
  const user = await userService.findById(req.params.id);
  if (!user) {
    res
      .status(404)
      .json({ success: false, error: { code: 'NOT_FOUND', message: 'User not found' } });
    return;
  }
  sendSuccess(res, user);
}

export async function create(req: Request, res: Response): Promise<void> {
  const user = await userService.create(req.body);
  sendSuccess(res, user, 201);
}

export async function update(req: Request, res: Response): Promise<void> {
  const user = await userService.update(req.params.id, req.body);
  sendSuccess(res, user);
}

export async function remove(req: Request, res: Response): Promise<void> {
  await userService.remove(req.params.id);
  sendSuccess(res, { deleted: true }, 200);
}
