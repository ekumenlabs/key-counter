# import gevent
# import gevent_inotifyx as inotify
from core import PushStrategy

import logging
logger = logging.getLogger('config')


class ConfigFileManager (object):
    "Maybe this is just a couple of functions."

    def __init__(self, filename):
        self.config_manager = ConfigManager()
        # * check file existance and read-permission.
        # * register watcher function
        # * trigger... relaunch... ?


class ConfigManager (object):
    """A config object is a list of dict , each of which has all strings for
    keys and values and adheres to the following shape:

    [{
        "name": (string),
        "type": (string),
        "options": {
            ...
        }
    }]

    Each of the inner dicts corresponds to the configuration of a single
    upstream. The "options" dict in each dict is free form, should be defined
    per each type of upstream, and should contain the minimum possible to
    configure that type.
    """

    def __init__(self, pusher, config=None):
        # Successful configuration is kept, keyed by inner upstream "name".
        self._config = {}

        # Reconfiguration will affect the single pusher object.
        self.pusher = pusher

        if config:
            self.reconfigure(config)

    def _normalize_upstream(self, upstream_config):
        upstream = {
            "name": upstream_config.get('name', None),
            "type": upstream_config.get('type', None),
            "options": upstream_config.get('options', {})
        }
        if not upstream["name"]:
            raise ValueError('upstream config without a "name" entry.')
        if not upstream["type"]:
            raise ValueError('upstream config without a "type" entry.')
        if upstream["type"] not in PushStrategy.PUSH_TYPES:
            types = ', '.join(PushStrategy.PUSH_TYPES)
            raise ValueError('invalid "type" entry in upstream config. Should '
                             'be one of %s.' % types)
        logger.debug("Normalized: %s" % upstream)
        return upstream

    def reconfigure(self, config):
        new_names = []
        for raw_upstream in config:
            upstream = self._normalize_upstream(raw_upstream)
            name = upstream["name"]
            # Either update the upstream, or create a new one.
            if name in self._config:
                self._update_upstream(upstream)
            else:
                self._add_upstream(upstream)
            # Collect names of upstreams that ought to survive.
            new_names.append(name)
        # Clean up old upstreams.
        self._cleanup_config(new_names)

    def _cleanup_config(self, names_to_keep):
        "Remove all upstreams which are not in the passed list of names."
        logger.debug("Clean up the config.")
        new_config = {}
        for name in self._config:
            if name in names_to_keep:
                new_config[name] = self._config[name]
            else:
                logger.debug('Removing unused upstream "%s"' % name)
                self.pusher.remove_upstream(name)
        self._config = new_config

    def _add_upstream(self, upstream_config):
        name = upstream_config["name"]
        _type = upstream_config["type"]
        options = upstream_config["options"]
        self.pusher.add_upstream(name, _type, **options)
        self._config[name] = upstream_config
        logger.debug('Added config for upstream "%s"' % name)

    def _update_upstream(self, upstream_config):
        name = upstream_config["name"]
        old_type = self._config[name]["type"]
        old_options = self._config[name]["options"]
        new_type = upstream_config["type"]
        new_options = upstream_config["options"]

        if old_type != new_type or old_options != new_options:
            logger.debug('Updated config for upstream "%s"' % name)
            del self._config[name]
            self.pusher.remove_upstream(name)
            self.pusher.add_upstream(name, new_type, **new_options)
            self._config[name] = upstream_config
