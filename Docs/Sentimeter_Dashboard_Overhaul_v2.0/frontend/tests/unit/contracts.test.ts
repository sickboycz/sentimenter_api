import { describe, it, expect } from "vitest";
import { HealthData, MoodNowData } from "../../lib/api/contracts";

describe("contracts", () => {
  it("validates HealthData", () => {
    const sample = { status: "ok", as_of: new Date().toISOString(), checks: [] };
    expect(HealthData.safeParse(sample).success).toBe(true);
  });

  it("validates MoodNowData", () => {
    const sample = {
      as_of: new Date().toISOString(),
      sentiment: "Neutral",
      trend: "Sideways",
      index_intraday: 0.1,
      news_volume_intraday: 10,
      news_volatility_intraday: 0.2,
      confidence: 0.7,
      drivers: [],
      risk_vector: {}
    };
    expect(MoodNowData.safeParse(sample).success).toBe(true);
  });
});
