import socket
import platform
import yaml
import os
from logging import getLogger
logging = getLogger(__name__)


def GetConfig():
    """Returns a ``dict`` containing the configuration specified in
    ``Converter/config.yaml``, updated to include overrides for the
    current OS, then for the current system, and finally the
    current OS on the current system (top priority).  Linux assumes
    the external executables are system-wide while Windows assumes
    they are in the ``Converter\tools\standalone`` directory.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_dir, "..", "..", "config", "config.yaml")) as f:
        config = yaml.safe_load(f.read())
    system = platform.system()
    updates = [system, socket.gethostname()]
    for update in updates:
        if update not in config:
            continue
        update_dict = {k: v for k, v in config[update].items() if not isinstance(v, dict)}
        config.update(update_dict)
        if system in config[update]:
            config.update(config[update][system])
    config = {k: v for k, v in config.items() if type(v) is not dict}
    logging.debug("Configuration...")
    for k, v in config.items():
        logging.debug("%s -> %s", k, v)
    return config
