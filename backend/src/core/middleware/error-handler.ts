import { Request, Response, NextFunction } from 'express';
import { AppError, HttpStatus, ValidationError } from '../errors/app-error';
import { logger } from '../logger';
import { ApiResponse } from '../../shared/types/response';

export function errorHandler(
  err: Error,
  _req: Request,
  res: Response<ApiResponse<null>>,
  _next: NextFunction,
): void {
  if (err instanceof ValidationError) {
    res.status(err.statusCode).json({
      success: false,
      data: null,
      error: {
        message: err.message,
        details: err.errors,
      },
    });
    return;
  }

  if (err instanceof AppError) {
    if (!err.isOperational) {
      logger.error({ err }, 'Non-operational error encountered');
    }

    res.status(err.statusCode).json({
      success: false,
      data: null,
      error: { message: err.message },
    });
    return;
  }

  logger.error({ err }, 'Unhandled error');

  res.status(HttpStatus.INTERNAL_SERVER_ERROR).json({
    success: false,
    data: null,
    error: {
      message:
        process.env.NODE_ENV === 'production'
          ? 'An unexpected error occurred'
          : err.message,
    },
  });
}
