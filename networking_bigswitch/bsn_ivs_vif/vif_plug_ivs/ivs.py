# Derived from nova/virt/libvirt/vif.py
# Copyright 2017 Big Switch Networks, Inc.
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

from os_vif import objects
from os_vif import plugin
from oslo_concurrency import processutils
from oslo_config import cfg
from oslo_log import log as logging

from networking_bigswitch.bsn_ivs_vif.vif_plug_ivs import exception
from networking_bigswitch.bsn_ivs_vif.vif_plug_ivs.i18n import _LE
from networking_bigswitch.bsn_ivs_vif.vif_plug_ivs import linux_net

LOG = logging.getLogger(__name__)

class IvsPlugin(plugin.PluginBase):
    """An OVS plugin that can setup VIFs in many ways
    The OVS plugin supports several different VIF types, VIFBridge
    and VIFOpenVSwitch, and will choose the appropriate plugging
    action depending on the type of VIF config it receives.
    If given a VIFBridge, then it will create connect the VM via
    a regular Linux bridge device to allow security group rules to
    be applied to VM traiffic.
    """

    NIC_NAME_LEN = 14

    CONFIG_OPTS = (
        cfg.IntOpt('network_device_mtu',
                   default=1500,
                   help='MTU setting for network interface.',
                   deprecated_group="DEFAULT"),
        cfg.IntOpt('ovs_vsctl_timeout',
                   default=120,
                   help='Amount of time, in seconds, that ovs_vsctl should '
                   'wait for a response from the database. 0 is to wait '
                   'forever.',
                   deprecated_group="DEFAULT"),
    )

    @staticmethod
    def gen_port_name(prefix, id):
        return ("%s%s" % (prefix, id))[:IvsPlugin.NIC_NAME_LEN]

    @staticmethod
    def get_veth_pair_names(vif):
        return (IvsPlugin.gen_port_name("qvb", vif.id),
                IvsPlugin.gen_port_name("qvo", vif.id))

    def describe(self):
        return objects.host_info.HostPluginInfo(
            plugin_name="ivs",
            vif_info=[
                objects.host_info.HostVIFInfo(
                    vif_object_name=objects.vif.VIFBridge.__name__,
                    min_version="1.0",
                    max_version="1.0"),
                objects.host_info.HostVIFInfo(
                    vif_object_name=objects.vif.VIFOpenVSwitch.__name__,
                    min_version="1.0",
                    max_version="1.0"),
                objects.host_info.HostVIFInfo(
                    vif_object_name=objects.vif.VIFVHostUser.__name__,
                    min_version="1.0",
                    max_version="1.0"),
                objects.host_info.HostVIFInfo(
                    vif_object_name=objects.vif.VIFHostDevice.__name__,
                    min_version="1.0",
                    max_version="1.0"),
            ])

    def _get_mtu(self, vif):
        if vif.network and vif.network.mtu:
            return vif.network.mtu
        return self.config.network_device_mtu

    def _create_vif_port(self, vif, vif_name, instance_info, **kwargs):
        mtu = self._get_mtu(vif)
        linux_net.create_ivs_vif_port(vif_name,
                                      vif.port_profile.interface_id,
                                      vif.address,
                                      instance_info.uuid,
                                      mtu)

    def _update_vif_port(self, vif, vif_name):
        mtu = self._get_mtu(vif)
        linux_net.update_ivs_vif_port(vif_name, mtu)

    def get_vif_devname(self, vif):
        if 'devname' in vif:
            return vif['devname']
        return ("nic" + vif.id)[:IvsPlugin.NIC_NAME_LEN]

    def _get_firewall_required(self, vif):
        if vif.has_traffic_filtering:
            return False
        if self.is_no_op_firewall():
            return False
        return True

    def _plug_ivs_ethernet(self, vif, instance):
        dev = self.get_vif_devname(vif)
        linux_net.create_tap_dev(dev)
        self._create_vif_port(vif, dev, instance)

    def _plug_ivs_hybrid(self, vif, instance):
        """Plug using hybrid strategy (same as OVS)

        Create a per-VIF linux bridge, then link that bridge to the OVS
        integration bridge via a veth device, setting up the other end
        of the veth device just like a normal OVS port. Then boot the
        VIF on the linux bridge using standard libvirt mechanisms.
        """

        v1_name, v2_name = self.get_veth_pair_names(vif)

        linux_net.ensure_bridge(vif.bridge_name)

        mtu = self._get_mtu(vif)
        if not linux_net.device_exists(v2_name):
            linux_net.create_veth_pair(v1_name, v2_name, mtu)
            linux_net.add_bridge_port(vif.bridge_name, v1_name)
            self._create_vif_port(vif, v2_name, instance)
        else:
            linux_net.update_veth_pair(v1_name, v2_name, mtu)
            self._update_vif_port(vif, v2_name)

    def plug(self, vif, instance):
        if not hasattr(vif, "port_profile"):
            raise exception.MissingPortProfile()
        if self._get_firewall_required(vif) or vif.port_profile.hybrid_plug:
            self._plug_ivs_hybrid(vif, instance)
        else:
            self._plug_ivs_ethernet(vif, instance)

    def _unplug_ivs_hybrid(self, vif, instance):
        v1_name, v2_name = self.get_veth_pair_names(vif)

        linux_net.delete_bridge(vif.bridge_name, v1_name)

        linux_net.delete_ivs_vif_port(vif.network.bridge, v2_name,
                                      timeout=self.config.ovs_vsctl_timeout)

    def _unplug_ivs_ethernet(self, vif, instance):
        try:
            linux_net.delete_ivs_vif_port(self.get_vif_devname(vif))
        except processutils.ProcessExecutionError:
            LOG.exception(_LE("Failed while unplugging vif"),
                          instance=instance)

    def unplug(self, vif, instance):
        if not hasattr(vif, "port_profile"):
            raise exception.MissingPortProfile()
        if self._get_firewall_required(vif) or vif.port_profile.hybrid_plug:
            self._unplug_ivs_hybrid(vif, instance)
        else:
            self._unplug_ivs_ethernet(vif, instance)
