import mongoose from 'mongoose';

export interface HealthStatus {
  status: 'healthy' | 'unhealthy';
  timestamp: string;
  uptime: number;
  mongodb?: 'connected' | 'disconnected';
}

/**
 * Liveness: process is alive.
 */
export function getLiveness(): HealthStatus {
  return {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
  };
}

/**
 * Readiness: app and dependencies (DB) are ready to serve traffic.
 */
export async function getReadiness(): Promise<HealthStatus> {
  const mongoState = mongoose.connection.readyState;
  const mongodb = mongoState === 1 ? 'connected' : 'disconnected';
  const healthy = mongoState === 1;

  return {
    status: healthy ? 'healthy' : 'unhealthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    mongodb,
  };
}
