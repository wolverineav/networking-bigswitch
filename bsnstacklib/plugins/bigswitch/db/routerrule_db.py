# Copyright 2013, Big Switch Networks
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
#    under the License.

import sqlalchemy as sa
from sqlalchemy import orm

from neutron.db import api as db_api
from neutron.db import model_base


def setup_db():
    if BsnRouterRule._TEST_TABLE_SETUP:
        return
    engine = db_api.get_engine()
    BsnRouterRule.metadata.create_all(engine)
    BsnNextHop.metadata.create_all(engine)
    BsnRouterRule._TEST_TABLE_SETUP = True


def clear_db():
    if not BsnRouterRule._TEST_TABLE_SETUP:
        return
    engine = db_api.get_engine()
    with engine.begin() as conn:
        for table in reversed(
                model_base.BASEV2.metadata.sorted_tables):
            conn.execute(table.delete())


class BsnRouterRule(model_base.BASEV2,
                    model_base.HasTenant):
    # TODO(wolverineav) do a proper fix for this setup and clear db hack
    _TEST_TABLE_SETUP = None

    __tablename__ = 'bsn_routerrules'
    id = sa.Column(sa.Integer, primary_key=True)
    priority = sa.Column(sa.Integer, nullable=False)
    source = sa.Column(sa.String(64), nullable=False)
    destination = sa.Column(sa.String(64), nullable=False)
    nexthops = orm.relationship('BsnNextHop',
                                cascade='all,delete,delete-orphan')
    action = sa.Column(sa.String(10), nullable=False)
    router_id = sa.Column(sa.String(36),
                          sa.ForeignKey('routers.id',
                                        ondelete="CASCADE"))

    class Meta(object):
        unique_together = ('priority', 'tenant_id')


class BsnNextHop(model_base.BASEV2):
    __tablename__ = 'bsn_nexthops'
    rule_id = sa.Column(sa.Integer,
                        sa.ForeignKey('bsn_routerrules.id',
                                      ondelete="CASCADE"),
                        primary_key=True)
    nexthop = sa.Column(sa.String(64), nullable=False, primary_key=True)
