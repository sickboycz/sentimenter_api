import { describe, it, expect } from "vitest";
import { getDefaultApiKey } from "../../lib/api";

describe("api", () => {
  it("getDefaultApiKey returns string", () => {
    const key = getDefaultApiKey();
    expect(typeof key).toBe("string");
  });
});
