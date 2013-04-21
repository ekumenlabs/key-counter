import gevent

from core import NumbersManager, NumbersPusher, NumbersServer

import logging
logger = logging.getLogger('server')

###############################################################################

CLIENT_CONNECTION_ADDR = 'localhost'
CLIENT_CONNECTION_PORT = 55555
CLIENT_CONNECTION_TIMEOUT = 3  # seconds? see socket.socket.create_connection()

###############################################################################

FORMAT = "%(levelname)s -- %(name)s: %(message)s"
logging.basicConfig(format=FORMAT)

if __name__ == '__main__':
    logger.info('Receiving datagrams on :', CLIENT_CONNECTION_PORT)
    address = ':' + str(CLIENT_CONNECTION_PORT)

    manager = NumbersManager()
    server = NumbersServer(address, manager)
    # pusher = NumbersPusher(manager, strategy=push_strategies.PUSH_TO_STDOUT)
    pusher = NumbersPusher(manager)

    gevent.spawn(pusher.start)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info('Closing connections.')
        pusher.stop()
        server.stop()
        # Cushion wait.
        gevent.sleep(1)
