"""Create messages_pairs table

Revision ID: 003_create_settings
Revises: 002_create_messages_pairs
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_create_settings"
down_revision: Union[str, None] = "002_create_messages_pairs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create settings table
    op.create_table(
        "settings",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=False, start=1, increment=1),
            nullable=False,
        ),
        sa.Column("group_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "values", sa.NVARCHAR(length=None), nullable=False, server_default="'{}'"
        ),
        sa.Column(
            "last_update",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("GETDATE()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add unique constraint on group_id
    op.create_unique_constraint("uq_settings_group_id", "settings", ["group_id"])

    # Add index for faster queries
    op.create_index("ix_settings_group_id", "settings", ["group_id"])


def downgrade() -> None:
    op.drop_index("ix_settings_group_id", table_name="settings")
    op.drop_constraint("uq_settings_group_id", "settings", type_="unique")
    op.drop_table("settings")
