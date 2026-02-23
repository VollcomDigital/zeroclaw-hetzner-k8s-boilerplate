import mongoose from 'mongoose';
import { env } from './env';
import { logger } from '../core/logger';

const MONGO_MAX_POOL_SIZE = 10;
const MONGO_SERVER_SELECTION_TIMEOUT_MS = 5000;
const MONGO_SOCKET_TIMEOUT_MS = 45000;

let listenersInitialized = false;

function initializeConnectionListeners(): void {
  if (listenersInitialized) {
    return;
  }

  listenersInitialized = true;

  mongoose.connection.on('connected', () => {
    logger.info('MongoDB connection established');
  });

  mongoose.connection.on('error', (err: Error) => {
    logger.error({ err }, 'MongoDB connection error');
  });

  mongoose.connection.on('disconnected', () => {
    logger.warn('MongoDB disconnected');
    logger.info('Mongoose will attempt to reconnect automatically');
  });
}

export async function connectDatabase(): Promise<void> {
  initializeConnectionListeners();

  if (mongoose.connection.readyState === mongoose.ConnectionStates.connected) {
    logger.debug('MongoDB connection already established');
    return;
  }

  if (mongoose.connection.readyState === mongoose.ConnectionStates.connecting) {
    logger.debug('MongoDB connection already in progress');
    return;
  }

  try {
    await mongoose.connect(env.MONGODB_URI, {
      maxPoolSize: MONGO_MAX_POOL_SIZE,
      serverSelectionTimeoutMS: MONGO_SERVER_SELECTION_TIMEOUT_MS,
      socketTimeoutMS: MONGO_SOCKET_TIMEOUT_MS,
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
