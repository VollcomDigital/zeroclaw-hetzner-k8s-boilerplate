import mongoose from 'mongoose';
import { env } from './env';
import { logger } from '../core/logger';

/**
 * Set up Mongoose connection event listeners once at module load.
 * Mongoose v8 has built-in automatic reconnection; we only need logging.
 */
function setupConnectionListeners(): void {
  mongoose.connection.on('connected', () => {
    logger.info('MongoDB connection established');
  });

  mongoose.connection.on('error', (err: Error) => {
    logger.error({ err }, 'MongoDB connection error');
  });

  mongoose.connection.on('disconnected', () => {
    logger.warn('MongoDB disconnected (Mongoose will auto-reconnect)');
  });
}

setupConnectionListeners();

export async function connectDatabase(): Promise<void> {
  try {
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
  return mongoose.connection.readyState === mongoose.ConnectionStates.connected;
}
