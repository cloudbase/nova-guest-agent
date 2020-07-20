# Copyright 2020 Cloudbase Solutions Srl
# All Rights Reserved.

from nova_guest import utils
from nova_guest.agent.rpc import client as rpc_client


class API(object):
    def __init__(self):
        self._rpc_client = rpc_client.AgentClient()

    @utils.bad_request_on_error("Invalid destination environment: %s")
    def apply_networking(self, ctxt, server_id):
        output = self._rpc_client.apply_network_config(ctxt, server_id)
        return (True, output)
