import { afterEach, expect, it, vi } from 'vitest';
import { HttpSentinelApi } from '../api/realAdapter';
it('identifies non-JSON server responses without mislabeling them as offline', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(new Response('<html>Proxy unavailable</html>', { status: 502 })),
  );
  await expect(new HttpSentinelApi('/api/v1').getHealth()).rejects.toMatchObject({
    code: 'INVALID_RESPONSE',
    status: 502,
  });
});
const api = new HttpSentinelApi('http://localhost:8000/api/v1');
afterEach(() => vi.unstubAllGlobals());
it('uses canonical URLs, cookies and runtime response validation', async () => {
  const fetch = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({
        data: { status: 'ok', version: '1.0' },
        meta: { request_id: 'test', schema_version: '1.0' },
      }),
    ),
  );
  vi.stubGlobal('fetch', fetch);
  expect((await api.getHealth()).data.status).toBe('ok');
  expect(fetch).toHaveBeenCalledWith(
    'http://localhost:8000/api/v1/health',
    expect.objectContaining({ credentials: 'include', method: 'GET' }),
  );
});
it.each([401, 403, 404, 409, 422, 500])(
  'preserves a %i API error without leaking traces',
  async (status) => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: status === 409 ? 'CANDIDATE_STALE' : 'REQUEST_FAILED',
              message: 'Review this request.',
              details: {},
            },
            meta: { request_id: 'test', schema_version: '1.0' },
          }),
          { status },
        ),
      ),
    );
    await expect(api.getIncident('inc_001')).rejects.toMatchObject({
      status,
      message: 'Review this request.',
    });
  },
);
it('rejects malformed successful responses', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: { status: 'fictional' },
          meta: { request_id: 'test', schema_version: '1.0' },
        }),
      ),
    ),
  );
  await expect(api.getHealth()).rejects.toMatchObject({ code: 'INVALID_RESPONSE' });
});
it('exposes network failures and does not silently substitute mocks', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Network failed')));
  await expect(api.listAgents()).rejects.toMatchObject({ code: 'OFFLINE', status: 0 });
});
