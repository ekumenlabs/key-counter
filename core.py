from gevent.server import DatagramServer
import hashlib
import gevent
import json

import logging


###############################################################################

class NumbersManager:
    "Collect user counts, and sends them together."

    # Mapping from user name to current key count, shared by all managers.
    # It'll be populated on demand.
    user_data = {}

    def _hash_user_data(self):
        encoded_data = json.dumps(self.user_data, sort_keys=True)
        return hashlib.md5(encoded_data).hexdigest()

    def aggregate_user_data(self, user, count):
        # Add the user to the mapping.
        if not user in self.user_data:
            self.user_data[user] = []
        # Aggregate the latest count.
        self.user_data[user].append(count)

    def get_data_token(self):
        return self._hash_user_data()

    def get_data_packet(self):
        # TODO: This operation should produce both the packet and the token
        # atomically.
        packet = {}
        # Send the last count aggregated for each user.
        for user in self.user_data:
            packet[user] = self.user_data[user][-1]
        token = self._hash_user_data()
        return packet, token


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
    """A push strategy takes a data dict, in the format of the first element of
    the tuple returned by NumbersManager.get_data_packet(), and pushes it
    upstream.

    The details of what "upstream" is, and how to push that data to it, are
    isolated by each strategy.
    """

    PUSH_TEST = 'test'
    PUSH_TO_STDOUT = 'stdout'
    PUSH_TO_FILE = 'file'
    PUSH_TO_REST = 'rest'

    def __init__(self, strategy, *args, **kwargs):
        self.logger = logging.getLogger('push.strategy.%s' % strategy)
        if strategy == PushStrategy.PUSH_TEST:
            self.push = self._test_push(*args, **kwargs)
        elif strategy == PushStrategy.PUSH_TO_STDOUT:
            self.push = self._push_to_stdout(*args, **kwargs)
        elif strategy == PushStrategy.PUSH_TO_FILE:
            self.push = self._push_to_file(*args, **kwargs)
        elif strategy == PushStrategy.PUSH_TO_REST:
            self.push = self._push_to_REST_API(*args, **kwargs)
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

    def _push_to_REST_API(self, base_URL):
        """Push POSTing to a REST API.

        The API must implement the following endpoints:

        "base_URL/:user" : will receive an integer value which corresponds to
        the latest key count for that user.

        Each end point should accept a single integer as data payload, and
        return a status code of 202 Accepted.
        """
        import json
        import requests
        # No trailing slash on the base URL.
        base_url = base_URL
        if base_URL[-1] == '/':
            base_url = base_URL[0:-1]

        def _push(data):
            for user in data:
                url = "%s/%s" % (base_url, user)
                payload = json.dumps(data[user])
                req = requests.post(url, data=payload)
                if req.status_code != requests.codes.accepted:
                    # Push was not completed.
                    self.logger.error("Push not completed. "
                                      "I blame the backend upstream.")
        self.logger.info("Pushing to REST API at %s." % base_url)
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
