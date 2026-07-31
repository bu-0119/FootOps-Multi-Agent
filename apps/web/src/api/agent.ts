export interface QuestionUnderstanding {
  intent: string;
  subjects: string[];
  requested_comparisons: string[];
  requested_evidence: string[];
  ambiguities: string[];
}

export interface AnalysisPlanStep {
  title: string;
  purpose: string;
  required_data: string[];
  output: string;
}

export interface AnalysisPlanResponse {
  run_id: string;
  status: "planned";
  mode: "mock" | "deepseek";
  provider: "none" | "deepseek";
  model: string;
  model_called: boolean;
  data_retrieved: boolean;
  real_conclusions_generated: boolean;
  message: string;
  plan: {
    understanding: QuestionUnderstanding;
    steps: AnalysisPlanStep[];
    clarifying_questions: string[];
    assumptions: string[];
    limitations: string[];
  };
}

interface ErrorResponse {
  error?: {
    message?: string;
  };
}

export class AgentApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "AgentApiError";
  }
}

export async function requestAnalysisPlan(
  question: string,
): Promise<AnalysisPlanResponse> {
  const response = await fetch("/api/v1/analyses/plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    let detail: ErrorResponse | undefined;
    try {
      detail = (await response.json()) as ErrorResponse;
    } catch {
      detail = undefined;
    }
    throw new AgentApiError(
      detail?.error?.message ?? "Agent 服务暂时不可用，请稍后重试。",
      response.status,
    );
  }

  return (await response.json()) as AnalysisPlanResponse;
}

export function formatAnalysisPlan(response: AnalysisPlanResponse): string {
  const userFacingParagraphs =
    response.plan.clarifying_questions.length > 0
      ? response.plan.clarifying_questions
      : [response.plan.understanding.intent];

  return userFacingParagraphs
    .map((paragraph) => paragraph.trim())
    .filter(Boolean)
    .join("\n\n");
}
