"""pilot operations and trust layer

Revision ID: 2c19d6c4b7aa
Revises: 1e37a7efe47c
Create Date: 2026-09-17
"""

from alembic import op
import sqlalchemy as sa

revision = "2c19d6c4b7aa"
down_revision = "1e37a7efe47c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("technician_profiles") as batch:
        batch.add_column(sa.Column("network_approved", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("latitude", sa.Float(), nullable=True))
        batch.add_column(sa.Column("longitude", sa.Float(), nullable=True))
        batch.add_column(sa.Column("service_radius_km", sa.Float(), nullable=False, server_default="15"))
    op.create_index("ix_technician_profiles_network_approved", "technician_profiles", ["network_approved"])

    with op.batch_alter_table("repair_requests") as batch:
        batch.add_column(sa.Column("assigned_technician_id", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_foreign_key(
            "fk_repair_requests_assigned_technician",
            "technician_profiles",
            ["assigned_technician_id"],
            ["id"],
        )
    op.create_index("ix_repair_requests_assigned_technician_id", "repair_requests", ["assigned_technician_id"])
    op.execute("UPDATE repair_requests SET updated_at = created_at WHERE updated_at IS NULL")

    with op.batch_alter_table("payment_intents") as batch:
        batch.add_column(sa.Column("platform_fee_amount", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("technician_amount", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("receipt_number", sa.String(length=80), nullable=True))
        batch.add_column(sa.Column("transaction_date", sa.String(length=40), nullable=True))

    op.create_table(
        "repair_evidence",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("repair_request_id", sa.String(length=36), nullable=False),
        sa.Column("uploaded_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("stage", sa.String(length=20), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("object_key", sa.String(length=255), nullable=False, unique=True),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["repair_request_id"], ["repair_requests.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"]),
    )
    op.create_index("ix_repair_evidence_repair_request_id", "repair_evidence", ["repair_request_id"])
    op.create_index("ix_repair_evidence_uploaded_by_user_id", "repair_evidence", ["uploaded_by_user_id"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("repair_request_id", sa.String(length=36), nullable=True),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["repair_request_id"], ["repair_requests.id"]),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_repair_request_id", "notifications", ["repair_request_id"])

    op.create_table(
        "reviews",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("repair_request_id", sa.String(length=36), nullable=False, unique=True),
        sa.Column("customer_id", sa.String(length=36), nullable=False),
        sa.Column("technician_id", sa.String(length=36), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["repair_request_id"], ["repair_requests.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["technician_id"], ["technician_profiles.id"]),
    )
    op.create_index("ix_reviews_repair_request_id", "reviews", ["repair_request_id"])
    op.create_index("ix_reviews_customer_id", "reviews", ["customer_id"])
    op.create_index("ix_reviews_technician_id", "reviews", ["technician_id"])

    op.create_table(
        "disputes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("repair_request_id", sa.String(length=36), nullable=False, unique=True),
        sa.Column("opened_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("reason", sa.String(length=60), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="open"),
        sa.Column("resolution", sa.Text(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["repair_request_id"], ["repair_requests.id"]),
        sa.ForeignKeyConstraint(["opened_by_user_id"], ["users.id"]),
    )
    op.create_index("ix_disputes_repair_request_id", "disputes", ["repair_request_id"])
    op.create_index("ix_disputes_opened_by_user_id", "disputes", ["opened_by_user_id"])
    op.create_index("ix_disputes_status", "disputes", ["status"])

    op.create_table(
        "technician_payouts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("repair_request_id", sa.String(length=36), nullable=False, unique=True),
        sa.Column("technician_id", sa.String(length=36), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["repair_request_id"], ["repair_requests.id"]),
        sa.ForeignKeyConstraint(["technician_id"], ["technician_profiles.id"]),
    )
    op.create_index("ix_technician_payouts_repair_request_id", "technician_payouts", ["repair_request_id"])
    op.create_index("ix_technician_payouts_technician_id", "technician_payouts", ["technician_id"])
    op.create_index("ix_technician_payouts_status", "technician_payouts", ["status"])


def downgrade() -> None:
    op.drop_index("ix_technician_payouts_status", table_name="technician_payouts")
    op.drop_index("ix_technician_payouts_technician_id", table_name="technician_payouts")
    op.drop_index("ix_technician_payouts_repair_request_id", table_name="technician_payouts")
    op.drop_table("technician_payouts")
    op.drop_index("ix_disputes_status", table_name="disputes")
    op.drop_index("ix_disputes_opened_by_user_id", table_name="disputes")
    op.drop_index("ix_disputes_repair_request_id", table_name="disputes")
    op.drop_table("disputes")
    op.drop_index("ix_reviews_technician_id", table_name="reviews")
    op.drop_index("ix_reviews_customer_id", table_name="reviews")
    op.drop_index("ix_reviews_repair_request_id", table_name="reviews")
    op.drop_table("reviews")
    op.drop_index("ix_notifications_repair_request_id", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_repair_evidence_uploaded_by_user_id", table_name="repair_evidence")
    op.drop_index("ix_repair_evidence_repair_request_id", table_name="repair_evidence")
    op.drop_table("repair_evidence")
    with op.batch_alter_table("payment_intents") as batch:
        batch.drop_column("transaction_date")
        batch.drop_column("receipt_number")
        batch.drop_column("technician_amount")
        batch.drop_column("platform_fee_amount")
    op.drop_index("ix_repair_requests_assigned_technician_id", table_name="repair_requests")
    with op.batch_alter_table("repair_requests") as batch:
        batch.drop_constraint("fk_repair_requests_assigned_technician", type_="foreignkey")
        batch.drop_column("updated_at")
        batch.drop_column("assigned_technician_id")
    op.drop_index("ix_technician_profiles_network_approved", table_name="technician_profiles")
    with op.batch_alter_table("technician_profiles") as batch:
        batch.drop_column("service_radius_km")
        batch.drop_column("longitude")
        batch.drop_column("latitude")
        batch.drop_column("network_approved")
