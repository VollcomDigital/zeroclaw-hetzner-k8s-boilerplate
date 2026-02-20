import { Router } from 'express';
import { liveness, readiness } from './health.controller.js';

const router = Router();

router.get('/liveness', liveness);
router.get('/readiness', readiness);

export const healthRouter = router;
