"""Baseline migration infrastructure. Domain tables belong to Phase 2."""

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """There are no domain tables in the foundation baseline."""


def downgrade() -> None:
    """No domain objects were introduced by this revision."""
