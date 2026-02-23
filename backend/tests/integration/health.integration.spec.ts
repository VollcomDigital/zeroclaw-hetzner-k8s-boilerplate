import request from 'supertest';
import { createApp } from '../../src/app';
import { Application } from 'express';

jest.mock('../../src/config/env', () => ({
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

jest.mock('../../src/config/db', () => ({
  isDatabaseHealthy: jest.fn().mockReturnValue(true),
  connectDatabase: jest.fn(),
  disconnectDatabase: jest.fn(),
}));

describe('Health Endpoints (Integration)', () => {
  let app: Application;

  beforeAll(() => {
    app = createApp();
  });

  describe('GET /health/liveness', () => {
    it('should return 200 with alive status', async () => {
      const response = await request(app).get('/health/liveness');

      expect(response.status).toBe(200);
      expect(response.body.success).toBe(true);
      expect(response.body.data.status).toBe('alive');
    });
  });

  describe('GET /health/readiness', () => {
    it('should return 200 when database is healthy', async () => {
      const response = await request(app).get('/health/readiness');

      expect(response.status).toBe(200);
      expect(response.body.success).toBe(true);
      expect(response.body.data.status).toBe('ready');
    });
  });

  describe('GET /nonexistent', () => {
    it('should return 404 for unknown routes', async () => {
      const response = await request(app).get('/api/v1/nonexistent');

      expect(response.status).toBe(404);
      expect(response.body.success).toBe(false);
    });
  });
});
