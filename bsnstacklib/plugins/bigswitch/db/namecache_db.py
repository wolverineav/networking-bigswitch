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

from neutron.common import exceptions
from neutron.db import model_base
from oslo_config import cfg
from oslo_db import exception as db_exc
from oslo_db.sqlalchemy import session
from oslo_log import log as logging
from sqlalchemy.types import Enum

LOG = logging.getLogger(__name__)


class ObjectNameNotUnique(exceptions.NeutronException):
    message = _("Object type %(obj_type)s of name %(name_nospace)s is not "
                "unique.")
    status = None

    def __init__(self, **kwargs):
        self.obj_type = kwargs.get('obj_type')
        self.name_nospace = kwargs.get('name_nospace')
        super(TenantIDNotFound, self).__init__(**kwargs)


class ObjTypeEnum(Enum):
    network = "network"
    router = "router"
    security_group = "security_group"
    tenant = "tenant"


class NameCache(model_base.BASEV2):
    '''
    This table is used to cache names of various objects that have <space> in
    their names.
    '''
    __tablename__ = 'bsn_namecache'
    # this is an enum specifying the type of object being renamed
    obj_type = sa.Column(ObjTypeEnum(name="obj_type"), nullable=False,
                         primary_key=True)
    # uuid for the given obj type
    obj_id = sa.Column(sa.String(36), nullable=False, primary_key=True)
    # name and name_nospace both aren't unique, but the composite obj with
    # the whole row is unique
    name = sa.Column(sa.String(255), nullable=False, unique=False)
    name_nospace = sa.Column(sa.String(255), nullable=False, unique=False)

    class Meta(object):
        unique_together = ('obj_type', 'name_nospace')


class NameCacheHandler(object):
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
    def create(self, obj_type, obj_id, name):
        name_nospace = ''
        if name is not None:
            name_nospace = name.replace(' ', '_')
        namecache_obj = NameCache(obj_type=obj_type, obj_id=obj_id, name=name,
                                  name_nospace=name_nospace)
        try:
            with self.session.begin(subtransactions=True):
                LOG.debug("creating object namecache with %s" %
                          str(namecache_obj))
                self.session.add(namecache_obj)
                return namecache_obj
        except db_exc.DBDuplicateEntry:
            raise ObjectNameNotUnique(obj_type=obj_type,
                                      name_nospace=namecache_obj.name_nospace)
        except Exception as e:
            LOG.debug('exception while create ' + str(e))
            raise e

    # given the obj type and obj_id, return the unique object or None
    def get(self, obj_type, obj_id):
        # try and return the mapping if available:
        with self.session.begin(subtransactions=True):
            try:
                result = (self.session.query(NameCache)
                          .filter_by(obj_type=obj_type,
                                     obj_id=obj_id)
                          .first())
                LOG.debug("returning a namecache object %s" % result)
                return result
            except Exception:
                return None

    def delete(self, obj_type, obj_id):
        with self.session.begin(subtransactions=True):
            try:
                namespace_obj = self.get(obj_type, obj_id)
                if not namespace_obj:
                    # object does not exist, return
                    LOG.debug('obj not found. nothing to delete')
                    return
                self.session.delete(namespace_obj)
            except Exception as e:
                LOG.debug('exception while delete ' + str(e))
                raise e
