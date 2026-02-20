import { envSchema, type Env } from './env.schema.js';
import { logger } from '../logger/index.js';

/**
 * Validates and exports environment config.
 * Fails fast at startup if validation fails.
 */
function loadConfig(): Env {
  const result = envSchema.safeParse(process.env);

  if (!result.success) {
    const msg = `Invalid environment config:\n${result.error.format()._errors.join('\n')}`;
    logger.error({ err: result.error.format() }, msg);
    process.exit(1);
  }

  return result.data;
}

/** Resolve MongoDB URI based on NODE_ENV (test uses _test DB). */
export function getMongoUri(): string {
  const env = process.env as Record<string, string>;
  if (process.env.NODE_ENV === 'test' && env.MONGODB_URI_TEST) {
    return env.MONGODB_URI_TEST;
  }
  return env.MONGODB_URI ?? '';
}

export const config = loadConfig();
