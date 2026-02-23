import { Request, Response } from 'express';
import { authService } from './auth.service';
import { registerSchema, loginSchema } from './auth.validation';
import { BadRequestError, UnauthorizedError } from '../../core/errors/app-error';
import { ApiResponse } from '../../shared/types/response';
import { userService } from '../users/user.service';
import { AUTH_COOKIE_NAME, getAuthCookieOptions } from './auth.constants';

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
}

interface SessionPayload {
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
  res.cookie(AUTH_COOKIE_NAME, authResult.token, getAuthCookieOptions());

  res.status(201).json({
    success: true,
    data: {
      user: authResult.user,
    },
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
  res.cookie(AUTH_COOKIE_NAME, authResult.token, getAuthCookieOptions());

  res.json({
    success: true,
    data: {
      user: authResult.user,
    },
  });
}

export async function me(
  req: Request,
  res: Response<ApiResponse<SessionPayload>>,
): Promise<void> {
  if (!req.user) {
    throw new UnauthorizedError();
  }

  const user = await userService.findById(req.user.userId);

  res.json({
    success: true,
    data: {
      user: user.toPublicJSON(),
    },
  });
}

export function logout(_req: Request, res: Response<ApiResponse<null>>): void {
  const cookieOptions = getAuthCookieOptions();
  res.clearCookie(AUTH_COOKIE_NAME, {
    httpOnly: cookieOptions.httpOnly,
    secure: cookieOptions.secure,
    sameSite: cookieOptions.sameSite,
    path: cookieOptions.path,
  });

  res.status(200).json({
    success: true,
    data: null,
  });
}

export function csrfToken(
  req: Request,
  res: Response<ApiResponse<{ csrfToken: string }>>,
): void {
  const token = req.csrfToken();
  res.status(200).json({
    success: true,
    data: { csrfToken: token },
  });
}
