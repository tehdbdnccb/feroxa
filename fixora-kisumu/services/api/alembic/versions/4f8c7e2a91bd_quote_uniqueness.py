"""enforce one quote per repair

Revision ID: 4f8c7e2a91bd
Revises: 2c19d6c4b7aa
Create Date: 2026-09-17
"""
from alembic import op

revision = "4f8c7e2a91bd"
down_revision = "2c19d6c4b7aa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("uq_quotes_repair_request_id", "quotes", ["repair_request_id"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_quotes_repair_request_id", table_name="quotes")
