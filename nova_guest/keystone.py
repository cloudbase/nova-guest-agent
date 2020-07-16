# Copyright 2016 Cloudbase Solutions Srl
# All Rights Reserved.

from keystoneauth1 import exceptions as ks_exceptions
from keystoneauth1 import loading
from keystoneauth1 import session as ks_session
from keystoneclient.v3 import client as kc_v3
from oslo_config import cfg
from oslo_log import log as logging

from nova_guest import exception

opts = [
    cfg.StrOpt("auth_url",
               default=None,
               help="Default auth URL to be used when not specified in the"
               " migration's connection info."),
    cfg.IntOpt("identity_api_version",
               min=2, max=3,
               default=2,
               help="Default Keystone API version."),
    cfg.BoolOpt("allow_untrusted",
                default=False,
                help="Allow untrusted SSL/TLS certificates."),
]

CONF = cfg.CONF
CONF.register_opts(opts, "keystone")

LOG = logging.getLogger(__name__)


def create_keystone_session(ctxt):
    allow_untrusted = CONF.keystone.allow_untrusted
    # TODO(gsamfira): add "ca_cert" to connection_info
    verify = not allow_untrusted

    plugin_name = "token"
    plugin_args = {
        "token": ctxt.auth_token
    }

    project_name = ctxt.project_name
    auth_url = CONF.keystone.auth_url
    if not auth_url:
        raise exception.NovaGuestException(
            '"auth_url" in group "[keystone]" not set')

    plugin_args.update({
        "auth_url": auth_url,
        "project_name": project_name,
    })

    keystone_version = CONF.keystone.identity_api_version

    if keystone_version == 3:
        plugin_name = "v3" + plugin_name

        project_domain_name = ctxt.project_domain_name
        # NOTE: only set the kwarg if proper argument is provided:
        if project_domain_name:
            plugin_args["project_domain_name"] = project_domain_name

        project_domain_id = ctxt.project_domain_id
        if project_domain_id:
            plugin_args["project_domain_id"] = project_domain_id

        if not project_domain_name and not project_domain_id:
            raise exception.NovaGuestException(
                "Either 'project_domain_name' or 'project_domain_id' is "
                "required for Keystone v3 Auth.")

        # NOTE: The v3token plugin does not allow the user_domain_name
        #       or user_domain_id options, while the v3password plugin
        #       requires at least any of these.
        if plugin_name != "v3token":
            user_domain_name = ctxt.user_domain_name
            if user_domain_name:
                plugin_args["user_domain_name"] = user_domain_name

            user_domain_id = ctxt.user_domain_id
            if user_domain_id:
                plugin_args["user_domain_id"] = user_domain_id

            if not user_domain_name and not user_domain_id:
                raise exception.NovaGuestException(
                    "Either 'user_domain_name' or 'user_domain_id' is "
                    "required for Keystone v3 Auth.")

    loader = loading.get_plugin_loader(plugin_name)
    auth = loader.load_from_options(**plugin_args)

    return ks_session.Session(auth=auth, verify=verify)
