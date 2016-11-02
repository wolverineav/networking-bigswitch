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

class NameCache(model_base.BASEV2):
    '''
    This table is used to cache names of various objects that have <space> in
    their names.
    '''
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


class NameCacheHandler(model_base.BASEV2):
    '''
    A wrapper object to keep track of the session between the read
    and the update operations.

    This class needs an SQL engine completely independent of the main
    neutron connection so rollbacks from consistency hash operations don't
    affect the parent sessions.

    Similar to HashHandler for ConsistencyDb
    '''
    _FACADE = None

    def __init__(self):
        # create a session for accessing the namecache objects from the DB
        if NameCacheHandler._FACADE is None:
            NameCacheHandler._FACADE = session.EngineFacade.from_config(
                cfg.CONF, sqlite_fk=True)
        self.session = (NameCacheHandler._FACADE
                        .get_session(autocommit=True, expire_on_commit=False))

    # this will try and update the cache with the object specified
    # returns a tuple (bool success, string name_nospace)
    def create(self, obj_type, name):
        # try the update here:
        with self.session.begin(subtransactions=True):
            name_nospace = ''
            if name is not None:
                name_nospace = name.replace(' ', '_')
            namecache_obj = NameCache(obj_type=obj_type, name=name,
                                      name_nospace=name_nospace)
            try:
                self.session.add(namecache_obj)
                self.session.commit()
                return namecache_obj
            except:
                self.session.rollback()
                return None

    # given the obj type and name_nospace, return a tuple
    # (bool success, string name)
    def get(self, obj_type, name_nospace):
        # try and return the mapping if available:
        with self.session.begin(subtransactions=True):
            try:
                result = (self.session.query(NameCache)
                          .filter_by(obj_type=obj_type,
                                     name_nospace=name_nospace)
                          .first())
                return result
            except:
                return None

    def delete(self, obj_type, name_nospace):
        with self.session.begin(subtransaction=True):
            try:
                namespace_obj = self.get(obj_type, name_nospace)
                if not namespace_obj:
                    return
                self.session.delete(namespace_obj)
                self.session.commit()
            except:
                self.session.rollback()
