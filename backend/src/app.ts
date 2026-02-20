import express, { Application } from 'express';
import { securityMiddleware } from './core/middleware/security';
import { requestLogger } from './core/middleware/request-logger';
import { errorHandler } from './core/middleware/error-handler';
import { healthRoutes } from './modules/health/health.routes';
import { userRoutes } from './modules/users/user.routes';
import { authRoutes } from './modules/auth/auth.routes';
import { NotFoundError } from './core/errors/app-error';

export function createApp(): Application {
  const app = express();

  app.use(express.json({ limit: '10mb' }));
  app.use(express.urlencoded({ extended: true }));

  app.use(...securityMiddleware());

  app.use(requestLogger);

  app.use('/health', healthRoutes);
  app.use('/api/v1/auth', authRoutes);
  app.use('/api/v1/users', userRoutes);

  app.all('*', (req, _res, next) => {
    next(new NotFoundError(`Route ${req.method} ${req.originalUrl}`));
  });

  app.use(errorHandler);

  return app;
}
