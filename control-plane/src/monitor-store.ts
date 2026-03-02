export type PlatformModule = "backend" | "control-plane" | "agent-fleet" | "sandbox-agent" | "unknown";
export type ModuleHealth = "healthy" | "degraded" | "offline" | "unknown";

export interface MonitorEvent {
  id: string;
  timestamp: string;
  module: PlatformModule;
  type: string;
  message: string;
  traceId?: string;
  agentId?: string;
  health?: ModuleHealth;
  payload?: Record<string, unknown>;
}

export interface ModuleStatus {
  module: PlatformModule;
  health: ModuleHealth;
  lastEventType: string;
  lastEventMessage: string;
  updatedAt: string;
}

export interface AgentRuntimeView {
  agentId: string;
  module: PlatformModule;
  state: "running" | "idle";
  traceId?: string;
  updatedAt: string;
}

export interface MonitorSnapshot {
  generatedAt: string;
  modules: ModuleStatus[];
  activeAgents: AgentRuntimeView[];
  recentEvents: MonitorEvent[];
}

type Listener = (event: MonitorEvent, snapshot: MonitorSnapshot) => void;

export class MonitorStore {
  private readonly modules = new Map<PlatformModule, ModuleStatus>();
  private readonly activeAgents = new Map<string, AgentRuntimeView>();
  private readonly events: MonitorEvent[] = [];
  private readonly listeners = new Set<Listener>();
  private readonly maxEvents = 200;

  constructor() {
    const now = new Date().toISOString();
    ["backend", "control-plane", "agent-fleet", "sandbox-agent"].forEach((module) => {
      this.modules.set(module as PlatformModule, {
        module: module as PlatformModule,
        health: "unknown",
        lastEventType: "none",
        lastEventMessage: "No activity yet",
        updatedAt: now
      });
    });
  }

  ingest(event: MonitorEvent): MonitorSnapshot {
    const normalized = { ...event, module: event.module ?? "unknown" };
    this.events.unshift(normalized);
    if (this.events.length > this.maxEvents) {
      this.events.length = this.maxEvents;
    }

    const now = normalized.timestamp;
    const current = this.modules.get(normalized.module) ?? {
      module: normalized.module,
      health: "unknown" as ModuleHealth,
      lastEventType: "none",
      lastEventMessage: "No activity yet",
      updatedAt: now
    };

    this.modules.set(normalized.module, {
      ...current,
      health: normalized.health ?? current.health,
      lastEventType: normalized.type,
      lastEventMessage: normalized.message,
      updatedAt: now
    });

    if (normalized.type === "agent-spawned" && normalized.agentId) {
      this.activeAgents.set(normalized.agentId, {
        agentId: normalized.agentId,
        module: normalized.module,
        state: "running",
        traceId: normalized.traceId,
        updatedAt: now
      });
    }

    if (normalized.type === "agent-idle" && normalized.agentId) {
      const existing = this.activeAgents.get(normalized.agentId);
      if (existing) {
        this.activeAgents.set(normalized.agentId, {
          ...existing,
          state: "idle",
          updatedAt: now
        });
      }
    }

    if ((normalized.type === "agent-terminated" || normalized.type === "agent-failed") && normalized.agentId) {
      this.activeAgents.delete(normalized.agentId);
    }

    const snapshot = this.snapshot();
    this.listeners.forEach((listener) => listener(normalized, snapshot));
    return snapshot;
  }

  snapshot(): MonitorSnapshot {
    return {
      generatedAt: new Date().toISOString(),
      modules: Array.from(this.modules.values()).sort((a, b) => a.module.localeCompare(b.module)),
      activeAgents: Array.from(this.activeAgents.values()).sort((a, b) => a.agentId.localeCompare(b.agentId)),
      recentEvents: this.events.slice(0, 100)
    };
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }
}
