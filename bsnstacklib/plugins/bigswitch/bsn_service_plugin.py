# Copyright 2011 OpenStack Foundation.
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

from neutron.callbacks import events
from neutron.callbacks import registry
from neutron.callbacks import resources
from neutron import context
from neutron.db import common_db_mixin
from neutron.services import service_base
from oslo_serialization import jsonutils

from oslo_log import log

from bsnstacklib.plugins.bigswitch import servermanager
from bsnstacklib.plugins.bigswitch.extensions import bsnserviceextension

from bsnstacklib.plugins.bigswitch.db import network_template_db
from bsnstacklib.plugins.bigswitch.db import reachability_test_db
from bsnstacklib.plugins.bigswitch import servermanager

LOG = log.getLogger(__name__)

class BSNServicePlugin(service_base.ServicePluginBase,
                       bsnserviceextension.BSNServicePluginBase,
                       common_db_mixin.CommonDbMixin):

    supported_extension_aliases = ["bsn-service-extension"]

    def __init__(self):
        super(BSNServicePlugin, self).__init__()
        # initialize BCF server handler
        self.servers = servermanager.ServerPool.get_instance()

    def get_plugin_type(self):
        # Tell Neutron this is a BSN service plugin
        return 'BSNSERVICEPLUGIN'

    def get_plugin_name(self):
        return 'bsn_service_extension'

    def get_plugin_description(self):
        return "BSN Service Plugin"

    def _make_network_template_dict(self, template, fields=None):
        return self._fields({
            'id' : template.id,
            'tenant_id': template.tenant_id,
            'body': template.body,
            'template_name' : template.template_name
            }, fields)

    def _make_network_template_assignment_dict(self, template_assignment,
                                               template, fields=None):
        return self._fields({
            'template_id': template_assignment.template_id,
            'tenant_id': template_assignment.tenant_id,
            'stack_id': template_assignment.stack_id,
            'template': self._make_network_template_dict(\
                            template_assignment.template)
            }, fields)

    def _make_reachability_test_dict(self, reachabilitytest, fields=None):
        return self._fields({
            'id': reachabilitytest.id,
            'tenant_id': reachabilitytest.tenant_id,
            'test_id': reachabilitytest.test_id,
            'src_tenant_id': reachabilitytest.src_tenant_id,
            'src_segment_id': reachabilitytest.src_segment_id,
            'src_ip': reachabilitytest.src_ip,
            'dst_tenant_id': reachabilitytest.dst_tenant_id,
            'dst_segment_id': reachabilitytest.dst_segment_id,
            'dst_ip': reachabilitytest.dst_ip,
            'expected_result': reachabilitytest.expected_result
            }, fields)

    def _make_reachability_test_result_dict(self, reachabilitytestresult,
                                            test, fields=None):
        return self._fields({
            'id': reachabilitytestresult.id,
            'test_primary_key': reachabilitytestresult.test_primary_key,
            'tenant_id': reachabilitytestresult.tenant_id,
            'test_id': reachabilitytestresult.test_id,
            'test_time': reachabilitytestresult.test_time,
            'test_result': reachabilitytestresult.test_result,
            'detail': reachabilitytestresult.detail,
            'reachabilitytest': self._make_reachability_test_dict(test),
            }, fields)

    def _make_network_template_from_dict(self, template_dict):
        net_template = template_dict['networktemplate']
        return network_template_db.NetworkTemplate(
                    tenant_id=net_template['tenant_id'],
                    body=net_template['body'],
                    template_name=net_template['template_name'])

    def _make_network_template_assignment_from_dict(self, template_assignment_dict):
        net_template_assignment = \
            template_assignment_dict['networktemplateassignment']
        return network_template_db.NetworkTemplateAssignment(
                    template_id=net_template_assignment['template_id'],
                    tenant_id=net_template_assignment['tenant_id'],
                    stack_id=net_template_assignment['stack_id'])

    def _make_reachability_test_from_dict(self, reachabilitytest):
        test_dict = reachabilitytest['reachabilitytest']
        return reachability_test_db.ReachabilityTest(
            tenant_id=test_dict['tenant_id'],
            test_id=test_dict['test_id'],
            src_tenant_id=test_dict['src_tenant_id'],
            src_segment_id=test_dict['src_segment_id'],
            src_ip=test_dict['src_ip'],
            dst_tenant_id=test_dict['dst_tenant_id'],
            dst_segment_id=test_dict['dst_segment_id'],
            dst_ip=test_dict['dst_ip'],
            expected_result=test_dict['expected_result'])

    def _make_reachability_test_result_from_dict(self, reachabilitytestresult):
        test_result_dict = reachabilitytestresult['reachabilitytestresult']
        return reachability_test_db.ReachabilityTestResult(
            test_primary_key=test_result_dict['test_primary_key'],
            tenant_id=test_result_dict['tenant_id'],
            test_id=test_result_dict['test_id'],
            test_time=test_result_dict['test_time'],
            test_result=test_result_dict['test_result'],
            detail=test_result_dict['detail'],
            )

    def _get_network_template_by_id(self, context, template_id):
        return context.session.query(network_template_db.NetworkTemplate)\
                              .filter_by(id=template_id)\
                              .first()

    def _get_network_template_assignment_by_id(self, context, tenant_id):
        return context.session.query(\
                    network_template_db.NetworkTemplateAssignment)\
                    .filter_by(tenant_id=tenant_id)\
                    .first()

    def _get_reachability_test_by_id(self, context, reachabilitytest_id):
        return context.session.query(reachability_test_db.ReachabilityTest)\
                              .filter_by(id=reachabilitytest_id)\
                              .first()

    def _get_reachability_test_result_by_id(self, context, test_result_id):
        return context.session.query(\
                    reachability_test_db.ReachabilityTestResult)\
                    .filter_by(id=test_result_id)\
                    .first()


    # public methods based on extension names
    # CRUD methods for each extension

    # network-templates
    def get_networktemplates(self, context, filters=None, fields=None,
                             sorts=None, limit=None, marker=None,
                             page_reverse=False):
        all_templates = context.session.query(network_template_db.NetworkTemplate).all()
        result_list = []
        for template in all_templates:
            result_list.append(self._make_network_template_dict(template, fields))
        return result_list

    def get_networktemplate(self, context, template_id, fields=None):
        return_template = self._get_network_template_by_id(context, template_id)
        return self._make_network_template_dict(return_template, fields)

    def create_networktemplate(self, context, networktemplate):
        with context.session.begin(subtransactions=True):
            template_db_obj = self._make_network_template_from_dict(networktemplate)
            context.session.add(template_db_obj)
            return networktemplate['networktemplate']

    def delete_networktemplate(self, context, template_id):
        with context.session.begin(subtransactions=True):
            context.session.delete(self._get_network_template_by_id(context, template_id))

    def update_networktemplate(self, context, template_id, networktemplate):
        with context.session.begin(subtransactions=True):
            json_template = networktemplate['networktemplate']
            self._get_network_template_by_id(context, template_id)\
                .update({'template_name': json_template['template_name'],
                         'body': json_template['body']})
            return self.get_networktemplate(context, template_id)

    # network-template-assignments
    def get_networktemplateassignments(self, context, filters=None,
                                       fields=None, sorts=None, limit=None,
                                       marker=None, page_reverse=False):
        all_assignments = context.session.query(\
            network_template_db.NetworkTemplateAssignment).all()
        result_list = []
        for temp_assignment in all_assignments:
            template_db_obj = \
                self._get_network_template_by_id(context,
                                                 temp_assignment.template_id)
            net_template_dict = \
                self._make_network_template_assignment_dict(temp_assignment,
                                                            template_db_obj,
                                                            fields)
            result_list.append(net_template_dict)
        return result_list

    def get_networktemplateassignment(self, context, tenant_id, fields=None):
        template_assignment_db_obj = \
            self._get_network_template_assignment_by_id(context, tenant_id)
        template_db_obj = self._get_network_template_by_id(context,
            template_assignment_db_obj.template_id)
        return self._make_network_template_assignment_dict(
            template_assignment_db_obj, template_db_obj)


    def create_networktemplateassignment(self, context,
                                         networktemplateassignment):
        with context.session.begin(subtransactions=True):
            template_assignment_db_obj = \
                self._make_network_template_assignment_from_dict(\
                    networktemplateassignment)
            context.session.add(template_assignment_db_obj)
            return networktemplateassignment['networktemplateassignment']

    def delete_networktemplateassignment(self, context, tenant_id):
        with context.session.begin(subtransactions=True):
            context.session\
                .delete(self._get_network_template_assignment_by_id(context,
                                                                    tenant_id))

    def update_networktemplateassignment(self, context, tenant_id,
                                         networktemplateassignment):
        with context.session.begin(subtransactions=True):
            net_temp_assign_dict = \
                networktemplateassignment['networktemplateassignment']
            self._get_network_template_assignment_by_id(context, tenant_id)\
                .update({'template_id': net_temp_assign_dict['template_id'],
                         'stack_id': net_temp_assign_dict['stack_id']})
            return self.get_networktemplateassignment(context, tenant_id)

    # reachability test
    def get_reachabilitytests(self, context, filters=None, fields=None,
                              sorts=None, limit=None, marker=None,
                              page_reverse=False):
        all_tests = context.session.query(\
            reachability_test_db.ReachabilityTest).all()
        result_list = []
        for test_db_obj in all_tests:
            result_list.append(self._make_reachability_test_dict(test_db_obj))
        return result_list

    def get_reachabilitytest(self, context, reachabilitytest_id, fields=None):
        test_db_obj = self._get_reachability_test_by_id(context,
                                                        reachabilitytest_id)
        return self._make_reachability_test_dict(test_db_obj)

    def create_reachabilitytest(self, context, reachabilitytest):
        with context.session.begin(subtransactions=True):
            test_db_obj = self._make_reachability_test_from_dict(\
                reachabilitytest)
            context.session.add(test_db_obj)
            return reachabilitytest['reachabilitytest']

    def update_reachabilitytest(self, context, reachabilitytest_id,
                                reachabilitytest):
        with context.session.begin(subtransactions=True):
            test_dict = reachabilitytest['reachabilitytest']
            self._get_reachability_test_by_id(context, reachabilitytest_id)\
                .update({'test_id': test_dict['test_id'],
                         'src_tenant_id': test_dict['src_tenant_id'],
                         'src_segment_id': test_dict['src_segment_id'],
                         'src_ip': test_dict['src_ip'],
                         'dst_tenant_id': test_dict['dst_tenant_id'],
                         'dst_segment_id': test_dict['dst_segment_id'],
                         'dst_ip': test_dict['dst_ip'],
                         'expected_result': test_dict['expected_result']})
            return self.get_reachabilitytest(context, reachabilitytest_id)

    def delete_reachabilitytest(self, context, reachabilitytest_id):
        with context.session.begin(subtransactions=True):
            context.session\
                .delete(self._get_reachability_test_by_id(context,
                                                          reachabilitytest_id))

    # reachability test results
    def get_reachabilitytestresults(self, context, filters=None,
                                    fields=None, sorts=None, limit=None,
                                    marker=None, page_reverse=False):
        all_test_results = context.session.query(\
            reachability_test_db.ReachabilityTestResult).all()
        result_list = []
        for test_result in all_test_results:
            test_db_obj = \
                self._get_reachability_test_by_id(context,
                                                  test_result.test_primary_key)
            test_result_dict = self._make_reachability_test_result_dict(\
                test_result, test_db_obj, fields)
            result_list.append(test_result_dict)
        return result_list

    def get_reachabilitytestresult(self, context, test_result_id, fields=None):
        test_result_db_obj = \
            self._get_reachability_test_result_by_id(context, test_result_id)
        test_db_obj = self._get_reachability_test_by_id(context,\
            test_result_db_obj.test_primary_key)
        return self._make_reachability_test_result_dict(test_result_db_obj,\
                                                        test_db_obj)

    def create_reachabilitytestresult(self, context, reachabilitytestresult):
        with context.session.begin(subtransactions=True):
            test_result_db_obj = \
                self._make_reachability_test_result_from_dict(\
                    reachabilitytestresult)
            context.session.add(test_result_db_obj)
            return reachabilitytestresult['reachabilitytestresult']

    def delete_reachabilitytestresults(self, context, reachabilitytestresult_id):
        with context.session.begin(subtransactions=True):
            context.session\
                   .delete(self._get_reachability_test_result_by_id(\
                           context, reachabilitytestresult_id))

    def update_reachabilitytestresult(self, context, result_id,
                                      reachabilitytestresult):
        with context.session.begin(subtransactions=True):
            test_result_dict = reachabilitytestresult['reachabilitytestresult']
            self._get_reachability_test_result_by_id(context, result_id)\
                .update({'test_id': test_result_dict['test_id'],
                         'test_time': test_result_dict['test_time'],
                         'test_result': test_result_dict['test_result'],
                         'detail': test_result_dict['detail']})
            return self.get_reachabilitytestresult(context, result_id)

