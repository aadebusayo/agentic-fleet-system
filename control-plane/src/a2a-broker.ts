type Message = {
  id: string;
  traceId: string;
  sourceAgent: string;
  targetAgent: string;
  kind: string;
  payload: Record<string, unknown>;
  timestamp: string;
};

export class A2ACommunicationBroker {
  private readonly queue: Message[] = [];

  send(message: Message): void {
    this.queue.push(message);
  }

  receive(targetAgent: string): Message[] {
    return this.queue.filter((msg) => msg.targetAgent === targetAgent);
  }

  trace(traceId: string): Message[] {
    return this.queue.filter((msg) => msg.traceId === traceId);
  }
}
