"""domain persistence

Revision ID: 0002_domain
Revises: 0001_foundation
"""

import sqlalchemy as sa

from alembic import context, op

revision = "0002_domain"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None

DOMAIN_TABLES = (
    "agent_executions",
    "application_attempts",
    "application_revisions",
    "applications",
    "approval_decisions",
    "artifacts",
    "audit_events",
    "auth_sessions",
    "backend_settings",
    "code_index_entries",
    "diagnoses",
    "evidence_references",
    "idempotency_records",
    "incident_monitoring_events",
    "incident_reports",
    "incidents",
    "monitoring_events",
    "patch_candidates",
    "repository_revisions",
    "roles",
    "stage_transitions",
    "user_roles",
    "users",
    "validation_checks",
    "validation_results",
    "verification_checks",
    "verification_results",
    "workflow_runs",
)


def upgrade() -> None:
    op.create_table(
        "applications",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("workspace_key", sa.String(length=128), nullable=False),
        sa.Column(
            "monitoring_enabled",
            sa.Boolean(create_constraint=True, name="monitoring_bool"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("supported_errors", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(workspace_key) BETWEEN 1 AND 128 AND workspace_key NOT GLO"
            "B '*[^A-Za-z0-9_.-]*' AND instr(workspace_key,'..') = 0",
            name=op.f("ck_applications_workspace_key_format"),
        ),
        sa.CheckConstraint("schema_version = '1.0'", name=op.f("ck_applications_schema_version")),
        sa.CheckConstraint(
            "status IN ('healthy','degraded','offline')",
            name=op.f("ck_applications_application_status"),
        ),
        sa.CheckConstraint("length(id) BETWEEN 1 AND 64", name=op.f("ck_applications_id_length")),
        sa.CheckConstraint(
            "length(name) BETWEEN 1 AND 200", name=op.f("ck_applications_name_length")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_applications")),
        sa.UniqueConstraint("workspace_key", name=op.f("uq_applications_workspace_key")),
    )
    op.create_table(
        "artifacts",
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("sha256", sa.String(length=71), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "redacted", sa.Boolean(create_constraint=True, name="redacted_bool"), nullable=False
        ),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kind IN ('log','source_snapshot','source_excerpt','diff','test_ou"
            "tput','verification','report','diagnosis','snapshot')",
            name=op.f("ck_artifacts_artifact_kind"),
        ),
        sa.CheckConstraint(
            "length(sha256) = 71 AND substr(sha256,1,7) = 'sha256:' AND substr"
            "(sha256,8) NOT GLOB '*[^0-9a-f]*'",
            name=op.f("ck_artifacts_sha256_format"),
        ),
        sa.CheckConstraint(
            "length(storage_key) BETWEEN 1 AND 512 AND substr(storage_key,1,1)"
            " NOT IN ('/','.') AND storage_key NOT GLOB '*[^A-Za-z0-9_./-]*' A"
            "ND instr(storage_key,'..') = 0 AND instr(storage_key,'//') = 0",
            name=op.f("ck_artifacts_storage_key_relative"),
        ),
        sa.CheckConstraint("schema_version = '1.0'", name=op.f("ck_artifacts_schema_version")),
        sa.CheckConstraint("length(id) BETWEEN 1 AND 64", name=op.f("ck_artifacts_id_length")),
        sa.CheckConstraint("size_bytes >= 0", name=op.f("ck_artifacts_size_nonnegative")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_artifacts")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_artifacts_storage_key")),
    )
    op.create_table(
        "backend_settings",
        sa.Column("singleton_key", sa.String(length=16), nullable=False),
        sa.Column("monitoring_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("max_candidate_revisions", sa.Integer(), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "schema_version = '1.0'", name=op.f("ck_backend_settings_schema_version")
        ),
        sa.CheckConstraint(
            "singleton_key = 'settings'", name=op.f("ck_backend_settings_singleton_key")
        ),
        sa.CheckConstraint(
            "length(id) BETWEEN 1 AND 64", name=op.f("ck_backend_settings_id_length")
        ),
        sa.CheckConstraint(
            "max_candidate_revisions BETWEEN 0 AND 2",
            name=op.f("ck_backend_settings_candidate_revisions"),
        ),
        sa.CheckConstraint(
            "monitoring_interval_seconds BETWEEN 3 AND 60",
            name=op.f("ck_backend_settings_monitoring_interval"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_backend_settings")),
        sa.UniqueConstraint("singleton_key", name=op.f("uq_backend_settings_singleton_key")),
    )
    op.create_table(
        "roles",
        sa.Column("name", sa.String(length=32), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "name IN ('admin','developer','reviewer','viewer')", name=op.f("ck_roles_role_name")
        ),
        sa.CheckConstraint("schema_version = '1.0'", name=op.f("ck_roles_schema_version")),
        sa.CheckConstraint("length(id) BETWEEN 1 AND 64", name=op.f("ck_roles_id_length")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roles")),
        sa.UniqueConstraint("name", name=op.f("uq_roles_name")),
    )
    op.create_table(
        "users",
        sa.Column("username", sa.String(length=128, collation="NOCASE"), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(create_constraint=True, name="active_bool"), nullable=False
        ),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint("schema_version = '1.0'", name=op.f("ck_users_schema_version")),
        sa.CheckConstraint("length(id) BETWEEN 1 AND 64", name=op.f("ck_users_id_length")),
        sa.CheckConstraint(
            "length(username) BETWEEN 1 AND 128", name=op.f("ck_users_username_length")
        ),
        sa.CheckConstraint(
            "password_hash IS NULL OR length(password_hash) >= 20",
            name=op.f("ck_users_password_hash"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("username", name=op.f("uq_users_username")),
    )
    op.create_table(
        "auth_sessions",
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=71), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(token_hash) = 71 AND substr(token_hash,1,7) = 'sha256:' AN"
            "D substr(token_hash,8) NOT GLOB '*[^0-9a-f]*'",
            name=op.f("ck_auth_sessions_token_hash_format"),
        ),
        sa.CheckConstraint("schema_version = '1.0'", name=op.f("ck_auth_sessions_schema_version")),
        sa.CheckConstraint("expires_at > created_at", name=op.f("ck_auth_sessions_session_expiry")),
        sa.CheckConstraint("length(id) BETWEEN 1 AND 64", name=op.f("ck_auth_sessions_id_length")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_auth_sessions_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_auth_sessions_token_hash")),
    )
    op.create_index(op.f("ix_auth_sessions_user_id"), "auth_sessions", ["user_id"], unique=False)
    op.create_table(
        "idempotency_records",
        sa.Column("actor_user_id", sa.String(length=64), nullable=False),
        sa.Column("operation", sa.String(length=100), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=71), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("response_artifact_id", sa.String(length=64), nullable=True),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(request_hash) = 71 AND substr(request_hash,1,7) = 'sha256:"
            "' AND substr(request_hash,8) NOT GLOB '*[^0-9a-f]*'",
            name=op.f("ck_idempotency_records_request_hash_format"),
        ),
        sa.CheckConstraint(
            "schema_version = '1.0'", name=op.f("ck_idempotency_records_schema_version")
        ),
        sa.CheckConstraint(
            "status IN ('pending','completed','failed')",
            name=op.f("ck_idempotency_records_idempotency_status"),
        ),
        sa.CheckConstraint(
            "length(id) BETWEEN 1 AND 64", name=op.f("ck_idempotency_records_id_length")
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_idempotency_records_actor_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["response_artifact_id"],
            ["artifacts.id"],
            name=op.f("fk_idempotency_records_response_artifact_id_artifacts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_idempotency_records")),
        sa.UniqueConstraint(
            "actor_user_id", "operation", "key", name=op.f("uq_idempotency_records_actor_user_id")
        ),
    )
    op.create_table(
        "repository_revisions",
        sa.Column("application_id", sa.String(length=64), nullable=False),
        sa.Column("revision", sa.String(length=128), nullable=False),
        sa.Column("snapshot_artifact_id", sa.String(length=64), nullable=False),
        sa.Column("indexed_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(revision) BETWEEN 1 AND 128 AND revision NOT GLOB '*[^A-Za"
            "-z0-9_.-]*' AND instr(revision,'..') = 0",
            name=op.f("ck_repository_revisions_revision_format"),
        ),
        sa.CheckConstraint(
            "schema_version = '1.0'", name=op.f("ck_repository_revisions_schema_version")
        ),
        sa.CheckConstraint(
            "length(id) BETWEEN 1 AND 64", name=op.f("ck_repository_revisions_id_length")
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_repository_revisions_application_id_applications"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_artifact_id"],
            ["artifacts.id"],
            name=op.f("fk_repository_revisions_snapshot_artifact_id_artifacts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_repository_revisions")),
        sa.UniqueConstraint(
            "application_id", "revision", name=op.f("uq_repository_revisions_application_id")
        ),
        sa.UniqueConstraint("id", "application_id", name=op.f("uq_repository_revisions_id")),
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("role_id", sa.String(length=64), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint("schema_version = '1.0'", name=op.f("ck_user_roles_schema_version")),
        sa.CheckConstraint("length(id) BETWEEN 1 AND 64", name=op.f("ck_user_roles_id_length")),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], name=op.f("fk_user_roles_role_id_roles"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_user_roles_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_roles")),
        sa.UniqueConstraint("user_id", "role_id", name=op.f("uq_user_roles_user_id")),
    )
    op.create_table(
        "application_revisions",
        sa.Column("application_id", sa.String(length=64), nullable=False),
        sa.Column("revision_id", sa.String(length=64), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "schema_version = '1.0'", name=op.f("ck_application_revisions_schema_version")
        ),
        sa.CheckConstraint(
            "length(id) BETWEEN 1 AND 64", name=op.f("ck_application_revisions_id_length")
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_application_revisions_application_id_applications"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["revision_id", "application_id"],
            ["repository_revisions.id", "repository_revisions.application_id"],
            name=op.f("fk_application_revisions_revision_id_repository_revisions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_application_revisions")),
        sa.UniqueConstraint("application_id", name=op.f("uq_application_revisions_application_id")),
    )
    op.create_table(
        "code_index_entries",
        sa.Column("application_id", sa.String(length=64), nullable=False),
        sa.Column("repository_revision", sa.String(length=128), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("symbol", sa.String(length=300), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=71), nullable=False),
        sa.Column("artifact_id", sa.String(length=64), nullable=False),
        sa.Column("index_metadata", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(content_hash) = 71 AND substr(content_hash,1,7) = 'sha256:"
            "' AND substr(content_hash,8) NOT GLOB '*[^0-9a-f]*'",
            name=op.f("ck_code_index_entries_content_hash_format"),
        ),
        sa.CheckConstraint(
            "length(file_path) BETWEEN 1 AND 512 AND substr(file_path,1,1) NOT"
            " IN ('/','.') AND file_path NOT GLOB '*[^A-Za-z0-9_./-]*' AND ins"
            "tr(file_path,'..') = 0 AND instr(file_path,'//') = 0",
            name=op.f("ck_code_index_entries_file_path_relative"),
        ),
        sa.CheckConstraint(
            "schema_version = '1.0'", name=op.f("ck_code_index_entries_schema_version")
        ),
        sa.CheckConstraint(
            "length(id) BETWEEN 1 AND 64", name=op.f("ck_code_index_entries_id_length")
        ),
        sa.CheckConstraint(
            "start_line >= 1 AND end_line >= start_line",
            name=op.f("ck_code_index_entries_line_range"),
        ),
        sa.ForeignKeyConstraint(
            ["application_id", "repository_revision"],
            ["repository_revisions.application_id", "repository_revisions.revision"],
            name=op.f("fk_code_index_entries_application_id_repository_revisions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["artifact_id"],
            ["artifacts.id"],
            name=op.f("fk_code_index_entries_artifact_id_artifacts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_code_index_entries")),
        sa.UniqueConstraint(
            "application_id",
            "repository_revision",
            "file_path",
            "start_line",
            "end_line",
            name=op.f("uq_code_index_entries_application_id"),
        ),
        sa.UniqueConstraint(
            "id", "application_id", "repository_revision", name=op.f("uq_code_index_entries_id")
        ),
    )
    op.create_table(
        "monitoring_events",
        sa.Column("application_id", sa.String(length=64), nullable=False),
        sa.Column("repository_revision", sa.String(length=128), nullable=False),
        sa.Column("source_event_id", sa.String(length=256), nullable=False),
        sa.Column("fingerprint", sa.String(length=71), nullable=False),
        sa.Column(
            "severity",
            sa.Enum(
                "low",
                "medium",
                "high",
                "critical",
                name="severity",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("error_type", sa.String(length=200), nullable=False),
        sa.Column("message", sa.String(length=2000), nullable=False),
        sa.Column("classification", sa.String(length=16), nullable=False),
        sa.Column("log_artifact_id", sa.String(length=64), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "classification IN ('supported','unsupported')",
            name=op.f("ck_monitoring_events_classification"),
        ),
        sa.CheckConstraint(
            "length(fingerprint) = 71 AND substr(fingerprint,1,7) = 'sha256:' "
            "AND substr(fingerprint,8) NOT GLOB '*[^0-9a-f]*'",
            name=op.f("ck_monitoring_events_fingerprint_format"),
        ),
        sa.CheckConstraint(
            "schema_version = '1.0'", name=op.f("ck_monitoring_events_schema_version")
        ),
        sa.CheckConstraint(
            "length(id) BETWEEN 1 AND 64", name=op.f("ck_monitoring_events_id_length")
        ),
        sa.CheckConstraint(
            "length(message) BETWEEN 1 AND 2000", name=op.f("ck_monitoring_events_message_length")
        ),
        sa.CheckConstraint(
            "length(source_event_id) BETWEEN 1 AND 256",
            name=op.f("ck_monitoring_events_source_event_id_length"),
        ),
        sa.ForeignKeyConstraint(
            ["application_id", "repository_revision"],
            ["repository_revisions.application_id", "repository_revisions.revision"],
            name=op.f("fk_monitoring_events_application_id_repository_revisions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_monitoring_events_application_id_applications"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["log_artifact_id"],
            ["artifacts.id"],
            name=op.f("fk_monitoring_events_log_artifact_id_artifacts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_monitoring_events")),
        sa.UniqueConstraint(
            "application_id", "source_event_id", name=op.f("uq_monitoring_events_application_id")
        ),
        sa.UniqueConstraint(
            "id", "application_id", "repository_revision", name=op.f("uq_monitoring_events_id")
        ),
    )
    op.create_index(
        "ix_monitoring_events_application_fingerprint",
        "monitoring_events",
        ["application_id", "fingerprint"],
        unique=False,
    )
    op.create_table(
        "incidents",
        sa.Column("application_id", sa.String(length=64), nullable=False),
        sa.Column("repository_revision", sa.String(length=128), nullable=False),
        sa.Column("source_event_id", sa.String(length=256), nullable=False),
        sa.Column("fingerprint", sa.String(length=71), nullable=False),
        sa.Column(
            "severity",
            sa.Enum(
                "low",
                "medium",
                "high",
                "critical",
                name="severity",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("error_type", sa.String(length=200), nullable=False),
        sa.Column("message", sa.String(length=2000), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "detected",
                "diagnosing",
                "generating_patch",
                "validating",
                "revision_requested",
                "awaiting_approval",
                "approved",
                "applying",
                "verifying",
                "restoring",
                "resolved",
                "rejected",
                "manual_review",
                "unresolved",
                "error",
                "reported",
                name="run_state",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("current_stage", sa.String(length=64), nullable=False),
        sa.Column("detected_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(fingerprint) = 71 AND substr(fingerprint,1,7) = 'sha256:' "
            "AND substr(fingerprint,8) NOT GLOB '*[^0-9a-f]*'",
            name=op.f("ck_incidents_fingerprint_format"),
        ),
        sa.CheckConstraint(
            "resolved_at IS NULL OR status IN ('resolved','reported')",
            name=op.f("ck_incidents_resolved_status"),
        ),
        sa.CheckConstraint("schema_version = '1.0'", name=op.f("ck_incidents_schema_version")),
        sa.CheckConstraint("length(id) BETWEEN 1 AND 64", name=op.f("ck_incidents_id_length")),
        sa.CheckConstraint(
            "length(message) BETWEEN 1 AND 2000", name=op.f("ck_incidents_message_length")
        ),
        sa.ForeignKeyConstraint(
            ["application_id", "repository_revision"],
            ["repository_revisions.application_id", "repository_revisions.revision"],
            name=op.f("fk_incidents_application_id_repository_revisions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["application_id", "source_event_id"],
            ["monitoring_events.application_id", "monitoring_events.source_event_id"],
            name=op.f("fk_incidents_application_id_monitoring_events"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_incidents_application_id_applications"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incidents")),
        sa.UniqueConstraint(
            "id", "application_id", "repository_revision", name=op.f("uq_incidents_id")
        ),
        sa.UniqueConstraint("id", "application_id", name=op.f("uq_incidents_id")),
    )
    op.create_index(
        "ix_incidents_application_status_detected",
        "incidents",
        ["application_id", "status", "detected_at"],
        unique=False,
    )
    op.create_index(
        "uq_incidents_active_fingerprint",
        "incidents",
        ["application_id", "fingerprint"],
        unique=True,
        sqlite_where=sa.text("status NOT IN ('resolved','rejected','unresolved','reported')"),
    )
    op.create_table(
        "incident_monitoring_events",
        sa.Column("incident_id", sa.String(length=64), nullable=False),
        sa.Column("monitoring_event_id", sa.String(length=64), nullable=False),
        sa.Column("application_id", sa.String(length=64), nullable=False),
        sa.Column("repository_revision", sa.String(length=128), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "schema_version = '1.0'", name=op.f("ck_incident_monitoring_events_schema_version")
        ),
        sa.CheckConstraint(
            "length(id) BETWEEN 1 AND 64", name=op.f("ck_incident_monitoring_events_id_length")
        ),
        sa.ForeignKeyConstraint(
            ["incident_id", "application_id", "repository_revision"],
            ["incidents.id", "incidents.application_id", "incidents.repository_revision"],
            name=op.f("fk_incident_monitoring_events_incident_id_incidents"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["monitoring_event_id", "application_id", "repository_revision"],
            [
                "monitoring_events.id",
                "monitoring_events.application_id",
                "monitoring_events.repository_revision",
            ],
            name=op.f("fk_incident_monitoring_events_monitoring_event_id_monitoring_events"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incident_monitoring_events")),
        sa.UniqueConstraint(
            "monitoring_event_id", name=op.f("uq_incident_monitoring_events_monitoring_event_id")
        ),
    )
    op.create_index(
        "ix_incident_monitoring_events_incident",
        "incident_monitoring_events",
        ["incident_id"],
        unique=False,
    )
    op.create_table(
        "incident_reports",
        sa.Column("incident_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "outcome",
            sa.Enum(
                "detected",
                "diagnosing",
                "generating_patch",
                "validating",
                "revision_requested",
                "awaiting_approval",
                "approved",
                "applying",
                "verifying",
                "restoring",
                "resolved",
                "rejected",
                "manual_review",
                "unresolved",
                "error",
                "reported",
                name="run_state",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("report_artifact_id", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.String(length=4000), nullable=False),
        sa.Column("limitations", sa.JSON(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "outcome IN ('resolved','rejected','unresolved','manual_review','error','reported')",
            name=op.f("ck_incident_reports_terminal_outcome"),
        ),
        sa.CheckConstraint(
            "schema_version = '1.0'", name=op.f("ck_incident_reports_schema_version")
        ),
        sa.CheckConstraint(
            "length(id) BETWEEN 1 AND 64", name=op.f("ck_incident_reports_id_length")
        ),
        sa.CheckConstraint("version >= 1", name=op.f("ck_incident_reports_version_positive")),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            name=op.f("fk_incident_reports_incident_id_incidents"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["report_artifact_id"],
            ["artifacts.id"],
            name=op.f("fk_incident_reports_report_artifact_id_artifacts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incident_reports")),
        sa.UniqueConstraint("incident_id", "version", name=op.f("uq_incident_reports_incident_id")),
    )
    op.create_index(
        "ix_incident_reports_incident_generated",
        "incident_reports",
        ["incident_id", "generated_at"],
        unique=False,
    )
    op.create_table(
        "workflow_runs",
        sa.Column("incident_id", sa.String(length=64), nullable=False),
        sa.Column("application_id", sa.String(length=64), nullable=False),
        sa.Column("repository_revision", sa.String(length=128), nullable=False),
        sa.Column(
            "state",
            sa.Enum(
                "detected",
                "diagnosing",
                "generating_patch",
                "validating",
                "revision_requested",
                "awaiting_approval",
                "approved",
                "applying",
                "verifying",
                "restoring",
                "resolved",
                "rejected",
                "manual_review",
                "unresolved",
                "error",
                "reported",
                name="run_state",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("error_artifact_id", sa.String(length=64), nullable=True),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint("schema_version = '1.0'", name=op.f("ck_workflow_runs_schema_version")),
        sa.CheckConstraint("attempt >= 1", name=op.f("ck_workflow_runs_attempt_positive")),
        sa.CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name=op.f("ck_workflow_runs_run_time_order"),
        ),
        sa.CheckConstraint("length(id) BETWEEN 1 AND 64", name=op.f("ck_workflow_runs_id_length")),
        sa.ForeignKeyConstraint(
            ["error_artifact_id"],
            ["artifacts.id"],
            name=op.f("fk_workflow_runs_error_artifact_id_artifacts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["incident_id", "application_id", "repository_revision"],
            ["incidents.id", "incidents.application_id", "incidents.repository_revision"],
            name=op.f("fk_workflow_runs_incident_id_incidents"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workflow_runs")),
        sa.UniqueConstraint(
            "id", "application_id", "repository_revision", name=op.f("uq_workflow_runs_id")
        ),
        sa.UniqueConstraint("id", "incident_id", name=op.f("uq_workflow_runs_id")),
        sa.UniqueConstraint("incident_id", "attempt", name=op.f("uq_workflow_runs_incident_id")),
    )
    op.create_index(
        "uq_workflow_runs_active_incident",
        "workflow_runs",
        ["incident_id"],
        unique=True,
        sqlite_where=sa.text(
            "state NOT IN ('resolved','rejected','unresolved','reported','manual_review','error')"
        ),
    )
    op.create_index(
        "uq_workflow_runs_applying_application",
        "workflow_runs",
        ["application_id"],
        unique=True,
        sqlite_where=sa.text("state IN ('applying','verifying','restoring')"),
    )
    op.create_table(
        "agent_executions",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("application_id", sa.String(length=64), nullable=False),
        sa.Column("input_revision", sa.String(length=128), nullable=False),
        sa.Column(
            "agent_type",
            sa.Enum(
                "manager",
                "monitoring",
                "diagnosis",
                "repair",
                "testing",
                "reporting",
                name="agent_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "idle",
                "running",
                "completed",
                "error",
                "offline",
                name="agent_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("output_artifact_id", sa.String(length=64), nullable=True),
        sa.Column("error_artifact_id", sa.String(length=64), nullable=True),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "schema_version = '1.0'", name=op.f("ck_agent_executions_schema_version")
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at >= created_at",
            name=op.f("ck_agent_executions_execution_time_order"),
        ),
        sa.CheckConstraint(
            "duration_ms >= 0", name=op.f("ck_agent_executions_duration_nonnegative")
        ),
        sa.CheckConstraint(
            "length(id) BETWEEN 1 AND 64", name=op.f("ck_agent_executions_id_length")
        ),
        sa.ForeignKeyConstraint(
            ["error_artifact_id"],
            ["artifacts.id"],
            name=op.f("fk_agent_executions_error_artifact_id_artifacts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["output_artifact_id"],
            ["artifacts.id"],
            name=op.f("fk_agent_executions_output_artifact_id_artifacts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "application_id", "input_revision"],
            [
                "workflow_runs.id",
                "workflow_runs.application_id",
                "workflow_runs.repository_revision",
            ],
            name=op.f("fk_agent_executions_run_id_workflow_runs"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_executions")),
    )
    op.create_index(
        "ix_agent_executions_run_type",
        "agent_executions",
        ["run_id", "agent_type", "created_at"],
        unique=False,
    )
    op.create_table(
        "audit_events",
        sa.Column("incident_id", sa.String(length=64), nullable=True),
        sa.Column("application_id", sa.String(length=64), nullable=True),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("actor_type", sa.String(length=16), nullable=False),
        sa.Column("actor_user_id", sa.String(length=64), nullable=True),
        sa.Column("actor_key", sa.String(length=128), nullable=False),
        sa.Column("payload_metadata", sa.JSON(), nullable=False),
        sa.Column("payload_artifact_id", sa.String(length=64), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "actor_type != 'human' OR actor_user_id IS NOT NULL",
            name=op.f("ck_audit_events_human_actor"),
        ),
        sa.CheckConstraint(
            "actor_type IN ('agent','human','system')", name=op.f("ck_audit_events_actor_type")
        ),
        sa.CheckConstraint("schema_version = '1.0'", name=op.f("ck_audit_events_schema_version")),
        sa.CheckConstraint(
            "incident_id IS NULL OR application_id IS NOT NULL",
            name=op.f("ck_audit_events_incident_requires_application"),
        ),
        sa.CheckConstraint("length(id) BETWEEN 1 AND 64", name=op.f("ck_audit_events_id_length")),
        sa.CheckConstraint(
            "run_id IS NULL OR incident_id IS NOT NULL",
            name=op.f("ck_audit_events_run_requires_incident"),
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_audit_events_actor_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_audit_events_application_id_applications"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["incident_id", "application_id"],
            ["incidents.id", "incidents.application_id"],
            name=op.f("fk_audit_events_incident_id_incidents"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["payload_artifact_id"],
            ["artifacts.id"],
            name=op.f("fk_audit_events_payload_artifact_id_artifacts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "incident_id"],
            ["workflow_runs.id", "workflow_runs.incident_id"],
            name=op.f("fk_audit_events_run_id_workflow_runs"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index(
        "ix_audit_events_application_occurred",
        "audit_events",
        ["application_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_events_incident_occurred",
        "audit_events",
        ["incident_id", "occurred_at"],
        unique=False,
    )
    op.create_table(
        "diagnoses",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("application_id", sa.String(length=64), nullable=False),
        sa.Column("repository_revision", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("hypothesis", sa.String(length=4000), nullable=False),
        sa.Column("confidence_label", sa.String(length=8), nullable=False),
        sa.Column("uncertainty", sa.String(length=2000), nullable=False),
        sa.Column("suggested_direction", sa.String(length=2000), nullable=False),
        sa.Column("result_artifact_id", sa.String(length=64), nullable=True),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence_label IN ('low','medium','high')",
            name=op.f("ck_diagnoses_confidence_label"),
        ),
        sa.CheckConstraint("schema_version = '1.0'", name=op.f("ck_diagnoses_schema_version")),
        sa.CheckConstraint(
            "status IN ('completed','manual_review')", name=op.f("ck_diagnoses_diagnosis_status")
        ),
        sa.CheckConstraint("length(id) BETWEEN 1 AND 64", name=op.f("ck_diagnoses_id_length")),
        sa.ForeignKeyConstraint(
            ["result_artifact_id"],
            ["artifacts.id"],
            name=op.f("fk_diagnoses_result_artifact_id_artifacts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "application_id", "repository_revision"],
            [
                "workflow_runs.id",
                "workflow_runs.application_id",
                "workflow_runs.repository_revision",
            ],
            name=op.f("fk_diagnoses_run_id_workflow_runs"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_diagnoses")),
        sa.UniqueConstraint(
            "id", "application_id", "repository_revision", name=op.f("uq_diagnoses_id")
        ),
        sa.UniqueConstraint("run_id", name=op.f("uq_diagnoses_run_id")),
    )
    op.create_table(
        "patch_candidates",
        sa.Column("incident_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("application_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("base_revision", sa.String(length=128), nullable=False),
        sa.Column("patch_hash", sa.String(length=71), nullable=False),
        sa.Column("changed_files", sa.JSON(), nullable=False),
        sa.Column("rationale", sa.String(length=4000), nullable=False),
        sa.Column("diff_artifact_id", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "proposed",
                "validated",
                "failed",
                "stale",
                "approved",
                "rejected",
                "applied",
                name="patch_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("supersedes_candidate_id", sa.String(length=64), nullable=True),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(patch_hash) = 71 AND substr(patch_hash,1,7) = 'sha256:' AN"
            "D substr(patch_hash,8) NOT GLOB '*[^0-9a-f]*'",
            name=op.f("ck_patch_candidates_patch_hash_format"),
        ),
        sa.CheckConstraint(
            "schema_version = '1.0'", name=op.f("ck_patch_candidates_schema_version")
        ),
        sa.CheckConstraint(
            "length(id) BETWEEN 1 AND 64", name=op.f("ck_patch_candidates_id_length")
        ),
        sa.CheckConstraint(
            "supersedes_candidate_id IS NULL OR supersedes_candidate_id != id",
            name=op.f("ck_patch_candidates_different_predecessor"),
        ),
        sa.CheckConstraint("version >= 1", name=op.f("ck_patch_candidates_version_positive")),
        sa.ForeignKeyConstraint(
            ["diff_artifact_id"],
            ["artifacts.id"],
            name=op.f("fk_patch_candidates_diff_artifact_id_artifacts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "application_id", "base_revision"],
            [
                "workflow_runs.id",
                "workflow_runs.application_id",
                "workflow_runs.repository_revision",
            ],
            name=op.f("fk_patch_candidates_run_id_workflow_runs"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "incident_id"],
            ["workflow_runs.id", "workflow_runs.incident_id"],
            name=op.f("fk_patch_candidates_run_id_workflow_runs"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_candidate_id", "incident_id"],
            ["patch_candidates.id", "patch_candidates.incident_id"],
            name=op.f("fk_patch_candidates_supersedes_candidate_id_patch_candidates"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_patch_candidates")),
        sa.UniqueConstraint("id", "application_id", name=op.f("uq_patch_candidates_id")),
        sa.UniqueConstraint(
            "id", "incident_id", "patch_hash", "base_revision", name=op.f("uq_patch_candidates_id")
        ),
        sa.UniqueConstraint("id", "incident_id", name=op.f("uq_patch_candidates_id")),
        sa.UniqueConstraint("id", "patch_hash", name=op.f("uq_patch_candidates_id")),
        sa.UniqueConstraint("incident_id", "version", name=op.f("uq_patch_candidates_incident_id")),
    )
    op.create_index(
        "ix_patch_candidates_incident_version",
        "patch_candidates",
        ["incident_id", "version"],
        unique=False,
    )
    op.create_table(
        "stage_transitions",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column(
            "from_state",
            sa.Enum(
                "detected",
                "diagnosing",
                "generating_patch",
                "validating",
                "revision_requested",
                "awaiting_approval",
                "approved",
                "applying",
                "verifying",
                "restoring",
                "resolved",
                "rejected",
                "manual_review",
                "unresolved",
                "error",
                "reported",
                name="from_state",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
        sa.Column(
            "to_state",
            sa.Enum(
                "detected",
                "diagnosing",
                "generating_patch",
                "validating",
                "revision_requested",
                "awaiting_approval",
                "approved",
                "applying",
                "verifying",
                "restoring",
                "resolved",
                "rejected",
                "manual_review",
                "unresolved",
                "error",
                "reported",
                name="to_state",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("reason", sa.String(length=2000), nullable=False),
        sa.Column("actor_user_id", sa.String(length=64), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "schema_version = '1.0'", name=op.f("ck_stage_transitions_schema_version")
        ),
        sa.CheckConstraint(
            "from_state IS NULL OR from_state != to_state",
            name=op.f("ck_stage_transitions_different_states"),
        ),
        sa.CheckConstraint(
            "length(id) BETWEEN 1 AND 64", name=op.f("ck_stage_transitions_id_length")
        ),
        sa.CheckConstraint("sequence >= 1", name=op.f("ck_stage_transitions_sequence_positive")),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_stage_transitions_actor_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["workflow_runs.id"],
            name=op.f("fk_stage_transitions_run_id_workflow_runs"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stage_transitions")),
        sa.UniqueConstraint("run_id", "sequence", name=op.f("uq_stage_transitions_run_id")),
    )
    op.create_table(
        "evidence_references",
        sa.Column("diagnosis_id", sa.String(length=64), nullable=False),
        sa.Column("code_index_entry_id", sa.String(length=64), nullable=False),
        sa.Column("application_id", sa.String(length=64), nullable=False),
        sa.Column("repository_revision", sa.String(length=128), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "schema_version = '1.0'", name=op.f("ck_evidence_references_schema_version")
        ),
        sa.CheckConstraint(
            "length(id) BETWEEN 1 AND 64", name=op.f("ck_evidence_references_id_length")
        ),
        sa.ForeignKeyConstraint(
            ["code_index_entry_id", "application_id", "repository_revision"],
            [
                "code_index_entries.id",
                "code_index_entries.application_id",
                "code_index_entries.repository_revision",
            ],
            name=op.f("fk_evidence_references_code_index_entry_id_code_index_entries"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["diagnosis_id", "application_id", "repository_revision"],
            ["diagnoses.id", "diagnoses.application_id", "diagnoses.repository_revision"],
            name=op.f("fk_evidence_references_diagnosis_id_diagnoses"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence_references")),
        sa.UniqueConstraint(
            "diagnosis_id", "code_index_entry_id", name=op.f("uq_evidence_references_diagnosis_id")
        ),
    )
    op.create_table(
        "validation_results",
        sa.Column("candidate_id", sa.String(length=64), nullable=False),
        sa.Column("patch_hash", sa.String(length=71), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "passed",
                "failed",
                "error",
                "timeout",
                "not_run",
                name="check_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("environment_id", sa.String(length=128), nullable=False),
        sa.Column("evidence_artifact_id", sa.String(length=64), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(patch_hash) = 71 AND substr(patch_hash,1,7) = 'sha256:' AN"
            "D substr(patch_hash,8) NOT GLOB '*[^0-9a-f]*'",
            name=op.f("ck_validation_results_patch_hash_format"),
        ),
        sa.CheckConstraint(
            "schema_version = '1.0'", name=op.f("ck_validation_results_schema_version")
        ),
        sa.CheckConstraint(
            "duration_ms >= 0", name=op.f("ck_validation_results_duration_nonnegative")
        ),
        sa.CheckConstraint(
            "length(id) BETWEEN 1 AND 64", name=op.f("ck_validation_results_id_length")
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id", "patch_hash"],
            ["patch_candidates.id", "patch_candidates.patch_hash"],
            name=op.f("fk_validation_results_candidate_id_patch_candidates"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_artifact_id"],
            ["artifacts.id"],
            name=op.f("fk_validation_results_evidence_artifact_id_artifacts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_validation_results")),
        sa.UniqueConstraint(
            "id", "candidate_id", "patch_hash", "status", name=op.f("uq_validation_results_id")
        ),
    )
    op.create_index(
        "ix_validation_results_candidate_created",
        "validation_results",
        ["candidate_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "approval_decisions",
        sa.Column("incident_id", sa.String(length=64), nullable=False),
        sa.Column("candidate_id", sa.String(length=64), nullable=False),
        sa.Column("patch_hash", sa.String(length=71), nullable=False),
        sa.Column("base_revision", sa.String(length=128), nullable=False),
        sa.Column("decision", sa.String(length=8), nullable=False),
        sa.Column("actor_id", sa.String(length=64), nullable=False),
        sa.Column("validation_id", sa.String(length=64), nullable=True),
        sa.Column(
            "validation_status",
            sa.Enum(
                "passed",
                "failed",
                "error",
                "timeout",
                "not_run",
                name="validation_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
        sa.Column("comment", sa.String(length=2000), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "decision != 'approve' OR (validation_id IS NOT NULL AND validation_status = 'passed')",
            name=op.f("ck_approval_decisions_approve_requires_passed_validation"),
        ),
        sa.CheckConstraint(
            "decision IN ('approve','reject')", name=op.f("ck_approval_decisions_decision")
        ),
        sa.CheckConstraint(
            "length(patch_hash) = 71 AND substr(patch_hash,1,7) = 'sha256:' AN"
            "D substr(patch_hash,8) NOT GLOB '*[^0-9a-f]*'",
            name=op.f("ck_approval_decisions_patch_hash_format"),
        ),
        sa.CheckConstraint(
            "schema_version = '1.0'", name=op.f("ck_approval_decisions_schema_version")
        ),
        sa.CheckConstraint(
            "(validation_id IS NULL AND validation_status IS NULL) OR (validat"
            "ion_id IS NOT NULL AND validation_status IS NOT NULL)",
            name=op.f("ck_approval_decisions_validation_pair"),
        ),
        sa.CheckConstraint(
            "length(comment) <= 2000", name=op.f("ck_approval_decisions_comment_length")
        ),
        sa.CheckConstraint(
            "length(id) BETWEEN 1 AND 64", name=op.f("ck_approval_decisions_id_length")
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name=op.f("fk_approval_decisions_actor_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id", "incident_id", "patch_hash", "base_revision"],
            [
                "patch_candidates.id",
                "patch_candidates.incident_id",
                "patch_candidates.patch_hash",
                "patch_candidates.base_revision",
            ],
            name=op.f("fk_approval_decisions_candidate_id_patch_candidates"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["validation_id", "candidate_id", "patch_hash", "validation_status"],
            [
                "validation_results.id",
                "validation_results.candidate_id",
                "validation_results.patch_hash",
                "validation_results.status",
            ],
            name=op.f("fk_approval_decisions_validation_id_validation_results"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approval_decisions")),
        sa.UniqueConstraint("candidate_id", name=op.f("uq_approval_decisions_candidate_id")),
        sa.UniqueConstraint(
            "id",
            "candidate_id",
            "patch_hash",
            "base_revision",
            "decision",
            name=op.f("uq_approval_decisions_id"),
        ),
    )
    op.create_table(
        "validation_checks",
        sa.Column("validation_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "passed",
                "failed",
                "error",
                "timeout",
                "not_run",
                name="check_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("evidence_artifact_id", sa.String(length=64), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "schema_version = '1.0'", name=op.f("ck_validation_checks_schema_version")
        ),
        sa.CheckConstraint(
            "status != 'passed' OR (exit_code IS NOT NULL AND exit_code = 0)",
            name=op.f("ck_validation_checks_passed_exit_zero"),
        ),
        sa.CheckConstraint(
            "duration_ms >= 0", name=op.f("ck_validation_checks_duration_nonnegative")
        ),
        sa.CheckConstraint(
            "length(id) BETWEEN 1 AND 64", name=op.f("ck_validation_checks_id_length")
        ),
        sa.ForeignKeyConstraint(
            ["evidence_artifact_id"],
            ["artifacts.id"],
            name=op.f("fk_validation_checks_evidence_artifact_id_artifacts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["validation_id"],
            ["validation_results.id"],
            name=op.f("fk_validation_checks_validation_id_validation_results"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_validation_checks")),
        sa.UniqueConstraint(
            "validation_id", "name", name=op.f("uq_validation_checks_validation_id")
        ),
    )
    op.create_table(
        "application_attempts",
        sa.Column("application_id", sa.String(length=64), nullable=False),
        sa.Column("candidate_id", sa.String(length=64), nullable=False),
        sa.Column("approval_id", sa.String(length=64), nullable=False),
        sa.Column("approval_decision", sa.String(length=8), nullable=False),
        sa.Column("patch_hash", sa.String(length=71), nullable=False),
        sa.Column("before_revision", sa.String(length=128), nullable=False),
        sa.Column("after_revision", sa.String(length=128), nullable=True),
        sa.Column("snapshot_artifact_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("applied_at", sa.DateTime(), nullable=False),
        sa.Column("restore_status", sa.String(length=16), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "approval_decision = 'approve'",
            name=op.f("ck_application_attempts_approved_decision_only"),
        ),
        sa.CheckConstraint(
            "length(patch_hash) = 71 AND substr(patch_hash,1,7) = 'sha256:' AN"
            "D substr(patch_hash,8) NOT GLOB '*[^0-9a-f]*'",
            name=op.f("ck_application_attempts_patch_hash_format"),
        ),
        sa.CheckConstraint(
            "restore_status IN ('not_needed','restored','manual_action')",
            name=op.f("ck_application_attempts_restore_status"),
        ),
        sa.CheckConstraint(
            "schema_version = '1.0'", name=op.f("ck_application_attempts_schema_version")
        ),
        sa.CheckConstraint(
            "status != 'resolved' OR after_revision IS NOT NULL",
            name=op.f("ck_application_attempts_resolved_revision"),
        ),
        sa.CheckConstraint(
            "status IN ('applying','verifying','resolved','unresolved')",
            name=op.f("ck_application_attempts_attempt_status"),
        ),
        sa.CheckConstraint(
            "length(id) BETWEEN 1 AND 64", name=op.f("ck_application_attempts_id_length")
        ),
        sa.ForeignKeyConstraint(
            ["application_id", "after_revision"],
            ["repository_revisions.application_id", "repository_revisions.revision"],
            name=op.f("fk_application_attempts_application_id_repository_revisions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["approval_id", "candidate_id", "patch_hash", "before_revision", "approval_decision"],
            [
                "approval_decisions.id",
                "approval_decisions.candidate_id",
                "approval_decisions.patch_hash",
                "approval_decisions.base_revision",
                "approval_decisions.decision",
            ],
            name=op.f("fk_application_attempts_approval_id_approval_decisions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id", "application_id"],
            ["patch_candidates.id", "patch_candidates.application_id"],
            name=op.f("fk_application_attempts_candidate_id_patch_candidates"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_artifact_id"],
            ["artifacts.id"],
            name=op.f("fk_application_attempts_snapshot_artifact_id_artifacts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_application_attempts")),
        sa.UniqueConstraint("approval_id", name=op.f("uq_application_attempts_approval_id")),
        sa.UniqueConstraint("id", "candidate_id", name=op.f("uq_application_attempts_id")),
    )
    op.create_index(
        "uq_application_attempts_active_application",
        "application_attempts",
        ["application_id"],
        unique=True,
        sqlite_where=sa.text("status IN ('applying','verifying')"),
    )
    op.create_table(
        "verification_results",
        sa.Column("application_attempt_id", sa.String(length=64), nullable=False),
        sa.Column("candidate_id", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "passed",
                "failed",
                "error",
                "timeout",
                "not_run",
                name="check_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("monitoring_observation", sa.String(length=2000), nullable=False),
        sa.Column("evidence_artifact_id", sa.String(length=64), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "schema_version = '1.0'", name=op.f("ck_verification_results_schema_version")
        ),
        sa.CheckConstraint(
            "duration_ms >= 0", name=op.f("ck_verification_results_duration_nonnegative")
        ),
        sa.CheckConstraint(
            "length(id) BETWEEN 1 AND 64", name=op.f("ck_verification_results_id_length")
        ),
        sa.ForeignKeyConstraint(
            ["application_attempt_id", "candidate_id"],
            ["application_attempts.id", "application_attempts.candidate_id"],
            name=op.f("fk_verification_results_application_attempt_id_application_attempts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_artifact_id"],
            ["artifacts.id"],
            name=op.f("fk_verification_results_evidence_artifact_id_artifacts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_verification_results")),
    )
    op.create_index(
        "ix_verification_results_attempt_created",
        "verification_results",
        ["application_attempt_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "verification_checks",
        sa.Column("verification_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "passed",
                "failed",
                "error",
                "timeout",
                "not_run",
                name="check_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("evidence_artifact_id", sa.String(length=64), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=8), server_default="1.0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "schema_version = '1.0'", name=op.f("ck_verification_checks_schema_version")
        ),
        sa.CheckConstraint(
            "status != 'passed' OR (exit_code IS NOT NULL AND exit_code = 0)",
            name=op.f("ck_verification_checks_passed_exit_zero"),
        ),
        sa.CheckConstraint(
            "duration_ms >= 0", name=op.f("ck_verification_checks_duration_nonnegative")
        ),
        sa.CheckConstraint(
            "length(id) BETWEEN 1 AND 64", name=op.f("ck_verification_checks_id_length")
        ),
        sa.ForeignKeyConstraint(
            ["evidence_artifact_id"],
            ["artifacts.id"],
            name=op.f("fk_verification_checks_evidence_artifact_id_artifacts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["verification_id"],
            ["verification_results.id"],
            name=op.f("fk_verification_checks_verification_id_verification_results"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_verification_checks")),
        sa.UniqueConstraint(
            "verification_id", "name", name=op.f("uq_verification_checks_verification_id")
        ),
    )


def downgrade() -> None:
    # Refuse destructive downgrades of populated databases. Never silently discard history.
    if context.is_offline_mode():
        raise RuntimeError("Domain downgrade requires online data-safety checks.")
    connection = op.get_bind()
    for table in DOMAIN_TABLES:
        if connection.scalar(sa.text(f'SELECT 1 FROM "{table}" LIMIT 1')):
            raise RuntimeError("Domain data exists; downgrade refused. Back up/export first.")
    op.drop_table("verification_checks")
    op.drop_index("ix_verification_results_attempt_created", table_name="verification_results")
    op.drop_table("verification_results")
    op.drop_index(
        "uq_application_attempts_active_application",
        table_name="application_attempts",
        sqlite_where=sa.text("status IN ('applying','verifying')"),
    )
    op.drop_table("application_attempts")
    op.drop_table("validation_checks")
    op.drop_table("approval_decisions")
    op.drop_index("ix_validation_results_candidate_created", table_name="validation_results")
    op.drop_table("validation_results")
    op.drop_table("evidence_references")
    op.drop_table("stage_transitions")
    op.drop_index("ix_patch_candidates_incident_version", table_name="patch_candidates")
    op.drop_table("patch_candidates")
    op.drop_table("diagnoses")
    op.drop_index("ix_audit_events_incident_occurred", table_name="audit_events")
    op.drop_index("ix_audit_events_application_occurred", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_agent_executions_run_type", table_name="agent_executions")
    op.drop_table("agent_executions")
    op.drop_index(
        "uq_workflow_runs_applying_application",
        table_name="workflow_runs",
        sqlite_where=sa.text("state IN ('applying','verifying','restoring')"),
    )
    op.drop_index(
        "uq_workflow_runs_active_incident",
        table_name="workflow_runs",
        sqlite_where=sa.text(
            "state NOT IN ('resolved','rejected','unresolved','reported','manual_review','error')"
        ),
    )
    op.drop_table("workflow_runs")
    op.drop_index("ix_incident_reports_incident_generated", table_name="incident_reports")
    op.drop_table("incident_reports")
    op.drop_index("ix_incident_monitoring_events_incident", table_name="incident_monitoring_events")
    op.drop_table("incident_monitoring_events")
    op.drop_index(
        "uq_incidents_active_fingerprint",
        table_name="incidents",
        sqlite_where=sa.text("status NOT IN ('resolved','rejected','unresolved','reported')"),
    )
    op.drop_index("ix_incidents_application_status_detected", table_name="incidents")
    op.drop_table("incidents")
    op.drop_index("ix_monitoring_events_application_fingerprint", table_name="monitoring_events")
    op.drop_table("monitoring_events")
    op.drop_table("code_index_entries")
    op.drop_table("application_revisions")
    op.drop_table("user_roles")
    op.drop_table("repository_revisions")
    op.drop_table("idempotency_records")
    op.drop_index(op.f("ix_auth_sessions_user_id"), table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_table("users")
    op.drop_table("roles")
    op.drop_table("backend_settings")
    op.drop_table("artifacts")
    op.drop_table("applications")
