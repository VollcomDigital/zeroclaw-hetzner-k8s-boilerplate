import { Request, Response } from 'express';

jest.mock('../../../src/config/env', () => ({
  env: {
    NODE_ENV: 'test',
    PORT: 3000,
    MONGODB_URI: 'mongodb://localhost:27017/test',
    JWT_SECRET: 'test-secret-minimum-16-chars',
    JWT_EXPIRES_IN: '7d',
    CORS_ORIGIN: '*',
    LOG_LEVEL: 'silent',
  },
}));

jest.mock('../../../src/config/db');

import { liveness, readiness } from '../../../src/modules/health/health.controller';
import * as db from '../../../src/config/db';

const mockRequest = {} as Request;

function createMockResponse(): Response {
  const res = {} as Response;
  res.status = jest.fn().mockReturnValue(res);
  res.json = jest.fn().mockReturnValue(res);
  return res;
}

describe('HealthController', () => {
  describe('liveness', () => {
    it('should return 200 with alive status', () => {
      const res = createMockResponse();

      liveness(mockRequest, res);

      expect(res.status).toHaveBeenCalledWith(200);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({
          success: true,
          data: expect.objectContaining({
            status: 'alive',
          }),
        }),
      );
    });

    it('should include timestamp and uptime in response', () => {
      const res = createMockResponse();

      liveness(mockRequest, res);

      const responseData = (res.json as jest.Mock).mock.calls[0][0];
      expect(responseData.data.timestamp).toBeDefined();
      expect(typeof responseData.data.uptime).toBe('number');
    });
  });

  describe('readiness', () => {
    it('should return 200 when database is healthy', () => {
      (db.isDatabaseHealthy as jest.Mock).mockReturnValue(true);
      const res = createMockResponse();

      readiness(mockRequest, res);

      expect(res.status).toHaveBeenCalledWith(200);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({
          success: true,
          data: expect.objectContaining({
            status: 'ready',
            database: 'connected',
          }),
        }),
      );
    });

    it('should return 503 when database is unhealthy', () => {
      (db.isDatabaseHealthy as jest.Mock).mockReturnValue(false);
      const res = createMockResponse();

      readiness(mockRequest, res);

      expect(res.status).toHaveBeenCalledWith(503);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({
          success: false,
          data: expect.objectContaining({
            status: 'not_ready',
            database: 'disconnected',
          }),
        }),
      );
    });
  });
});
