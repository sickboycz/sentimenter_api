/** Zod schemas for API response validation (v1.2). */

import { z } from "zod";

export const ResponseMeta = z.object({
  request_id: z.string().min(8),
  as_of: z.string(),
});

export const ApiEnvelope = z.object({
  meta: ResponseMeta,
  data: z.unknown(),
  errors: z.array(
    z.object({
      code: z.string(),
      message: z.string(),
      details: z.record(z.unknown()).optional(),
      hint: z.string().optional(),
    })
  ),
});

export const ApiListEnvelope = ApiEnvelope.extend({
  pagination: z.object({
    limit: z.number(),
    next_cursor: z.string().nullable(),
    returned: z.number(),
  }),
});

export function validateEnvelope<T>(raw: unknown): z.infer<typeof ApiEnvelope> {
  return ApiEnvelope.parse(raw);
}

export function validateListEnvelope(raw: unknown): z.infer<typeof ApiListEnvelope> {
  return ApiListEnvelope.parse(raw);
}
