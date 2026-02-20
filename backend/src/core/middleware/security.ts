import helmet from 'helmet';
import cors from 'cors';
import rateLimit from 'express-rate-limit';
import { RequestHandler } from 'express';
import { env } from '../../config/env';

const RATE_LIMIT_WINDOW_MS = 15 * 60 * 1000;
const RATE_LIMIT_MAX_REQUESTS = 100;

export function securityMiddleware(): RequestHandler[] {
  return [
    helmet() as RequestHandler,

    cors({
      origin: env.CORS_ORIGIN,
      credentials: true,
      methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
      allowedHeaders: ['Content-Type', 'Authorization'],
    }),

    rateLimit({
      windowMs: RATE_LIMIT_WINDOW_MS,
      max: RATE_LIMIT_MAX_REQUESTS,
      standardHeaders: true,
      legacyHeaders: false,
      message: { success: false, data: null, error: { message: 'Too many requests, please try again later' } },
    }),
  ];
}
