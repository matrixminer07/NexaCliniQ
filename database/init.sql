CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  picture TEXT,
  google_id TEXT,
  password_hash TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_login TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token TEXT UNIQUE NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  method TEXT NOT NULL,
  path TEXT NOT NULL,
  status INTEGER NOT NULL,
  request_id TEXT,
  request_body TEXT
);

CREATE TABLE IF NOT EXISTS predictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  input_params JSONB NOT NULL,
  probability DOUBLE PRECISION NOT NULL,
  verdict TEXT NOT NULL,
  warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
  tags JSONB NOT NULL DEFAULT '[]'::jsonb,
  notes TEXT NOT NULL DEFAULT '',
  compound_name TEXT
);
CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_input_params ON predictions USING GIN(input_params);

CREATE TABLE IF NOT EXISTS scenarios (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  inputs JSONB NOT NULL,
  outputs JSONB NOT NULL,
  tags JSONB NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS active_learning_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  compound_name TEXT,
  features JSONB NOT NULL,
  uncertainty_score DOUBLE PRECISION NOT NULL,
  predicted_prob DOUBLE PRECISION NOT NULL,
  priority TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  true_label INTEGER,
  labelled_by TEXT,
  labelled_at TIMESTAMPTZ,
  notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS raw_bioactivity (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source TEXT NOT NULL,
  compound_smiles TEXT,
  inchikey TEXT,
  endpoint TEXT,
  value DOUBLE PRECISION,
  units TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS training_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  inchikey TEXT,
  smiles TEXT,
  toxicity DOUBLE PRECISION,
  bioavailability DOUBLE PRECISION,
  solubility DOUBLE PRECISION,
  binding DOUBLE PRECISION,
  molecular_weight DOUBLE PRECISION,
  label INTEGER,
  source TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS model_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  version TEXT NOT NULL,
  algorithm TEXT DEFAULT 'stacked_ensemble',
  training_dataset_size INT,
  val_auc FLOAT,
  val_f1 FLOAT,
  val_brier FLOAT,
  artifact_path TEXT NOT NULL,
  deployed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  deployed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS drift_alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  feature_name TEXT NOT NULL,
  kl_divergence DOUBLE PRECISION NOT NULL,
  detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
