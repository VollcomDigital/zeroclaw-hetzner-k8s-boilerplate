import type { Response } from 'express';

/** Standard API response envelope. */
export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: { code?: string; message: string };
}

/**
 * Sends a success JSON response.
 */
export function sendSuccess<T>(res: Response, data: T, statusCode = 200): void {
  const payload: ApiResponse<T> = { success: true, data };
  res.status(statusCode).json(payload);
}

/**
 * Sends an error JSON response.
 */
export function sendError(res: Response, message: string, statusCode = 500, code?: string): void {
  const payload: ApiResponse = {
    success: false,
    error: { code, message },
  };
  res.status(statusCode).json(payload);
}
