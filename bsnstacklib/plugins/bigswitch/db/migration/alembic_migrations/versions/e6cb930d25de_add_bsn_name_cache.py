"""add bsn name cache

Revision ID: e6cb930d25de
Revises: 8f6787d31990
Create Date: 2016-10-24 12:03:09.991235

"""

# revision identifiers, used by Alembic.
revision = 'e6cb930d25de'
down_revision = '1ef57200f387'
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op
from sqlalchemy.types import Enum


def upgrade():
    op.create_table(
        'bsn_namecache',
        sa.Column('obj_type', Enum("tenant", "network",
                                   "security_group", name="obj_type"),
                  nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('name_nospace', sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint('obj_type', 'name', 'name_nospace',
                                name='bsn_namecache_pk'))


def downgrade():
    pass
