import express from 'express';
import helmet from 'helmet';
import cors from 'cors';
import compression from 'compression';
import rateLimit from 'express-rate-limit';
import { config } from './config/index.js';
import { requestLogger } from './common/middleware/requestLogger.js';
import { errorHandler } from './common/middleware/errorHandler.js';
import { notFound } from './common/middleware/notFound.js';
import { healthRouter } from './modules/health/health.router.js';
import { userRouter } from './modules/users/user.router.js';
import { authRouter } from './modules/auth/auth.router.js';

const app = express();

app.use(helmet());
app.use(
  cors({
    origin: config.CORS_ORIGIN,
    credentials: true,
  })
);
app.use(compression());
app.use(express.json());

app.use(
  rateLimit({
    windowMs: config.RATE_LIMIT_WINDOW_MS,
    max: config.RATE_LIMIT_MAX,
    standardHeaders: true,
    legacyHeaders: false,
  })
);

app.use(requestLogger);

const prefix = config.API_PREFIX;
app.use(`${prefix}/health`, healthRouter);
app.use(`${prefix}/auth`, authRouter);
app.use(`${prefix}/users`, userRouter);

app.use(notFound);
app.use(errorHandler);

export default app;
