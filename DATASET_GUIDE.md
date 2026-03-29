# Dataset Guide

This guide documents the NexusCliniQ dataset sources, licensing, refresh cadence, and preprocessing pipeline used by the weekly dataset sync workflow.

## Sources

## ChEMBL
- Source: https://www.ebi.ac.uk/chembl/
- API endpoint: https://www.ebi.ac.uk/chembl/api/data/activity.json?format=json&limit=1000
- Purpose: Bioactivity records (IC50/Ki/Kd style assay values) used to enrich binding and efficacy signal.
- License: ChEMBL data is distributed under Creative Commons Attribution-ShareAlike (CC BY-SA); verify current terms at ChEMBL before commercial use.
- Refresh cadence: Weekly via Celery `sync_datasets_task`.

## Tox21
- Source: https://tox21.gov and DeepChem mirrored loader assets
- Pull path used: `tox21.csv.gz` compatible dataset format.
- Purpose: Toxicity labels across multiple assay endpoints.
- License: Public U.S. government research data; confirm dataset-specific downstream restrictions when redistributing.
- Refresh cadence: Weekly via Celery `sync_datasets_task`.

## ADMET-AI Benchmarks
- Source: https://github.com/swansonk14/admet_ai/tree/main/admet_ai/data
- Purpose: Curated ADMET benchmark rows used for bioavailability/solubility signal augmentation.
- License: Repository-specific open-source license (check upstream LICENSE file prior to production redistribution).
- Refresh cadence: Weekly via Celery `sync_datasets_task`.

## PubChem BioAssay
- Source: https://pubchem.ncbi.nlm.nih.gov/rest/pug
- Purpose: Complement ChEMBL assay coverage with assay-centric activity records by AID.
- Current configured AIDs: `PUBCHEM_AID_LIST` (default `743269,720709`).
- License: U.S. government-hosted public data; verify assay-level downstream terms when redistributing curated derivatives.
- Refresh cadence: Weekly via Celery `sync_datasets_task`.

## ZINC15 (Roadmap)
- Source: https://zinc15.docking.org
- Purpose: Very large purchasable compound catalog for virtual screening negatives and unlabeled queue enrichment.
- Status: Documented for roadmap; not ingested by default in current weekly sync task.

## Storage Model

## Raw Landing Table
- Table: `raw_bioactivity`
- Columns:
  - `id`
  - `source`
  - `compound_smiles`
  - `inchikey`
  - `endpoint`
  - `value`
  - `units`
  - `created_at`

## Clean Training Table
- Table: `training_data`
- Columns:
  - `id`
  - `inchikey`
  - `smiles`
  - `toxicity`
  - `bioavailability`
  - `solubility`
  - `binding`
  - `molecular_weight`
  - `label`
  - `source`
  - `created_at`

## Preprocessing Steps

1. Pull records from each source feed.
2. For ChEMBL, pull activity pages using configured target IDs for toxicity, binding, bioavailability, and solubility endpoints.
3. For PubChem, pull configured assay IDs via REST CSV export and map assay activity to endpoint-specific normalized values.
4. Standardize chemical string representations.
5. If RDKit is installed:
- Parse SMILES.
- Remove salts/fragments using fragment parent extraction.
- Neutralize charges with RDKit standardizer.
- Canonicalize SMILES.
- Derive InChIKey for deduplication.
6. Drop invalid molecules that fail parsing.
7. Write all records to `raw_bioactivity`.
8. Deduplicate cleaned records by `inchikey` (fallback key: canonical SMILES).
9. Map endpoint/source-specific fields to model feature columns.
10. Write normalized records to `training_data`.
11. Log sync metadata by inserting a `model_versions` row (non-deployed) with dataset size, source breakdown, and configured source selectors.

## Refresh Workflow

- Task: `sync_datasets_task`
- Schedule: Weekly (Sunday, 03:00) in Celery beat.
- Trigger endpoint: `POST /data/sync-datasets` (admin)
- Backward-compatible alias: `POST /data/import-chembl` (admin, same async dataset sync flow)
- Task status endpoint: `GET /jobs/<task_id>`

## Operational Notes

- RDKit is optional. If unavailable, the pipeline keeps source rows but uses less robust normalization.
- Always review source licenses before shipping model artifacts trained on combined public data.
- For GxP workflows, persist raw payload snapshots and transformation metadata externally for audit trails.
