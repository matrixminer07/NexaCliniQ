import { z } from 'zod'

// Core API contracts requested for runtime boundary validation.
export const PredictResponseSchema = z.object({
  probability: z.number().min(0).max(1),
  confidence_interval: z.tuple([z.number(), z.number()]),
  shap_values: z.record(z.string(), z.number()),
  phase_probabilities: z.record(z.string(), z.number()).optional(),
})

export const RiskItemSchema = z.object({
  risk: z.string(), category: z.string(),
  likelihood: z.enum(['High', 'Medium', 'Low']),
  impact: z.enum(['High', 'Medium', 'Low']),
  mitigation: z.string().optional(),
})

export const RiskRegisterSchema = z.array(RiskItemSchema)

export const MarketSizingSchema = z.object({
  tam: z.number(), sam: z.number(), som: z.number(),
  segments: z.array(z.object({ name: z.string(), value: z.number() })).optional(),
})

export const ScenarioSchema = z.object({
  id: z.string().uuid(), name: z.string(), type: z.string(),
  input_params: z.record(z.string(), z.unknown()), result: z.unknown().optional(),
  created_at: z.string().datetime(),
})

export const ScenarioListSchema = z.array(ScenarioSchema)

export const HistoryItemSchema = z.object({
  id: z.string().uuid(), compound_id: z.string().optional(),
  input_params: z.record(z.string(), z.unknown()), result: z.record(z.string(), z.unknown()),
  created_at: z.string().datetime(),
})

export const HistoryListSchema = z.array(HistoryItemSchema)

export const ExecutiveSummarySchema = z.object({
  headline: z.string(), recommendation: z.string(),
  key_risks: z.array(z.string()), key_opportunities: z.array(z.string()),
  npv_summary: z.string().optional(),
})

export const StrategyRoadmapSchema = z.array(z.object({
  milestone: z.string(), date: z.string(),
  description: z.string().optional(),
  status: z.enum(['completed', 'in-progress', 'upcoming']).optional(),
}))

export const JobStatusSchema = z.object({
  task_id: z.string(),
  status: z.enum(['PENDING', 'STARTED', 'SUCCESS', 'FAILURE']),
  progress: z.number().nullable().optional(),
  result: z.unknown().optional(),
  error: z.string().nullable().optional(),
})

export const AdminStatsSchema = z.object({
  total_users: z.number().default(0),
  users_this_week: z.number().default(0),
  predictions_today: z.number().default(0),
  predictions_yesterday: z.number().default(0),
  api_requests_24h: z.number().default(0),
  errors_24h: z.number().default(0),
  active_sessions: z.number().default(0),
  model_auc: z.number().default(0),
})

export const UserSchema = z.object({
  id: z.string(),
  name: z.string().default('Unknown'),
  email: z.string(),
  role: z.enum(['admin', 'researcher', 'viewer']),
  status: z.enum(['active', 'suspended']).default('active'),
  mfa_enabled: z.boolean().default(false),
  last_login: z.string().nullable().optional(),
  created_at: z.string().optional(),
  predictions_run: z.number().default(0),
})

export const UserListSchema = z.object({
  data: z.array(UserSchema).default([]),
  total: z.number().default(0),
  page: z.number().default(1),
  limit: z.number().default(20),
})

export const AuditLogSchema = z.object({
  id: z.string(),
  timestamp: z.string(),
  user: z.string().optional(),
  endpoint: z.string().optional(),
  path: z.string().default(''),
  method: z.string().default('GET'),
  status: z.number().default(200),
  response_ms: z.number().optional(),
  request_body: z.unknown().optional(),
})

export const ModelVersionSchema = z.object({
  id: z.string().optional(),
  version: z.string().optional(),
  algorithm: z.string().optional(),
  training_dataset_size: z.number().optional(),
  val_auc: z.number().optional(),
  val_f1: z.number().optional(),
  val_brier: z.number().optional(),
  created_at: z.string().optional(),
  deployed: z.boolean().optional(),
})

export const DriftAlertSchema = z.object({
  id: z.string(),
  feature_name: z.string(),
  kl_divergence: z.number(),
  detected_at: z.string(),
  acknowledged_by: z.string().optional(),
})

export const CalibrationSchema = z.object({
  points: z.array(z.object({ predicted: z.number(), actual: z.number() })).default([]),
})

// Generic API response envelope helpers.
export function createSuccessEnvelopeSchema<T extends z.ZodTypeAny>(dataSchema: T) {
  return z.object({
    success: z.literal(true),
    data: dataSchema,
    error: z.null().optional(),
  })
}

export function createErrorEnvelopeSchema() {
  return z.object({
    success: z.literal(false),
    error: z.string(),
    details: z.unknown().optional(),
  })
}
