import type { Request, Response, NextFunction } from 'express';
import { logger } from '../../logger/index.js';

/**
 * Request logging middleware.
 * Logs method, url, status, and duration.
 */
export function requestLogger(req: Request, res: Response, next: NextFunction): void {
  const start = Date.now();

  res.on('finish', () => {
    const duration = Date.now() - start;
    logger.info(
      {
        method: req.method,
        url: req.originalUrl,
        status: res.statusCode,
        duration,
      },
      'Request'
    );
  });

  next();
}
