# Copyright 2016, Big Switch Networks
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License

"""add bsn name cache

Revision ID: e6cb930d25de
Revises: 1ef57200f387
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
        sa.Column('obj_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('name_nospace', sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint('obj_type', 'obj_id', name='bsn_namecache_pk'))


def downgrade():
    pass
