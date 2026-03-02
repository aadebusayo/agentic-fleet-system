import { describe, expect, it } from "vitest";

import { PolicyEngine } from "../src/policy-engine.js";

describe("PolicyEngine", () => {
  it("authorizes operator operations within limits", () => {
    const engine = new PolicyEngine();
    const decision = engine.authorizeOperation("deploy", "operator", "t-1", 5, 2);
    expect(decision.allowed).toBe(true);
  });

  it("blocks when over limits", () => {
    const engine = new PolicyEngine();
    const decision = engine.authorizeOperation("deploy", "operator", "t-2", 500, 2);
    expect(decision.allowed).toBe(false);
  });

  it("blocks unauthorized role", () => {
    const engine = new PolicyEngine();
    const decision = engine.authorizeOperation("deploy", "viewer", "t-3", 1, 1);
    expect(decision.allowed).toBe(false);
  });

  it("enforces budget cap", () => {
    const engine = new PolicyEngine();
    const decision = engine.authorizeOperation("deploy", "operator", "t-4", 1, 100);
    expect(decision.allowed).toBe(false);
  });
});
