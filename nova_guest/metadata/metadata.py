import netaddr

from novaclient import client as nova_client
from neutronclient.v2_0 import client as neutorn_client

from nova_guest import keystone
from nova_guest import exception
from nova_guest import cache

MEMOIZE = cache.get_cache_decorator('api')


class MetadataWrapper(object):

    def __init__(self, ctxt):
        self._session = keystone.create_keystone_session(ctxt)
        self._nova_client = nova_client.Client("2", session=self._session)
        self._neutron_client = neutorn_client.Client(session=self._session)

    @MEMOIZE
    def _get_network_details(self, network_id):
        # Cachable function
        return self._neutron_client.list_networks(id=network_id)

    @MEMOIZE
    def _get_subnet_details(self, subnet_id):
        # Cachable function
        return self._neutron_client.list_subnets(id=subnet_id)

    def _format_links(self, ports):
        links = []
        for port in ports:
            net_details = self._get_network_details(port["network_id"])
            links.append(
                {
                    "id": "tap%s" % port["id"][:11],
                    "vif_id": port["id"],
                    "type": port["binding:vif_type"],
                    "mtu": net_details["mtu"],
                    "ethernet_mac_address": port["mac_address"],
                }
            )
        return links

    def _format_net_type(self, subnet):
        subnet_type = "ipv%d" % subnet["ip_version"]
        if subnet["enable_dhcp"]:
            if subnet["ip_version"] == 4:
                subnet_type += "_dhcp"
            else:
                subnet_type += subnet["ipv6_address_mode"]
        return subnet_type

    def _get_netmask(self, subnet):
        net = netaddr.IPNetwork(subnet)
        return [str(net.network), str(net.netmask)]

    def _get_default_route(self, subnet):
        if subnet["ip_version"] == 4:
            network = "0.0.0.0"
            netmask = "0.0.0.0"
        else:
            network = "::"
            netmask = "::"
        return {
            "network": network,
            "netmask": netmask,
            "gateway": subnet["gateway_ip"],
        }

    def _get_host_routes(self, subnet):
        routes = []
        for route in subnet["host_routes"]:
            network, mask = self._get_netmask(
                route["destination"])
            gateway = route["nexthop"]
            routes.append({
                "network": network,
                "netmask": mask,
                "gateway": gateway,
            })
        return routes

    def _append_aditional_info(self, net, fixed_ip, subnet):
        if subnet["enable_dhcp"]:
            if subnet["ip_version"] == 4:
                return net
        
        net["netmask"] = self._get_netmask(subnet["cidr"])[1]
        net["ip_address"] = fixed_ip["ip_address"]
        net["routes"] = []
        if subnet["gateway_ip"]:
            net["routes"].append(
                self._get_default_route(subnet) 
            )
        net["routes"].extend(
            self._get_host_routes(subnet))
        net["services"] = []
        for dns in subnet["dns_nameservers"]:
            net["services"].append(
                {
                    "type": "dns",
                    "address": dns,
                }
            )
        return net

    def _format_networks(self, ports):
        networks = []
        idx = 0
        for port in ports:
            for fixed_ip in port["fixed_ips"]:
                subnet = self._get_subnet_details(
                    fixed_ip["subnet_id"])
                net = {
                    "id": "network" + str(idx),
                    "link": "tap%s" % port["id"][:11],
                    "network_id": port["network_id"],
                    "type": self._format_net_type(subnet),
                }
                self._append_aditional_info(
                    net, fixed_ip, subnet)
            networks.append(net)
            idx += 1
        return networks

    def _extract_services(self, nets):
        svcs = []
        for net in nets:
            for svc in net["services"]:
                if svc not in svcs:
                    svcs.append(svc)
        return svcs
    
    def get_instance(self, instance_id):
        instance = self._nova_client.servers.get(instance_id)
        return instance

    def get_metadata(self, instance_id):
        ports = self._neutron_client.list_ports(device_id=instance_id)
        nets = self._format_networks(ports["ports"])
        ret = {
            "links": self._format_links(ports["ports"]),
            "networks": nets,
            "services": self._extract_services(nets)
        }
        return ret

