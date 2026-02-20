import { Router } from 'express';
import { liveness, readiness } from './health.controller';

const router = Router();

router.get('/liveness', liveness);
router.get('/readiness', readiness);

export { router as healthRoutes };
