from gevent.server import DatagramServer
import gevent
import json

import logging


###############################################################################

class NumbersManager:
    "Collect user counts and provides collected computed values."

    def __init__(self):
        self.compute = None
        # Buffer for previous data, used to compute new values.
        self.stashed_data = {}
        # Mapping from user name to previous key count.
        # NOTE: Using a dict as per aggregate_user_data() specification.
        self.aggregated = {}

    def aggregate_user_data(self, user, count):
        """Aggregate data as a (user, count) pair.

        Repeated entries (different counts for the same user) are possible, but
        only the latest is retained.
        """
        self.aggregated[user] = count

    def get_data_packet(self):
        """Return the data packet and a token to it.

        Each time this method is called, the data aggregated so far is used to
        compute the data packet returned, and then dropped.

        In the event of repeated entries in the aggregated data, last entry is
        used to produce a value.
        """
        # Only aggregated users will be in the packet.
        packet = {user: 0 for user in self.aggregated}
        for user, count in self.aggregated.items():
            if user in self.stashed_data:
                # With previously collected data compute value to send.
                packet[user] = self.compute(self.stashed_data[user], count)

        self.stashed_data = self.aggregated
        self.aggregated = {}

        return packet


###############################################################################

class NumbersPusher:
    "Push packed key count data to the destination sever at regular intervals."

    logger = logging.getLogger('push.pusher')

    def __init__(self, manager, interval=1):
        """Takes a data manager and a push interval (defaults to 1 second)."""
        self.manager = manager
        self.interval = interval
        self.running = False
        # Will delegate pushing data to the push-strategy objects.
        self._pushers = {}
        # Complete the numbers manager by providing it with a compute()
        self.manager.compute = self._build_computer()

    def _build_computer(self):
        def compute(old_count, new_count):
            # Approximate the "kpm" (keys per minute).
            value = int(round((new_count - old_count) * 60 / self.interval))
            if value < 0:
                return 0
            return value
        return compute

    def stop(self):
        self.logger.info("Stoping the pusher event loop.")
        self.running = False

    def start(self):
        "Loop to collect data and call _push()"
        gevent.spawn(self.collect_and_push)

    def collect_and_push(self):
        self.running = True
        while self.running:
            gevent.sleep(self.interval)
            data_packet = self.manager.get_data_packet()
            self._push(data_packet)

    def _push(self, data):
        # Delegate to the configured push strategies.
        self.logger.debug("Calling push() data.")
        for pusher in self._pushers.values():
            pusher.push(data)

    def add_upstream(self, name, strategy, *args, **kwargs):
        self.logger.debug('Adding pusher "%s", of type "%s"'
                          % (name, strategy))
        self._pushers[name] = PushStrategy(strategy, *args, **kwargs)

    def remove_upstream(self, name):
        self.logger.debug('Removing pusher "%s"' % name)
        del self._pushers[name]


class PushStrategy (object):
    """A push strategy takes a data dict, in the format by
    NumbersManager.get_data_packet(), and pushes it upstream.

    The details of what "upstream" is, and how to push that data to it, are
    isolated by each strategy.
    """

    PUSH_TEST = 'test'
    PUSH_TO_STDOUT = 'stdout'
    PUSH_TO_FILE = 'file'
    PUSH_TO_HTTP = 'http'
    PUSH_TYPES = [PUSH_TEST, PUSH_TO_STDOUT, PUSH_TO_FILE, PUSH_TO_HTTP]

    def __init__(self, strategy, *args, **kwargs):
        self.logger = logging.getLogger('push.strategy.%s' % strategy)
        if strategy == PushStrategy.PUSH_TEST:
            self.push = self._test_push(*args, **kwargs)
        elif strategy == PushStrategy.PUSH_TO_STDOUT:
            self.push = self._push_to_stdout(*args, **kwargs)
        elif strategy == PushStrategy.PUSH_TO_FILE:
            self.push = self._push_to_file(*args, **kwargs)
        elif strategy == PushStrategy.PUSH_TO_HTTP:
            self.push = self._push_to_HTTP(*args, **kwargs)
        else:
            raise ValueError('Strategy "%s" not known.' % strategy)

    def _test_push(self, **kwargs):
        def _push(data):
            self.logger.debug("Pushing data.")
            self.pushed.append(data)
            self.logger.debug("Current pushed data: %s" % self.pushed)
        self.logger.info("Test pushing: "
                         "data is accumulated in self.pushed list.")
        # Allow to test pushing to RAM.
        self.pushed = []
        # Keep arbitraty options.
        for kw in kwargs:
            setattr(self, kw, kwargs[kw])
        return _push

    def _push_to_stdout(self):
        def _push(data):
            print data

        self.logger.info("Pushing to stdout.")
        return _push

    def _push_to_file(self, file_name):
        "Write data as JSON encoded lines."
        def _push(data):
            with open(file_name, 'a') as pushed:
                line = "%s\n" % json.dumps(data)
                pushed.write(line)
        self.logger.info("Pushing to file %s." % file_name)
        return _push

    def _push_to_HTTP(self, base_URL):
        """Push POSTing to a HTTP API.

        The API must implement the following endpoints:

        "base_URL/:user" : will receive a JSON object {'count': (number)} which
        corresponds to the latest key count for that user.

        Each end point should accept a single integer as data payload, and
        return a status code of 202 Accepted.
        """
        import requests
        import requests.exceptions
        POST_TIMEOUT = 3  # seconds
        # No trailing slash on the base URL.
        base_url = base_URL
        if base_URL[-1] == '/':
            base_url = base_URL[0:-1]

        def _push(data):
            for user in data:
                url = "%s/%s" % (base_url, user)
                req = None
                try:
                    req = requests.post(url, data=data[user],
                                        timeout=POST_TIMEOUT)
                except requests.exceptions.ConnectionError:
                    self.logger.error("Connection error. Either %s is not the "
                                      "correct base URL, or upstream is not "
                                      "behaving as expected." % base_url)
                except requests.exceptions.Timeout:
                    self.logger.error("Push timeout. Upstream is taking too "
                                      "long to process the data push.")
                if req and req.status_code != requests.codes.accepted:
                    self.logger.error("Push not completed. Upstream is not "
                                      "responding as expected.")
        self.logger.info("Pushing to HTTP API at %s." % base_url)
        return _push


###############################################################################

class NumbersServer(DatagramServer):
    "Persistent server capable of receiving key counts."
    logger = logging.getLogger('network')

    def __init__(self, port, manager, *args, **kwargs):
        address = ":%s" % port
        super(NumbersServer, self).__init__(address, *args, **kwargs)
        self.manager = manager

    def handle(self, data, address):
        try:
            data = json.loads(data)
            user = data['user']
            value = long(data['count'])
        except (ValueError, TypeError):
            # ValueError due to bad JSON data,
            # TypeError due to bad number.
            self.logger.warn('bad data ignored.')
        else:
            self.manager.aggregate_user_data(user, value)
