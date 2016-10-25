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
#    under the License.

import sqlalchemy as sa
from oslo_log import log as logging
from sqlalchemy.types import Enum

from neutron.db import model_base

LOG = logging.getLogger(__name__)


# This table is used to cache names of various objects that have <space> in
# their names.
class NameCache(model_base.BASEV2):
    __tablename__ = 'bsn_namecache'
    # this is an enum specifying the type of object being renamed
    obj_type = sa.Column(Enum("tenant",
                              "network",
                              "security_group",
                              name="obj_type"), nullable=False)
    # name and name_nospace both aren't unique, but the composite obj with
    # the whole row is unique
    name = sa.Column(sa.String(255), nullable=False, unique=False)
    name_nospace = sa.Column(sa.String(255), nullable=False, unique=False)

    class Meta(object):
        unique_together = ('obj_type', 'name', 'name_nospace')
