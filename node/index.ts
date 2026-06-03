export type BlocklogLogInput = {
  event_type: string;
  data: Record<string, unknown>;
  source?: string;
  timestamp?: string;
  idempotency_key?: string;
  log_signature?: string;
  public_key_id?: string;
};

export type BlocklogBatchInput = {
  logs: BlocklogLogInput[];
};

export type BlocklogClientOptions = {
  baseUrl: string;
  apiKey: string;
  timeoutMs?: number;
  maxRetries?: number;
  batchSize?: number;
  fetchImpl?: typeof fetch;
};

export class BlocklogClient {
  private readonly baseUrl: string;
  private readonly apiKey: string;
  private readonly timeoutMs: number;
  private readonly maxRetries: number;
  private readonly batchSize: number;
  private readonly fetchImpl: typeof fetch;

  constructor(options: BlocklogClientOptions) {
    if (!options.baseUrl) {
      throw new Error("baseUrl is required");
    }
    if (!options.apiKey) {
      throw new Error("apiKey is required");
    }

    this.baseUrl = options.baseUrl.replace(/\/$/, "");
    this.apiKey = options.apiKey;
    this.timeoutMs = options.timeoutMs ?? 10000;
    this.maxRetries = options.maxRetries ?? 3;
    this.batchSize = options.batchSize ?? 100;
    this.fetchImpl = options.fetchImpl ?? fetch;
  }

  public readonly incidents = {
    assign: (id: string, assignee: string, notes?: string) => 
      this.request(`/api/v1/incidents/${id}/assign`, { method: "POST", body: JSON.stringify({ assignee, notes }) }),
    resolve: (id: string, resolution_summary: string, root_cause?: any, remediation_actions?: any) =>
      this.request(`/api/v1/incidents/${id}/resolve`, { method: "POST", body: JSON.stringify({ resolution_summary, root_cause, remediation_actions }) }),
    close: (id: string, closure_notes: string, approval_status: string = "approved") =>
      this.request(`/api/v1/incidents/${id}/close`, { method: "POST", body: JSON.stringify({ closure_notes, approval_status }) }),
    generateReport: (id: string) =>
      this.request(`/api/v1/incidents/${id}/report`, { method: "POST", body: "{}" }),
  };

  public readonly decisions = {
    getTimeline: (id: string) => this.request(`/api/v1/decisions/${id}/timeline`, { method: "GET" }),
    getEvidence: (id: string) => this.request(`/api/v1/decisions/${id}/evidence`, { method: "GET" }),
  };

  public readonly forensics = {
    compare: (baseline_session_id: string, candidate_session_id: string) =>
      this.request(`/api/v1/forensics/compare`, { method: "POST", body: JSON.stringify({ baseline_session_id, candidate_session_id }) }),
    getComparison: (id: string) => this.request(`/api/v1/forensics/compare/${id}`, { method: "GET" }),
  };

  public readonly hitl = {
    reject: (reviewer: string, rejection_reason: string) =>
      this.request(`/api/v1/hitl/reject`, { method: "POST", body: JSON.stringify({ reviewer, rejection_reason }) }),
    escalate: (current_reviewer: string, escalation_target: string, escalation_reason: string) =>
      this.request(`/api/v1/hitl/escalate`, { method: "POST", body: JSON.stringify({ current_reviewer, escalation_target, escalation_reason }) }),
    getAuditTrail: () => this.request(`/api/v1/hitl/audit-trail`, { method: "GET" }),
  };

  async ingestLog(input: BlocklogLogInput) {
    const log = normalizeLog(input);
    return this.request("/api/v1/logs", {
      method: "POST",
      body: JSON.stringify(log),
    });
  }

  async ingestBatch(logs: BlocklogLogInput[]) {
    if (!Array.isArray(logs) || logs.length === 0) {
      throw new Error("logs must be a non-empty array");
    }

    const results: unknown[] = [];
    for (let index = 0; index < logs.length; index += this.batchSize) {
      const chunk = logs.slice(index, index + this.batchSize).map(normalizeLog);
      results.push(
        await this.request("/api/v1/logs/batch", {
          method: "POST",
          body: JSON.stringify({ logs: chunk } satisfies BlocklogBatchInput),
        }),
      );
    }
    return results;
  }

  async sealBatch(intervalMinutes = 5) {
    return this.request(`/api/v1/batches/seal?interval_minutes=${intervalMinutes}`, {
      method: "POST",
    });
  }

  private async request(path: string, init: RequestInit) {
    let lastError: Error | null = null;

    for (let attempt = 0; attempt < this.maxRetries; attempt += 1) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), this.timeoutMs);

      try {
        const response = await this.fetchImpl(`${this.baseUrl}${path}`, {
          ...init,
          signal: controller.signal,
          headers: {
            "Content-Type": "application/json",
            "X-API-Key": this.apiKey,
            ...(init.headers ?? {}),
          },
        });

        if (response.ok) {
          return response.json();
        }

        if (response.status < 500 || attempt === this.maxRetries - 1) {
          throw new Error(await response.text() || `Request failed (${response.status})`);
        }
      } catch (error) {
        lastError = error instanceof Error ? error : new Error("Request failed");
        if (attempt === this.maxRetries - 1) {
          throw lastError;
        }
        await sleep(250 * (attempt + 1));
      } finally {
        clearTimeout(timer);
      }
    }

    throw lastError ?? new Error("Request failed");
  }
}

function normalizeLog(input: BlocklogLogInput): BlocklogLogInput {
  if (!input.event_type || typeof input.event_type !== "string") {
    throw new Error("event_type is required");
  }
  if (!input.data || typeof input.data !== "object" || Array.isArray(input.data)) {
    throw new Error("data must be an object");
  }
  if (input.idempotency_key && input.idempotency_key.length < 8) {
    throw new Error("idempotency_key must be at least 8 characters");
  }

  return {
    ...input,
    source: input.source ?? "node-sdk",
    timestamp: input.timestamp ?? new Date().toISOString(),
    idempotency_key: input.idempotency_key ?? defaultIdempotencyKey(input),
  };
}

function defaultIdempotencyKey(input: BlocklogLogInput): string {
  const seed = JSON.stringify([input.event_type, input.source ?? "node-sdk", input.data]);
  let hash = 0;
  for (let index = 0; index < seed.length; index += 1) {
    hash = (hash * 31 + seed.charCodeAt(index)) >>> 0;
  }
  return `node_${hash.toString(16)}`;
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
