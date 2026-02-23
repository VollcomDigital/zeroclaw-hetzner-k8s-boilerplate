import { Request, Response } from 'express';
import { isDatabaseHealthy } from '../../config/db';
import { ApiResponse } from '../../shared/types/response';

interface HealthPayload {
  status: string;
  timestamp: string;
  uptime: number;
  database?: string;
}

/**
 * Liveness probe: confirms the process is alive. Does not check dependencies.
 */
export function liveness(_req: Request, res: Response<ApiResponse<HealthPayload>>): void {
  res.status(200).json({
    success: true,
    data: {
      status: 'alive',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
    },
  });
}

/**
 * Readiness probe: confirms the service can serve traffic (DB connected, etc.).
 */
export function readiness(_req: Request, res: Response<ApiResponse<HealthPayload>>): void {
  const dbHealthy = isDatabaseHealthy();
  const status = dbHealthy ? 'ready' : 'not_ready';
  const statusCode = dbHealthy ? 200 : 503;

  res.status(statusCode).json({
    success: dbHealthy,
    data: {
      status,
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      database: dbHealthy ? 'connected' : 'disconnected',
    },
  });
}
