import { describe, it, expect } from "vitest";
import { getDefaultApiKey, ApiDegradedError } from "../../lib/api";

describe("api", () => {
  it("getDefaultApiKey returns string", () => {
    const key = getDefaultApiKey();
    expect(typeof key).toBe("string");
  });

  it("ApiDegradedError is Error with name", () => {
    const err = new ApiDegradedError("test");
    expect(err).toBeInstanceOf(Error);
    expect(err.name).toBe("ApiDegradedError");
    expect(err.message).toBe("test");
  });
});
