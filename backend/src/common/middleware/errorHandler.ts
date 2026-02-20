import type { Request, Response, NextFunction } from 'express';
import { AppError } from '../errors/AppError.js';
import { sendError } from '../utils/response.js';
import { logger } from '../../logger/index.js';

/**
 * Centralized error-handling middleware.
 * Sends standardized JSON error responses.
 */
export function errorHandler(err: Error, _req: Request, res: Response, _next: NextFunction): void {
  if (err instanceof AppError) {
    sendError(res, err.message, err.statusCode, err.code);
    return;
  }

  if (err.name === 'ValidationError') {
    const message = 'Validation failed';
    sendError(res, message, 400, 'VALIDATION_ERROR');
    return;
  }

  logger.error({ err }, 'Unhandled error');
  sendError(res, 'Internal Server Error', 500, 'INTERNAL_ERROR');
}
