import express from "express";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";

import { A2ACommunicationBroker } from "./a2a-broker.js";
import { MonitorStore } from "./monitor-store.js";
import { PolicyEngine } from "./policy-engine.js";

const app = express();
app.use(express.json());

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
app.use("/ui", express.static(path.join(__dirname, "public")));

const policyEngine = new PolicyEngine();
const broker = new A2ACommunicationBroker();
const monitorStore = new MonitorStore();
const backendBaseUrl = process.env.BACKEND_BASE_URL ?? "http://localhost:8080";
const sandboxAgentBaseUrl = process.env.SANDBOX_AGENT_BASE_URL ?? "http://localhost:8083";

const operationSchema = z.object({
  traceId: z.string().min(1),
  role: z.string().min(1),
  operation: z.string().min(1),
  currentOps: z.number().optional().default(0),
  currentSpend: z.number().optional().default(0)
});

const a2aSchema = z.object({
  id: z.string(),
  traceId: z.string(),
  sourceAgent: z.string(),
  targetAgent: z.string(),
  kind: z.string(),
  payload: z.record(z.unknown()),
  timestamp: z.string()
});

const monitorEventSchema = z.object({
  module: z.enum(["backend", "control-plane", "agent-fleet", "sandbox-agent", "unknown"]),
  type: z.string().min(1),
  message: z.string().min(1),
  traceId: z.string().optional(),
  agentId: z.string().optional(),
  health: z.enum(["healthy", "degraded", "offline", "unknown"]).optional(),
  payload: z.record(z.unknown()).optional()
});

const chatDefinitionSchema = z.object({
  module: z.literal("chat"),
  version: z.string().min(1),
  actions: z.array(
    z.object({
      id: z.string().min(1),
      name: z.string().min(1),
      enabled: z.boolean(),
      handler: z.string().min(1),
      timeoutMs: z.number().int().positive()
    })
  ),
  processes: z.array(
    z.object({
      id: z.string().min(1),
      name: z.string().min(1),
      trigger: z.string().min(1),
      steps: z.array(z.string().min(1)).min(1)
    })
  )
});

const chatMessageSchema = z.object({
  message: z.string().min(1),
  conversationId: z.string().optional()
});

let chatDefinition = {
  module: "chat" as const,
  version: "1.0.0",
  actions: [
    { id: "intent-classify", name: "Intent Classification", enabled: true, handler: "backend.classify_intent", timeoutMs: 2000 },
    { id: "policy-check", name: "Policy Check", enabled: true, handler: "control-plane.authorize", timeoutMs: 3000 },
    { id: "agent-route", name: "Agent Routing", enabled: true, handler: "backend.route_to_agent", timeoutMs: 1500 },
    { id: "sandbox-execute", name: "Sandbox Execute", enabled: true, handler: "sandbox-agent.execute", timeoutMs: 8000 }
  ],
  processes: [
    {
      id: "chat-default",
      name: "Default Chat Process",
      trigger: "incoming-message",
      steps: ["intent-classify", "policy-check", "agent-route", "sandbox-execute"]
    }
  ]
};

function emitModuleEvent(
  module: "backend" | "control-plane" | "agent-fleet" | "sandbox-agent" | "unknown",
  type: string,
  message: string,
  context?: { traceId?: string; agentId?: string; health?: "healthy" | "degraded" | "offline" | "unknown"; payload?: Record<string, unknown> }
): void {
  monitorStore.ingest({
    id: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
    module,
    type,
    message,
    traceId: context?.traceId,
    agentId: context?.agentId,
    health: context?.health,
    payload: context?.payload
  });
}

function sanitizeUserReply(text: string): string {
  const withoutThink = text.replace(/<think>[\s\S]*?<\/think>/gi, "").trim();
  if (withoutThink.length > 0) {
    return withoutThink;
  }
  return "I processed your request. Please ask for more detail if needed.";
}

app.post("/authorize", (req, res) => {
  const parsed = operationSchema.safeParse(req.body);
  if (!parsed.success) {
    emitModuleEvent("control-plane", "authorization-invalid", "Authorization payload rejected", { health: "degraded" });
    return res.status(400).json({ error: "invalid-request", issues: parsed.error.issues });
  }
  const decision = policyEngine.authorizeOperation(
    parsed.data.operation,
    parsed.data.role,
    parsed.data.traceId,
    parsed.data.currentOps,
    parsed.data.currentSpend
  );
  const status = decision.allowed ? 200 : 403;
  emitModuleEvent("control-plane", decision.allowed ? "authorization-allowed" : "authorization-denied", `Operation ${parsed.data.operation} ${decision.allowed ? "allowed" : "denied"}`, {
    traceId: parsed.data.traceId,
    health: decision.allowed ? "healthy" : "degraded",
    payload: { role: parsed.data.role, operation: parsed.data.operation }
  });
  return res.status(status).json(decision);
});

app.post("/a2a/send", (req, res) => {
  const parsed = a2aSchema.safeParse(req.body);
  if (!parsed.success) {
    emitModuleEvent("control-plane", "a2a-invalid", "A2A payload rejected", { health: "degraded" });
    return res.status(400).json({ error: "invalid-a2a", issues: parsed.error.issues });
  }
  broker.send(parsed.data);
  emitModuleEvent("control-plane", "a2a-send", `A2A message sent to ${parsed.data.targetAgent}`, {
    traceId: parsed.data.traceId,
    payload: { sourceAgent: parsed.data.sourceAgent, targetAgent: parsed.data.targetAgent, kind: parsed.data.kind },
    health: "healthy"
  });
  return res.status(202).json({ accepted: true });
});

app.get("/a2a/receive/:agentId", (req, res) => {
  return res.json({ messages: broker.receive(req.params.agentId) });
});

app.get("/a2a/trace/:traceId", (req, res) => {
  return res.json({ messages: broker.trace(req.params.traceId) });
});

app.get("/monitor/snapshot", (_req, res) => {
  return res.json(monitorStore.snapshot());
});

app.get("/chat/definitions", (_req, res) => {
  return res.json(chatDefinition);
});

app.post("/chat/message", async (req, res) => {
  const parsed = chatMessageSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: "invalid-chat-message", issues: parsed.error.issues });
  }

  const conversationId = parsed.data.conversationId ?? crypto.randomUUID();
  const userMessage = parsed.data.message;

  emitModuleEvent("control-plane", "chat-user-message", "User chat message received", {
    health: "healthy",
    payload: { conversationId }
  });

  try {
    const orchestrateResponse = await fetch(`${backendBaseUrl}/orchestrate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: userMessage, confirmed: true })
    });

    if (!orchestrateResponse.ok) {
      const text = await orchestrateResponse.text();
      emitModuleEvent("control-plane", "chat-orchestrate-failed", "Backend orchestration failed", { health: "degraded" });
      return res.status(502).json({ error: "orchestration-failed", detail: text });
    }

    const orchestratePayload = (await orchestrateResponse.json()) as { traceId?: string };
    const traceId = orchestratePayload.traceId ?? crypto.randomUUID();

    const policyDecision = policyEngine.authorizeOperation("chat-message", "operator", traceId, 1, 0);
    if (!policyDecision.allowed) {
      emitModuleEvent("control-plane", "chat-policy-denied", "Chat request denied by policy", {
        traceId,
        health: "degraded"
      });
      return res.status(403).json({ error: "chat-policy-denied", traceId, reason: policyDecision.reason });
    }

    const executeResponse = await fetch(`${sandboxAgentBaseUrl}/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        traceId,
        task: {
          prompt: `User message: ${userMessage}\nRespond as the system assistant with concise, actionable next steps.`
        }
      })
    });

    if (!executeResponse.ok) {
      await executeResponse.text();
      emitModuleEvent("control-plane", "chat-execute-failed", "Sandbox execution failed", {
        traceId,
        health: "degraded"
      });
      return res.json({
        conversationId,
        reply:
          "I received your request and the workflow is processing, but the reasoning engine is currently slow. Please retry in a few seconds.",
        timestamp: new Date().toISOString()
      });
    }

    const executePayload = (await executeResponse.json()) as { result?: { llm?: string } };
    const reply = sanitizeUserReply(executePayload.result?.llm ?? "No response generated.");

    emitModuleEvent("control-plane", "chat-response-generated", "System response generated", {
      traceId,
      health: "healthy",
      payload: { conversationId }
    });

    return res.json({
      conversationId,
      reply,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    emitModuleEvent("control-plane", "chat-flow-error", "Unexpected chat flow error", { health: "degraded" });
    return res.json({
      conversationId,
      reply: "I hit a temporary processing issue. Please retry your message.",
      timestamp: new Date().toISOString()
    });
  }
});

app.put("/chat/definitions", (req, res) => {
  const parsed = chatDefinitionSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: "invalid-chat-definition", issues: parsed.error.issues });
  }
  chatDefinition = parsed.data;
  emitModuleEvent("control-plane", "chat-definition-updated", "Chat module actions/processes updated", {
    health: "healthy",
    payload: { version: parsed.data.version, actions: parsed.data.actions.length, processes: parsed.data.processes.length }
  });
  return res.status(200).json({ saved: true, definition: chatDefinition });
});

app.post("/monitor/events", (req, res) => {
  const parsed = monitorEventSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: "invalid-monitor-event", issues: parsed.error.issues });
  }
  const snapshot = monitorStore.ingest({
    id: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
    module: parsed.data.module,
    type: parsed.data.type,
    message: parsed.data.message,
    traceId: parsed.data.traceId,
    agentId: parsed.data.agentId,
    health: parsed.data.health,
    payload: parsed.data.payload
  });
  return res.status(202).json({ accepted: true, snapshot });
});

app.get("/monitor/stream", (req, res) => {
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders();

  const heartbeat = setInterval(() => {
    res.write(`event: heartbeat\ndata: ${JSON.stringify({ ts: new Date().toISOString() })}\n\n`);
  }, 15000);

  res.write(`event: snapshot\ndata: ${JSON.stringify(monitorStore.snapshot())}\n\n`);

  const unsubscribe = monitorStore.subscribe((event, snapshot) => {
    res.write(`event: update\ndata: ${JSON.stringify({ event, snapshot })}\n\n`);
  });

  req.on("close", () => {
    clearInterval(heartbeat);
    unsubscribe();
  });
});

app.get("/ops", (_req, res) => {
  return res.sendFile(path.join(__dirname, "public", "ops.html"));
});

app.get("/chat", (_req, res) => {
  return res.sendFile(path.join(__dirname, "public", "chat-client.html"));
});

app.get("/chat-admin", (_req, res) => {
  return res.sendFile(path.join(__dirname, "public", "chat.html"));
});

setInterval(() => {
  emitModuleEvent("control-plane", "heartbeat", "Control plane heartbeat", { health: "healthy" });
}, 20000);

const port = Number(process.env.PORT ?? 8081);
app.listen(port, () => {
  console.log(`control-plane listening on ${port}`);
});
