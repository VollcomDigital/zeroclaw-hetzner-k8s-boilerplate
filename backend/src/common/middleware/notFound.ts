import type { Request, Response } from 'express';
import { sendError } from '../utils/response.js';

/**
 * 404 handler for unmatched routes.
 */
export function notFound(_req: Request, res: Response): void {
  sendError(res, 'Not Found', 404, 'NOT_FOUND');
}
