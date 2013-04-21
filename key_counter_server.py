import gevent
import argparse
import core

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
            'formatter': 'brief'
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
logger = logging.getLogger('server')

###############################################################################

CONNECTION_PORT = 55555
PUSH_INTERVAL = 3.0  # seconds

if __name__ == '__main__':

    # Parse the arguments for host, port and username.
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p", "--port", type=int,
        help=("server port (defaults to %s)" % CONNECTION_PORT))
    parser.add_argument(
        "-i", "--interval", type=float,
        help=("publishing interval, in seconds (defaults to %s)"
              % PUSH_INTERVAL))
    args = parser.parse_args()
    if not args.port:
        args.port = CONNECTION_PORT
    if not args.interval:
        args.port = PUSH_INTERVAL

    # Initialize core components.
    manager = core.NumbersManager()
    server = core.NumbersServer(args.port, manager)
    pusher = core.NumbersPusher(manager, args.interval,
                                strategy=core.PushStrategy.PUSH_TO_STDOUT)

    # Spawn the upstream pusher.
    gevent.spawn(pusher.start)

    try:
        logger.info("Receiving user data at *:%s" % args.port)
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info('Closing connections.')
        pusher.stop()
        server.stop()
        # Cushion wait.
        gevent.sleep(1)
