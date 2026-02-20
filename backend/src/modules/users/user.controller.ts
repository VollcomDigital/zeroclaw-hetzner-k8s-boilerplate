import { Request, Response } from 'express';
import { userService } from './user.service';
import { updateUserSchema } from './user.validation';
import { BadRequestError } from '../../core/errors/app-error';
import { ApiResponse, PaginatedResponse } from '../../shared/types/response';
import { IUser } from './user.model';

const DEFAULT_PAGE = 1;
const DEFAULT_LIMIT = 20;
const MAX_LIMIT = 100;

type PublicUser = Omit<IUser, 'password'> & { id: string };

export async function getUsers(
  req: Request,
  res: Response<PaginatedResponse<PublicUser>>,
): Promise<void> {
  const pageParam = Array.isArray(req.query.page) ? req.query.page[0] : req.query.page;
  const limitParam = Array.isArray(req.query.limit) ? req.query.limit[0] : req.query.limit;
  const page = Math.max(Number(pageParam) || DEFAULT_PAGE, 1);
  const limit = Math.min(Math.max(Number(limitParam) || DEFAULT_LIMIT, 1), MAX_LIMIT);

  const { users, total } = await userService.findAll(page, limit);

  res.json({
    success: true,
    data: users.map((u) => u.toPublicJSON()),
    pagination: {
      page,
      limit,
      total,
      totalPages: Math.ceil(total / limit),
    },
  });
}

export async function getUser(
  req: Request,
  res: Response<ApiResponse<PublicUser>>,
): Promise<void> {
  const { id } = req.params;
  const user = await userService.findById(id);
  res.json({ success: true, data: user.toPublicJSON() });
}

export async function updateUser(
  req: Request,
  res: Response<ApiResponse<PublicUser>>,
): Promise<void> {
  const result = updateUserSchema.safeParse(req.body);
  if (!result.success) {
    throw new BadRequestError(result.error.issues.map((i) => i.message).join(', '));
  }
  const { id } = req.params;
  const user = await userService.update(id, result.data);
  res.json({ success: true, data: user.toPublicJSON() });
}

export async function deleteUser(
  req: Request,
  res: Response<ApiResponse<null>>,
): Promise<void> {
  const { id } = req.params;
  await userService.delete(id);
  res.status(204).json({ success: true, data: null });
}
