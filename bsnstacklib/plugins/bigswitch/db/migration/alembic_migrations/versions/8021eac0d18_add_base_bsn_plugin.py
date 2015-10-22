"""add base BSN plugin

Revision ID: 8021eac0d18
Revises: 
Create Date: 2016-01-04 17:59:34.311932

"""

# revision identifiers, used by Alembic.
revision = '8021eac0d18'
down_revision = None
branch_labels = None
depends_on = None

import sqlalchemy as sa

from alembic import op

from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.mysql.base import VARCHAR
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import Enum, TIMESTAMP, TypeDecorator
from sqlalchemy import Table, Column, ForeignKey, func, Integer

class JSONEncodedDict(TypeDecorator):
    """Represents an immutable structure as a json-encoded string.
    Usage::
        JSONEncodedDict(255)
    """
    impl = VARCHAR
    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value

def upgrade():
    op.create_table(
        'networktemplates',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('template_name', sa.String(255), nullable=False, unique=True))

    op.create_table(
        'networktemplateassignments',
        sa.Column('template_id', sa.Integer, sa.ForeignKey('networktemplates.id'),
                  nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False, primary_key=True),
        sa.Column('stack_id', sa.String(255), nullable=False))

    op.create_table(
        'reachabilitytest',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('test_id', sa.String(64), nullable=False),
        sa.Column('src_tenant_id', sa.String(64), nullable=False),
        sa.Column('src_segment_id', sa.String(64), nullable=False),
        sa.Column('src_ip', sa.String(16), nullable=False),
        sa.Column('dst_tenant_id', sa.String(64), nullable=False),
        sa.Column('dst_segment_id', sa.String(64), nullable=False),
        sa.Column('dst_ip', sa.String(16), nullable=False),
        sa.Column('expected_result',
                  Enum("reached destination", "dropped by route",
                       "dropped by policy", "dropped due to private segment",
                       "packet in", "forwarded", "dropped", "multiple sources",
                       "unsupported", "invalid input", name="expected_result"),
                  nullable=False))

    op.create_table(
        'reachabilitytestresult',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('test_primary_key', sa.Integer,
                  sa.ForeignKey('reachabilitytest.id'), nullable=False),
        sa.Column('tenant_id', sa.String(64), nullable=False),
        sa.Column('test_id', sa.String(64), nullable=False),
        sa.Column('test_time', TIMESTAMP(timezone=True), nullable=False,
                  default=func.now()),
        sa.Column('test_result', Enum("pass", "fail", "pending"),
                  nullable=False),
        sa.Column('detail', JSONEncodedDict(8192), nullable=True))


def downgrade():
    pass
