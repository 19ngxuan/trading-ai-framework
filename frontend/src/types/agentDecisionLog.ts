import type { AgentMode, AgentParsingStatus } from "./experiment";
import type { PaginatedResponse } from "./api";

export type AgentDecisionLog = {
  id: number;
  executionStepId: number;
  experimentId: number;
  tradingDecisionId: number | null;
  agentMode: AgentMode;
  agentStepName: string;
  agentName: string | null;
  promptVersion: string | null;
  modelName: string | null;
  modelVersion: string | null;
  inputJson: Record<string, unknown> | null;
  promptText: string | null;
  rawOutputText: string | null;
  parsedOutputJson: Record<string, unknown> | null;
  parsingStatus: AgentParsingStatus;
  repairPromptText: string | null;
  repairRawOutputText: string | null;
  triggerType: "HISTORICAL" | "SCHEDULED" | "MANUAL" | "EVENT" | null;
  executionStepSequenceNumber: number | null;
  createdAt: string;
};

export type PaginatedAgentDecisionLogs = PaginatedResponse<AgentDecisionLog>;
