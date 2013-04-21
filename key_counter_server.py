from gevent.server import DatagramServer
import hashlib
import gevent
import json

CLIENT_CONNECTION_ADDR = 'localhost'
CLIENT_CONNECTION_PORT = 55555
CLIENT_CONNECTION_TIMEOUT = 3  # seconds? see socket.socket.create_connection()


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

    PUSH_INTERVAL = 3  # seconds

    def __init__(self, manager):
        self.manager = manager
        self.running = False

    def stop(self):
        self.running = False

    def start(self):
        "Loop to collect data and call self.push()"
        self.running = True
        token = None
        while self.running:
            gevent.sleep(self.PUSH_INTERVAL)
            if token != self.manager.get_data_token():
                data, token = self.manager.get_data_packet()
                self.push(data)

    def push(self, data):
        "Send data to upstream server."
        # Implement desired push strategy.
        print "Pushing: ", data


###############################################################################

class NumbersServer(DatagramServer):

    def __init__(self, address, manager, *args, **kwargs):
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
            manager.aggregate_user_data(user, value)


###############################################################################

if __name__ == '__main__':
    print 'Receiving datagrams on :', CLIENT_CONNECTION_PORT
    address = ':' + str(CLIENT_CONNECTION_PORT)

    manager = NumbersManager()
    server = NumbersServer(address, manager)
    pusher = NumbersPusher(manager)

    gevent.spawn(pusher.start)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print 'Closing connections.'
        pusher.stop()
        server.stop()
        # Cushion wait.
        gevent.sleep(1)
