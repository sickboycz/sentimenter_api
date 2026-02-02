import { describe, it, expect } from "vitest";
import { ApiEnvelope, MoodSnapshot } from "../../lib/api/contracts";

describe("Zod contracts", () => {
  it("validates mood now envelope", () => {
    const schema = ApiEnvelope(MoodSnapshot);
    const sample = {
      meta: { request_id: "req_12345678", as_of: new Date().toISOString(), model_versions: {} },
      data: {
        as_of: new Date().toISOString(),
        sentiment: "Neutral",
        trend: "Sideways",
        index_intraday: 0.1,
        news_volume_intraday: 10,
        news_volatility_intraday: 0.2,
        confidence: 0.7,
        drivers: [],
        risk_vector: {},
      },
      errors: [],
    };
    const parsed = schema.safeParse(sample);
    expect(parsed.success).toBe(true);
  });
});
