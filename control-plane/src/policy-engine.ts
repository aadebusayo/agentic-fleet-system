export interface PolicyDecision {
  allowed: boolean;
  reason: string;
  traceId: string;
  limits: { maxOps: number; maxBudget: number };
}

export class PolicyEngine {
  validate(operation: string, riskLevel: "low" | "medium" | "high" | "critical"): boolean {
    if (!operation.trim()) {
      return false;
    }
    return riskLevel !== "critical";
  }

  enforceLimits(currentOps: number, currentSpend: number, limits: { maxOps: number; maxBudget: number }): boolean {
    return currentOps <= limits.maxOps && currentSpend <= limits.maxBudget;
  }

  authorizeOperation(
    operation: string,
    role: string,
    traceId: string,
    currentOps = 0,
    currentSpend = 0
  ): PolicyDecision {
    const limits = { maxOps: 100, maxBudget: 25 };
    const allowedRole = role === "admin" || role === "operator";
    const valid = this.validate(operation, "medium");
    const within = this.enforceLimits(currentOps, currentSpend, limits);
    const allowed = allowedRole && valid && within;
    return {
      allowed,
      reason: allowed ? "authorized" : "blocked-by-policy",
      traceId,
      limits
    };
  }
}
