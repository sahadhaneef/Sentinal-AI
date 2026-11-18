import type { ApiError } from '../contracts/types';
import type { z } from 'zod';
export class ApiClientError extends Error {
  constructor(
    public code: string,
    message: string,
    public status = 0,
    public details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = 'ApiClientError';
  }
  toEnvelope(): ApiError {
    return {
      error: { code: this.code, message: this.message, details: this.details },
      meta: { request_id: 'client', schema_version: '1.0' },
    };
  }
}
export const notFound = () => new ApiClientError('NOT_FOUND', 'This item could not be found.', 404);
export function parseRequest<S extends z.ZodType>(schema: S, value: unknown): z.infer<S> {
  const parsed = schema.safeParse(value);
  if (!parsed.success)
    throw new ApiClientError('VALIDATION_ERROR', 'Check the supplied values and try again.', 422);
  return parsed.data;
}
