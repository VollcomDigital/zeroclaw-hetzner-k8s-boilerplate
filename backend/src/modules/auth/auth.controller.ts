import { Request, Response } from 'express';
import { authService } from './auth.service';
import { registerSchema, loginSchema } from './auth.validation';
import { BadRequestError } from '../../core/errors/app-error';
import { ApiResponse } from '../../shared/types/response';

interface AuthPayload {
  user: {
    id: string;
    email: string;
    firstName: string;
    lastName: string;
    role: string;
    isActive: boolean;
    createdAt: Date;
    updatedAt: Date;
  };
  token: string;
}

export async function register(
  req: Request,
  res: Response<ApiResponse<AuthPayload>>,
): Promise<void> {
  const result = registerSchema.safeParse(req.body);
  if (!result.success) {
    throw new BadRequestError(result.error.issues.map((i) => i.message).join(', '));
  }

  const authResult = await authService.register(result.data);

  res.status(201).json({
    success: true,
    data: authResult,
  });
}

export async function login(
  req: Request,
  res: Response<ApiResponse<AuthPayload>>,
): Promise<void> {
  const result = loginSchema.safeParse(req.body);
  if (!result.success) {
    throw new BadRequestError(result.error.issues.map((i) => i.message).join(', '));
  }

  const authResult = await authService.login(result.data);

  res.json({
    success: true,
    data: authResult,
  });
}

export async function me(
  req: Request,
  res: Response<ApiResponse<{ userId: string; email: string; role: string }>>,
): Promise<void> {
  res.json({
    success: true,
    data: req.user!,
  });
}
