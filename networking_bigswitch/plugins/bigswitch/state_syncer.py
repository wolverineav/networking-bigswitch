# Copyright 2019 Big Switch Networks, Inc.
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
import copy
from keystoneauth1.identity import v3
from keystoneauth1 import loading
from keystoneauth1 import session
from keystoneclient.v3 import client as ksclient
from novaclient import client as nv_client
from servermanager import ServerPool


NOVA_CLIENT_VERSION = "2"


class StateSyncer(object):
    """StateSync

    Periodic state syncer for BCF.
    This is not the same as topo_sync.

    StateSyncer provides network information, along with metadata about a bunch
    of other objects - such as compute nodes available, interface groups,
    VMs running on each compute node, last X errors for the calls to BCF,
    last topo_sync status.
    """

    def __init__(self, auth_url, username, password, project_name,
                 user_domain_name, project_domain_name):
        # typically:
        # username = neutron
        # project_name = service
        # user_domain_name = Default
        # project_domain_name = Default
        self.auth_url = auth_url
        self.username = username
        self.password = password
        self.project_name = project_name
        self.user_domain_name = user_domain_name
        self.project_domain_name = project_domain_name

        # initialize keystone client
        auth = v3.Password(auth_url=self.auth_url,
                           username=self.username,
                           password=self.password,
                           project_name=self.project_name,
                           user_domain_name=self.user_domain_name,
                           project_domain_name=self.project_domain_name)
        sess = session.Session(auth=auth)
        self.keystone_client = ksclient.Client(session=sess)

        # initialize nova client
        loader = loading.get_plugin_loader('password')
        auth = loader.load_from_options(auth_url=self.auth_url,
                                        username=self.username,
                                        password=self.password,
                                        project_name=self.project_name,
                                        user_domain_name=self.user_domain_name,
                                        project_domain_name=self.project_domain_name)
        sess = session.Session(auth=auth)
        self.nova_client = nv_client.Client(NOVA_CLIENT_VERSION, session=sess)


    def push_update(self):
        """Push current state of OSP to BCF

        Collects the info about various objects from keystone, nova, neutron
        and posts an update to BCF. A typical update has the following
        structure:
        {
            'tenant' : [
                {
                    'id': '',
                    'name': '',
                },
                {},
                ...
            ],

            'network' : [
                {
                    'id': '',
                    'name': '',
                },
                {},
                ...
            ],

            'hypervisor' : [
                {
                    'hardware-model': '',
                    'state': '',
                    'vcpus': 24,
                    'vcpus_used': 2,
                    'local_gb': hdd_size,
                    'local_gb_used': hdd_used,
                    'hostname': '',
                    'memory_mb': mem_size,
                    'memory_mb_used': mem_used,
                }, {}, ...
            ],

            'vm': [
                {
                    'name': '',
                    'hypervisor_hostname': '',
                    'state': '',
                    'tenant_id': '',
                    'tenant_name': '',
                    'interface': [
                        {
                            'network_name': '',
                            'mac_address': '',
                            'ip_address': '',
                            'type': 'fixed/floating',
                            'version': '4/6'
                        }, {}, ...
                    ],
                    'network': [
                        {
                            'network_name': '',
                            'interface': [
                                {
                                    'mac_addr': '',
                                    'ip_addr': '',
                                    'type': '',
                                },
                                {}
                            ]
                        },
                        {}
                    ],
                },
                {}, ...
            ]
        }

        :return: None - it does a REST call to BCF. does not return a value
        """
        # get serverpool instance
        serverpool = ServerPool.get_instance()
        # initialize empty dictionary post data
        post_data = {}

        # add tenant list
        post_data['tenant'] = copy.deepcopy(serverpool.keystone_tenants)

        # get hypervisors info from nova
        hypervisors = self.nova_client.hypervisors.list()
        hv_list = []
        for hv in hypervisors:
            hv_list.append({
                'hostname': hv.hypervisor_hostname,
                'vcpus': hv.vcpus,
                'vcpus_used': hv.vcpus_used,
                'disk_capacity': hv.local_gb,
                'disk_capacity_used': hv.local_gb_used,
                'memory_mb': hv.memory_mb,
                'memory_mb_used': hv.memory_mb_used,
                'power_state': hv.state,
                'status': hv.status,
                'current_workload': hv.current_workload
            })
        post_data['hypervisor'] = hypervisors

        # get VM info from nova
        vms = self.nova_client.servers.list()
        vm_list = []
        for vm in vms:
            # network info needs more parsing
            interfaces = []
            for addr in vm.addresses:
                for intf in vm.addresses[addr]:
                    interfaces.append({
                        'network_name': addr,
                        'mac_address': intf['OS-EXT-IPS-MAC:mac_addr'],
                        'ip_address': intf['addr'],
                        'type': intf['OS-EXT-IPS:type'],
                        'version': intf['version']
                    })

            vm_list.append({
                'name': vm.name,
                # hypervisor hostname is not straighforward object property
                'hypervisor_hostname': getattr(vm, 'OS-EXT-SRV-ATTR:hypervisor_hostname'),
                'state': getattr(vm, 'OS-EXT-STS:vm_state'),
                'tenant_id': vm.tenant_id,
                'tenant_name': serverpool.keystone_tenants[vm.tenant_id],
                'interface': interfaces
            })

        post_data['vm'] = vms

        # TODO(wolverineav) post to BCF
        serverpool.rest_call("path to new API for orchestrator")
