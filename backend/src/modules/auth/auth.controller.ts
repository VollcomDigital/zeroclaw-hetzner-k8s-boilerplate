import type { Request, Response } from 'express';
import { sendSuccess } from '../../common/utils/response.js';

/** Stub login — returns success. */
export async function login(_req: Request, res: Response): Promise<void> {
  sendSuccess(res, { token: 'stub-token' });
}
