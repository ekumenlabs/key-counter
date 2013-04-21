from gevent.server import DatagramServer
import json

CONNECTION_ADDR = 'localhost'
CONNECTION_PORT = 55555
CONNECTION_TIMEOUT = 3  # seconds? check socket.socket.create_connection(


class NumbersServer(DatagramServer):

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
            print '%s (%s): %i' % (user, address[0], value)


if __name__ == '__main__':
    print 'Receiving datagrams on :', CONNECTION_PORT
    server = NumbersServer(':' + str(CONNECTION_PORT))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print 'Closing connection.'
        server.stop()
