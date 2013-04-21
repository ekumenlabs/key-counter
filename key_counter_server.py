import gevent

from core import NumbersManager, NumbersPusher, NumbersServer, PushStrategy

###############################################################################

CLIENT_CONNECTION_ADDR = 'localhost'
CLIENT_CONNECTION_PORT = 55555
CLIENT_CONNECTION_TIMEOUT = 3  # seconds? see socket.socket.create_connection()

###############################################################################

LOGGING = {
    'version': 1,
    'formatters': {
        'simple': {
            'format': '%(levelname)s -- %(name)s -- %(message)s'
        },
        'brief': {
            'format': '%(message)s'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        }
    },
    'loggers': {
        'server': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'network': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'push': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'manager': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    }
}
import logging
import logging.config
logging.config.dictConfig(LOGGING)

###############################################################################

logger = logging.getLogger('server')

if __name__ == '__main__':
    logger.info('Receiving datagrams on : %s' % CLIENT_CONNECTION_PORT)
    address = ':' + str(CLIENT_CONNECTION_PORT)

    manager = NumbersManager()
    server = NumbersServer(address, manager)
    pusher = NumbersPusher(manager, strategy=PushStrategy.PUSH_TO_FILE,
                           file_name='output.log')

    gevent.spawn(pusher.start)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info('Closing connections.')
        pusher.stop()
        server.stop()
        # Cushion wait.
        gevent.sleep(1)
