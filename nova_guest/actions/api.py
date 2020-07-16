# Copyright 2020 Cloudbase Solutions Srl
# All Rights Reserved.

from nova_guest.agent.rpc import client as rpc_client


class API(object):
    def __init__(self):
        self._rpc_client = rpc_client.AgentClient()

    def apply_network_config(self, ctxt, server_id):
        return self._rpc_client.apply_network_config(
            ctxt, server_id)
