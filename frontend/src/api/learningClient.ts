import { MockSentinelApi } from './mockAdapter';
import type { SentinelApi } from './interfaces';
/** Isolated educational simulation in either data mode. Never calls the workspace HTTP adapter. */
export const createLearningApi = (): SentinelApi => new MockSentinelApi(120);
