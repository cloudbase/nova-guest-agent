import json
import base64
import time
import datetime

from nova_guest import exception

import libvirt
import libvirt_qemu
from oslo_log import log as logging

LOG = logging.getLogger(__name__)

EXEC_TIMEOUT = 60  # seconds 
OS_TYPE_LINUX = "linux"
OS_TYPE_WINDOWS = "windows"
OS_TYPE_UNKNOWN = "unknown"
OS_TYPE_MAP = {
    # TODO: add more
    "mswindows": OS_TYPE_WINDOWS,
    "ubuntu": OS_TYPE_LINUX,
    # Generic linux ID returned by LinuxOSProber
    OS_TYPE_LINUX: OS_TYPE_LINUX,
}

class CommandRunnerMixin(object):

    def _supports_guest_exec(self, dom):
        supported_commands = self._get_supported_commands(dom)
        required = (
            "guest-exec",
            "guest-exec-status",
            "guest-file-open",
            "guest-file-read",
            "guest-file-close")
        for i in required:
            if supported_commands.get(i, False) is False:
                return False
        return True

    def ping(self, dom):
        try:
            libvirt_qemu.qemuAgentCommand(
                dom, '{"execute": "guest-ping"}', 10, 0)
            return True
        except libvirt.libvirtError:
            return False
        return False

    def _get_result_body(self, result):
        res = self._parse_command_output(result)
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

    def _parse_command_output(self, result):
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
        ret = self._parse_command_output(result)
        pid = ret.get("pid")
        if pid is None:
            raise exception.NovaGuestException(
                "could not find pid in response")
        return pid

    def run_command(self, dom, command, parameters, wait=True):
        if self.ping(dom) is False:
            raise exception.GuestAgentNotAvailable()
    
        if self._supports_guest_exec(dom) is False:
            raise exception.NotSupportedOperation(
                "missing required guest-exec functionality")

        command = {
            "execute": "guest-exec",
            "arguments": {
                "path": command,
                "arg": parameters,
                "capture-output": True,
            }
        }
        try:
            ret = libvirt_qemu.qemuAgentCommand(
                dom, json.dumps(command), EXEC_TIMEOUT, 0)
        except Exception as err:
            raise exception.GuestExecutionError(
                "failed to run command: %s" % err) from err

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
                        raise exception.GuestExecutionError(
                            "Command returned errorcode: "
                            "%r" % command_result["exitcode"])
                    if command_result["signal"] != 0:
                        raise exception.GuestExecutionError(
                            "Command interrupted by signal: "
                            "%r" % command_result["signal"])
                    break
        return command_result
    
    def _open_file(self, dom, filePath):
        command = {
            "execute": "guest-file-open",
            "arguments": {
                "path": filePath,
                "mode": "r",
            }
        }
        try:
            ret = libvirt_qemu.qemuAgentCommand(
                dom, json.dumps(command), EXEC_TIMEOUT, 0)
        except Exception as err:
            raise exception.GuestExecutionError(
                "failed to open file: %s" % err) from err
        ret = self._parse_command_output(ret)
        return int(ret)
    
    def _close_file(self, dom, handle):
        command = {
            "execute": "guest-file-close",
            "arguments": {
                "handle": handle,
            }
        }
        try:
            libvirt_qemu.qemuAgentCommand(
                dom, json.dumps(command), EXEC_TIMEOUT, 0)
        except Exception as err:
            raise exception.GuestExecutionError(
                "failed to open file: %s" % err) from err

    def _read_from_file_handle(self, dom, handle):
        command = {
            "execute": "guest-file-read",
            "arguments": {
                "handle": handle,
            }
        }
        try:
            ret = libvirt_qemu.qemuAgentCommand(
                dom, json.dumps(command), EXEC_TIMEOUT, 0)
        except Exception as err:
            raise exception.GuestExecutionError(
                "failed to open file: %s" % err) from err
        data = self._parse_command_output(ret)
        if data is not dict:
            LOG.debug("failed to read file")
            return ""
        output = data.get("buf-b64", None)
        if output is None:
            return ""
        if type(output) is not str:
            output = output.decode()
        return base64.b64decode(output.encode()).decode()

    def _read_file(self, dom, filePath):
        fd = self._open_file(dom, filePath)
        try:
            return self._read_from_file_handle(dom, fd)
        finally:
            self._close_file(dom, fd)


class LinuxOSProber(CommandRunnerMixin):

    def __init__(self, con):
        self._con = con

    def _get_val_from_release_file(self, dom, releaseFile, key):
        try:
            data = self._read_file(dom, releaseFile)
        except Exception as err:
            LOG.debug("failed to read %s: %s" % (releaseFile, err))
            return None

        lines = data.splitlines()
        for line in lines:
            fields = line.split("=")
            if len(fields) != 2:
                continue
            if fields[0] == key:
                return fields[1].strip('"').strip("'").lower()
        return None

    def _get_os_id_from_os_release(self, dom):
        return self._get_val_from_release_file(dom, "/etc/os-release", "ID")

    def _get_os_id_from_lsb_release(self, dom):
        data = self._get_val_from_release_file(
            dom, "/etc/lsb-release", "DISTRIB_ID")
        if data is None:
            return None
        return data.lower()

    def _get_id_from_rhel_release_file(self, dom, releaseFile):
        try:
            data = self._read_file(dom, releaseFile)
        except Exception as err:
            LOG.debug("failed to read %s: %s" % (releaseFile, err))
            return None
        release_elements = data.split()
        if len(release_elements) == 0:
            return None
        return release_elements[0].lower()

    def _get_os_id_from_rh_release(self, dom):
        return self._get_id_from_rhel_release_file(
            dom, "/etc/redhat-release")

    def _get_os_release_from_centos_release(self, dom):
        return self._get_id_from_rhel_release_file(
            dom, "/etc/centos-release")

    def _is_linux(self, dom):
        try:
            ret = self.run_command(dom, "/bin/sh", ["-c", "uname -a"])
        except Exception as err:
            LOG.debug("failed to run uname -a: %s" % err)
            return False
        data = ret.get("out-data", None)
        if data is None:
            return False
        if type(data) is not str:
            data = data.decode()
        if "linux" in data.lower():
            return True
        return False

    def probe(self, dom):
        probes = [
            "_get_os_id_from_os_release",
            "_get_os_id_from_lsb_release",
            "_get_os_release_from_centos_release",
            "_get_os_id_from_rh_release",
        ]
        for probe in probes:
            try:
                func = getattr(self, probe, None)
                if func is None:
                    continue
                result = func(dom)
                if result is None:
                    continue
                return result
            except Exception as err:
                LOG.debug(
                    "failed to fetch os ID using %s (%s)" % (probe, err))
                continue
        if self._is_linux(dom):
            return OS_TYPE_LINUX
        return None


class WindowsOSProber(CommandRunnerMixin):
    
    def __init__(self, con):
        self._con = con
    
    def probe(self, dom):
        hosts_file = "C:\\Windows\\System32\\Drivers\\etc\\hosts"
        try:
            self._read_file(
                dom, hosts_file)
        except Exception as err:
            LOG.debug("failed to read %s: %s" % (hosts_file, err))
            return None
        return "mswindows"


class AgentConnection(CommandRunnerMixin):

    def __init__(self, location=None):
        self._con = libvirt.open(location)

    def _get_supported_commands(self, dom):
        try:
            ret = libvirt_qemu.qemuAgentCommand(
                dom, '{"execute": "guest-info"}', 10, 0)
        except Exception as err:
            raise exception.NotSupportedOperation(
                "failed to fetch guest info") from err
        parsed = self._parse_command_output(ret)
        cmds = {}
        for cmd in parsed["supported_commands"]:
            cmds[cmd["name"]] = cmd["enabled"]
        return cmds
    
    def _validate_commands(self, cmds):
        required = (
            "guest-exec",
            "guest-exec-status",
            "guest-file-open",
            "guest-file-read",
            "guest-file-close")
        missing = []
        for i in required:
            if cmds.get(i, False) is False:
                 missing.append(i)
        if len(missing) > 0:
            raise exception.NotSupportedOperation(
                "Missing required guest agent capabilities:"
                " %s" % ", ".join(missing))

    def get_instance_by_name(self, instanceName):
        allDomains = self._con.listAllDomains()
        for dom in allDomains:
            if dom.name() == instanceName:
                return dom
        raise exception.NotFound(
            "could not find instance with name %s" % instanceName)

    def _get_os_info_from_agent(self, dom):
        command = {
            "execute": "guest-get-osinfo"
        }
        ret = libvirt_qemu.qemuAgentCommand(
            dom, json.dumps(command), 10, 0)
        return self._parse_command_output(ret)
    
    def _get_os_info_from_vm(self, dom):
        linuxProber = LinuxOSProber(self._con).probe(dom)
        if linuxProber is not None:
            return {"id": linuxProber}
        windowsProber = WindowsOSProber(self._con)
        if windowsProber is not None:
            return {"id": windowsProber}
        return {"id": OS_TYPE_LINUX}

    def get_os_info(self, dom):
        cmds = self._get_supported_commands(dom)
        if cmds.get("guest-get-osinfo", False) is False:
            return self._get_os_info_from_vm(dom)
        return self._get_os_info_from_agent(dom)

    def get_guest_platform(self, dom):
        try:
            os_info = self.get_os_info(dom)
        except Exception as err:
            raise exception.NovaGuestException(
                "Failed to determine instance OS type") from err

        # TODO: properly detect plarform
        os_id = os_info.get("id")
        return OS_TYPE_MAP.get(os_id, OS_TYPE_LINUX)
    
    def is_alive(self, dom):
        state, _ = dom.state()
        if state != libvirt.VIR_DOMAIN_RUNNING:
            return False
        return True

    def execute_command(self, dom, command, parameters, wait=True):
        return self.run_command(dom, command, parameters, wait)
