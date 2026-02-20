import pino from 'pino';

const LOG_LEVEL = process.env.LOG_LEVEL ?? 'info';

/**
 * Structured JSON logger (Pino).
 * 12-Factor: Logs to stdout as event stream.
 */
export const logger = pino({
  level: LOG_LEVEL,
  formatters: {
    level: (label) => ({ level: label }),
  },
  ...(process.env.NODE_ENV === 'development' && {
    transport: {
      target: 'pino-pretty',
      options: {
        colorize: true,
        translateTime: 'SYS:standard',
      },
    },
  }),
});
