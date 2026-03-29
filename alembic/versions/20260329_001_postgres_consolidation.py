"""PostgreSQL consolidation for NexusCliniQ

Revision ID: 20260329_001
Revises:
Create Date: 2026-03-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260329_001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("google_id", sa.Text(), nullable=True),
        sa.Column("role", sa.Text(), nullable=False, server_default="researcher"),
        sa.Column("mfa_secret", sa.Text(), nullable=True),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("status", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Text(), nullable=True),
        sa.Column("request_body", sa.Text(), nullable=True),
    )

    op.create_table(
        "predictions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("input_params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("verdict", sa.Text(), nullable=False),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("compound_name", sa.Text(), nullable=True),
    )
    op.create_index("idx_predictions_created_at", "predictions", ["created_at"], unique=False)
    op.create_index("idx_predictions_verdict", "predictions", ["verdict"], unique=False)

    op.create_table(
        "active_learning_queue",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("compound_name", sa.Text(), nullable=True),
        sa.Column("features", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("uncertainty_score", sa.Float(), nullable=False),
        sa.Column("predicted_prob", sa.Float(), nullable=False),
        sa.Column("priority", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("true_label", sa.Integer(), nullable=True),
        sa.Column("labelled_by", sa.Text(), nullable=True),
        sa.Column("labelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
    )

    op.create_table(
        "scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("inputs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("outputs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )

    op.create_table(
        "raw_bioactivity",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("compound_smiles", sa.Text(), nullable=True),
        sa.Column("inchikey", sa.Text(), nullable=True),
        sa.Column("endpoint", sa.Text(), nullable=True),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("units", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "training_data",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("inchikey", sa.Text(), nullable=True),
        sa.Column("smiles", sa.Text(), nullable=True),
        sa.Column("toxicity", sa.Float(), nullable=True),
        sa.Column("bioavailability", sa.Float(), nullable=True),
        sa.Column("solubility", sa.Float(), nullable=True),
        sa.Column("binding", sa.Float(), nullable=True),
        sa.Column("molecular_weight", sa.Float(), nullable=True),
        sa.Column("label", sa.Integer(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("algorithm", sa.Text(), nullable=True, server_default="stacked_ensemble"),
        sa.Column("training_dataset_size", sa.Integer(), nullable=True),
        sa.Column("val_auc", sa.Float(), nullable=True),
        sa.Column("val_f1", sa.Float(), nullable=True),
        sa.Column("val_brier", sa.Float(), nullable=True),
        sa.Column("artifact_path", sa.Text(), nullable=False),
        sa.Column("sync_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("deployed", sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("NOW()")),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "drift_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("feature_name", sa.Text(), nullable=False),
        sa.Column("kl_divergence", sa.Float(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )


def downgrade() -> None:
    op.drop_table("drift_alerts")
    op.drop_table("model_versions")
    op.drop_table("training_data")
    op.drop_table("raw_bioactivity")
    op.drop_table("scenarios")
    op.drop_table("active_learning_queue")
    op.drop_index("idx_predictions_verdict", table_name="predictions")
    op.drop_index("idx_predictions_created_at", table_name="predictions")
    op.drop_table("predictions")
    op.drop_table("audit_logs")
    op.drop_table("users")
