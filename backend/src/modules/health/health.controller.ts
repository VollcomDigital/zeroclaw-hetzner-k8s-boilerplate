import type { Request, Response } from 'express';
import { sendSuccess } from '../../common/utils/response.js';
import { getLiveness, getReadiness } from './health.service.js';

export async function liveness(_req: Request, res: Response): Promise<void> {
  const data = getLiveness();
  sendSuccess(res, data);
}

export async function readiness(_req: Request, res: Response): Promise<void> {
  const data = await getReadiness();
  const statusCode = data.status === 'healthy' ? 200 : 503;
  sendSuccess(res, data, statusCode);
}
