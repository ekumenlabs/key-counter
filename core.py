from gevent.server import DatagramServer
import gevent
import json

import logging


###############################################################################

class NumbersManager:
    "Collect user counts and provides collected computed values."

    def __init__(self):
        # Buffer for previous data, used to compute new values.
        self.stashed_data = []
        # Mapping from user name to previous key count.
        self.aggregated = {}

    def aggregate_user_data(self, user, count):
        "Aggregate data as a (user, count) pair"
        self.aggregated[user] = count

    def get_data_packet(self):
        """Return the data packet and a token to it.

        Each time this method is called, the data aggregated so far is used to
        compute the data packet returned, and then dropped.
        """
        # Aggregated users with no entry in the stash are sent with zero value.
        packet = {user: 0 for user in self.aggregated}

        new_stash = []
        for user, stashed_count in self.stashed_data:
            # Compute for aggregated users.
            if user in packet:
                current_count = self.aggregated[user]
                # Include user and its current count in the next stash.
                new_stash.append((user, current_count))
                # Update user computed value.
                packet[user] = self._compute(stashed_count, current_count)
        # Update the stash and dropped the used up aggregated data.
        self.stashed_data = new_stash
        self.aggregated = {}

        return packet


###############################################################################

class NumbersPusher:
    "Push packed key count data to the destination sever."

    logger = logging.getLogger('push.pusher')

    def __init__(self, manager, interval, strategy='test', *args, **kwargs):
        self.manager = manager
        self.interval = interval
        self.running = False
        # Compose the push strategy object, and delegate to it.
        self._pusher = PushStrategy(strategy, *args, **kwargs)

    def stop(self):
        self.logger.info("Stoping the pusher event loop.")
        self.running = False

    def start(self):
        "Loop to collect data and call self.push()"
        self.running = True
        token = None
        while self.running:
            gevent.sleep(self.interval)
            if token != self.manager.get_data_token():
                data, token = self.manager.get_data_packet()
                self.push(data)

    def push(self, data):
        # Delegate to the selected push strategy.
        self.logger.debug("Calling push() data.")
        self._pusher.push(data)


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

    def _test_push(self):
        def _push(data):
            self.logger.debug("Pushing data.")
            self.pushed.append(data)
            self.logger.debug("Current pushed data: %s" % self.pushed)
        self.logger.info("Test pushing: "
                         "data is accumulated in self.pushed list.")
        self.pushed = []
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
            print 'bad data ignored.'
        else:
            self.manager.aggregate_user_data(user, value)
