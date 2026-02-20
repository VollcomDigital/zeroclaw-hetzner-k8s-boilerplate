import mongoose from 'mongoose';
import { getMongoUri } from '../config/index.js';
import { logger } from '../logger/index.js';

const MONGO_OPTIONS: mongoose.ConnectOptions = {
  maxPoolSize: 10,
  serverSelectionTimeoutMS: 5000,
};

/**
 * Connects to MongoDB. Retries on failure for orchestrated environments.
 */
export async function connectDb(): Promise<void> {
  const uri = getMongoUri();
  if (!uri) {
    logger.error('MONGODB_URI is not set');
    process.exit(1);
  }

  try {
    await mongoose.connect(uri, MONGO_OPTIONS);
    logger.info('MongoDB connected');
  } catch (err) {
    logger.error({ err }, 'MongoDB connection failed');
    throw err;
  }
}

/**
 * Graceful disconnect.
 */
export async function disconnectDb(): Promise<void> {
  await mongoose.disconnect();
  logger.info('MongoDB disconnected');
}
