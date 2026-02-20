import { z } from 'zod';

/**
 * Environment schema validated at startup.
 * 12-Factor: All config via environment variables.
 */
export const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  PORT: z.coerce.number().min(1).max(65535).default(3000),
  API_PREFIX: z.string().default('/api/v1'),
  MONGODB_URI: z.string().url().or(z.string().startsWith('mongodb://')),
  MONGODB_URI_TEST: z.string().optional(),
  JWT_SECRET: z.string().min(16).default('dev-secret-min-16-chars-local-only'),
  JWT_EXPIRES_IN: z.string().default('7d'),
  RATE_LIMIT_WINDOW_MS: z.coerce.number().default(900_000),
  RATE_LIMIT_MAX: z.coerce.number().default(100),
  CORS_ORIGIN: z.string().default('http://localhost:4200'),
  LOG_LEVEL: z.enum(['trace', 'debug', 'info', 'warn', 'error']).default('info'),
});

export type Env = z.infer<typeof envSchema>;
