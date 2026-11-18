import { MockSentinelApi } from './mockAdapter';
import { HttpSentinelApi } from './realAdapter';
import type { SentinelApi } from './interfaces';
const source = import.meta.env.VITE_DATA_SOURCE ?? 'mock';
if (source !== 'mock' && source !== 'api') throw new Error('VITE_DATA_SOURCE must be mock or api');
export const isDemo = source === 'mock';
const mock = isDemo ? new MockSentinelApi() : null;
export const api: SentinelApi =
  mock ?? new HttpSentinelApi(import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1');
export const demoControls = mock ? { reset: mock.resetDemo } : null;
