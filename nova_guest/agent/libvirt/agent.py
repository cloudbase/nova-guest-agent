import json
import base64
import time
import datetime

from nova_guest import exception

import libvirt
import libvirt_qemu

EXEC_TIMEOUT = 60  # seconds 
OS_TYPE_LINUX = "linux"
OS_TYPE_WINDOWS = "windows"
OS_TYPE_UNKNOWN = "unknown"
OS_TYPE_MAP = {
    # TODO: add more
    "mswindows": OS_TYPE_WINDOWS,
    "ubuntu": OS_TYPE_LINUX,
}


class AgentConnection(object):

    def __init__(self, location=None):
        self._con = libvirt.open(location)

    def get_instance_by_name(self, instanceName):
        allDomains = self._con.listAllDomains()
        for dom in allDomains:
            if dom.name() == instanceName:
                return dom
        raise exception.NovaGuestException(
            "could not find instance with name %s" % instanceName)

    def ping(self, dom):
        try:
            libvirt_qemu.qemuAgentCommand(
                dom, '{"execute": "guest-ping"}', 10, 0)
            return True
        except libvirt.libvirtError:
            return False
        return False

    def _get_result_body(self, result):
        res = self._parse_command_ourput(result)
        ret_value = {}
        required = ["exited"]
        int_values = [
            "exitcode", "signal",
            ]
        bool_values = [
            "out-truncated", "err-truncated"]
        base64_encoded = ["out-data", "err-data"]
        for key in required:
            if key not in res:
                raise exception.NovaGuestException(
                    "Missing required key %s" % key)
            ret_value[key] = res[key]

        for key in int_values:
            ret_value[key] = res.get(key, 0)

        for key in bool_values:
            ret_value[key] = res.get(key, False)

        for encoded in base64_encoded:
            if ret_value.get(encoded):
                ret_value[encoded] = base64.b64decode(ret_value[encoded])
            else:
                ret_value[encoded] = ""

        return ret_value

    def _parse_command_ourput(self, result):
        result = json.loads(result)
        ret = result.get("return")
        if ret is None:
            raise exception.NovaGuestException(
                "missing return in guest-exec result")
        return ret

    def _read_output(self, dom, pid):
        command = {
            "execute": "guest-exec-status",
            "arguments": {
                "pid": int(pid),
            }
        }
        ret = libvirt_qemu.qemuAgentCommand(
            dom, json.dumps(command), 10, 0)
        return self._get_result_body(ret)

    def _get_pid_from_guest_exec_result(self, result):
        ret = self._parse_command_ourput(result)
        pid = ret.get("pid")
        if pid is None:
            raise exception.NovaGuestException(
                "could not find pid in response")
        return pid

    def get_os_info(self, dom):
        command = {
            "execute": "guest-get-osinfo"
        }
        ret = libvirt_qemu.qemuAgentCommand(
            dom, json.dumps(command), 10, 0)
        return self._parse_command_ourput(ret)

    def get_guest_platform(self, dom):
        os_info = self.get_os_info(dom)
        # TODO: properly detect plarform
        os_id = os_info.get("id")
        return OS_TYPE_MAP.get(os_id, OS_TYPE_UNKNOWN)
    
    def is_alive(self, dom):
        state, _ = dom.state()
        if state != libvirt.VIR_DOMAIN_RUNNING:
            return False
        return True

    def execute_command(self, dom, command, parameters, wait=True):
        command = {
            "execute": "guest-exec",
            "arguments": {
                "path": command,
                "arg": parameters,
                "capture-output": True,
            }
        }
        ret = libvirt_qemu.qemuAgentCommand(
            dom, json.dumps(command), EXEC_TIMEOUT, 0)
        pid = self._get_pid_from_guest_exec_result(ret)
        command_result = self._read_output(dom, pid)
        start = datetime.datetime.now()
        if wait:
            while True:
                if command_result["exited"] is False:
                    now = datetime.datetime.now()
                    if now - start > datetime.timedelta(seconds=EXEC_TIMEOUT):
                        raise TimeoutError("timed out waiting for command")
                    time.sleep(1)
                    command_result = self._read_output(dom, pid)
                else:
                    if command_result["exitcode"] != 0:
                        raise exception.NovaGuestException(
                            "Command returned errorcode: "
                            "%r" % command_result["exitcode"])
                    if command_result["signal"] != 0:
                        raise exception.NovaGuestException(
                            "Command interrupted by signal: "
                            "%r" % command_result["signal"])
                    break
        return command_result
