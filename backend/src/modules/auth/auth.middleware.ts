import { Request, Response, NextFunction } from 'express';
import { authService } from './auth.service';
import { ForbiddenError, UnauthorizedError } from '../../core/errors/app-error';
import { AUTH_COOKIE_NAME } from './auth.constants';

export interface AuthenticatedUser {
  userId: string;
  email: string;
  role: string;
}

declare module 'express-serve-static-core' {
  interface Request {
    user?: AuthenticatedUser;
  }
}

export function authenticate(req: Request, _res: Response, next: NextFunction): void {
  const authHeader = req.headers.authorization;
  const bearerToken = authHeader?.startsWith('Bearer ') ? authHeader.slice(7) : null;
  const cookieToken =
    req.cookies && typeof req.cookies[AUTH_COOKIE_NAME] === 'string'
      ? req.cookies[AUTH_COOKIE_NAME]
      : null;
  const token = bearerToken ?? cookieToken;

  if (!token) {
    throw new UnauthorizedError('No token provided');
  }

  req.user = authService.verifyToken(token);
  next();
}

export function authorize(...roles: string[]) {
  return (req: Request, _res: Response, next: NextFunction): void => {
    if (!req.user) {
      throw new UnauthorizedError();
    }
    if (!roles.includes(req.user.role)) {
      throw new ForbiddenError('Insufficient permissions');
    }
    next();
  };
}
