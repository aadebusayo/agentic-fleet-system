import { describe, expect, it } from "vitest";

import { MonitorStore } from "../src/monitor-store.js";

describe("MonitorStore", () => {
  it("tracks agent lifecycle events", () => {
    const store = new MonitorStore();

    store.ingest({
      id: "e1",
      timestamp: new Date().toISOString(),
      module: "agent-fleet",
      type: "agent-spawned",
      message: "Agent started",
      agentId: "agent-1",
      traceId: "trace-1",
      health: "healthy"
    });

    let snapshot = store.snapshot();
    expect(snapshot.activeAgents.length).toBe(1);
    expect(snapshot.activeAgents[0].agentId).toBe("agent-1");

    store.ingest({
      id: "e2",
      timestamp: new Date().toISOString(),
      module: "agent-fleet",
      type: "agent-terminated",
      message: "Agent stopped",
      agentId: "agent-1",
      traceId: "trace-1",
      health: "healthy"
    });

    snapshot = store.snapshot();
    expect(snapshot.activeAgents.length).toBe(0);
  });

  it("updates module health from events", () => {
    const store = new MonitorStore();
    store.ingest({
      id: "e3",
      timestamp: new Date().toISOString(),
      module: "backend",
      type: "heartbeat",
      message: "Backend healthy",
      health: "healthy"
    });

    const status = store.snapshot().modules.find((module) => module.module === "backend");
    expect(status?.health).toBe("healthy");
  });
});
