import { getLiveness, getReadiness } from '../src/modules/health/health.service';

describe('Health Service', () => {
  describe('getLiveness', () => {
    it('returns healthy status with uptime', () => {
      const result = getLiveness();
      expect(result.status).toBe('healthy');
      expect(result.timestamp).toBeDefined();
      expect(typeof result.uptime).toBe('number');
    });
  });

  describe('getReadiness', () => {
    it('returns health status with mongodb state', async () => {
      const result = await getReadiness();
      expect(['healthy', 'unhealthy']).toContain(result.status);
      expect(result.mongodb).toBeDefined();
    });
  });
});
