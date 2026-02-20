import app from './app.js';
import { config } from './config/index.js';
import { connectDb, disconnectDb } from './db/mongoose.js';
import { logger } from './logger/index.js';

const PORT = config.PORT;

async function start(): Promise<void> {
  await connectDb();

  const server = app.listen(PORT, () => {
    logger.info({ port: PORT, env: config.NODE_ENV }, 'Server started');
  });

  const shutdown = async (signal: string): Promise<void> => {
    logger.info({ signal }, 'Shutdown signal received');
    server.close(async () => {
      await disconnectDb();
      process.exit(0);
    });
  };

  process.on('SIGTERM', () => shutdown('SIGTERM'));
  process.on('SIGINT', () => shutdown('SIGINT'));
}

start().catch((err) => {
  logger.error({ err }, 'Failed to start server');
  process.exit(1);
});
