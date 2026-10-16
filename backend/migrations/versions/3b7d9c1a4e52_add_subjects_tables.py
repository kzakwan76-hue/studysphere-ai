"""add subjects tables

Revision ID: 3b7d9c1a4e52
Revises: 66eaa1e25439
"""

import sqlalchemy as sa
from alembic import op

revision = "3b7d9c1a4e52"
down_revision = "66eaa1e25439"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_subjects_user_id_name"),
    )
    op.create_index(op.f("ix_subjects_user_id"), "subjects", ["user_id"], unique=False)
    op.create_table(
        "subject_documents",
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("document_id"),
    )
    op.create_index(op.f("ix_subject_documents_subject_id"), "subject_documents", ["subject_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_subject_documents_subject_id"), table_name="subject_documents")
    op.drop_table("subject_documents")
    op.drop_index(op.f("ix_subjects_user_id"), table_name="subjects")
    op.drop_table("subjects")