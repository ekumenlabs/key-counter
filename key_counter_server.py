from gevent.server import DatagramServer

CONNECTION_ADDR = 'localhost'
CONNECTION_PORT = 55555
CONNECTION_TIMEOUT = 3  # seconds? check socket.socket.create_connection(


class NumbersServer(DatagramServer):

    def handle(self, data, address):
        try:
            value = long(data)
        except TypeError:
            print 'bad data ignored.'
        else:
            print '%s: got %i' % (address[0], value)


if __name__ == '__main__':
    print 'Receiving datagrams on :', CONNECTION_PORT
    server = NumbersServer(':' + str(CONNECTION_PORT))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print 'Closing connection.'
        server.stop()
