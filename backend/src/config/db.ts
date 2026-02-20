import mongoose from 'mongoose';
import { env } from './env';
import { logger } from '../core/logger';

const RECONNECT_INTERVAL_MS = 5000;
const MAX_RECONNECT_ATTEMPTS = 10;

let reconnectAttempts = 0;

export async function connectDatabase(): Promise<void> {
  try {
    mongoose.connection.on('connected', () => {
      logger.info('MongoDB connection established');
      reconnectAttempts = 0;
    });

    mongoose.connection.on('error', (err: Error) => {
      logger.error({ err }, 'MongoDB connection error');
    });

    mongoose.connection.on('disconnected', () => {
      logger.warn('MongoDB disconnected');
      if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttempts++;
        logger.info(
          { attempt: reconnectAttempts, maxAttempts: MAX_RECONNECT_ATTEMPTS },
          'Attempting MongoDB reconnection',
        );
        setTimeout(() => {
          void connectDatabase();
        }, RECONNECT_INTERVAL_MS);
      }
    });

    await mongoose.connect(env.MONGODB_URI, {
      maxPoolSize: 10,
      serverSelectionTimeoutMS: 5000,
      socketTimeoutMS: 45000,
    });
  } catch (err) {
    logger.fatal({ err }, 'Failed to connect to MongoDB');
    throw err;
  }
}

export async function disconnectDatabase(): Promise<void> {
  await mongoose.disconnect();
  logger.info('MongoDB disconnected gracefully');
}

export function isDatabaseHealthy(): boolean {
  return mongoose.connection.readyState === 1;
}
