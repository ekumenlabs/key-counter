import gevent
import argparse
import key_counter.core
import key_counter.config

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
            'level': 'INFO',
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
        'config': {
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

    # Parse the arguments for port and publishing interval.
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "config_file",
        help="configuration file (JSON) to know where to publish to.")
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
        args.interval = PUSH_INTERVAL

    # Initialize core components.
    manager = key_counter.core.NumbersManager()
    server = key_counter.core.NumbersServer(args.port, manager)
    pusher = key_counter.core.NumbersPusher(manager, args.interval)

    # Spawn the upstream pusher, dry.
    gevent.spawn(pusher.start)

    # Initialize the configuration components.
    config_manager = key_counter.config.ConfigManager(pusher)
    file_config_manager = key_counter.config.ConfigFileManager(
        config_manager, args.config_file, interval=5)

    # pusher = key_counter.core.NumbersPusher(
    #     manager, args.interval,
    #     strategy=key_counter.core.PushStrategy.PUSH_TO_HTTP,
    #     base_URL='http://localhost:3000/')

    try:
        logger.info("Receiving user data at *:%s" % args.port)
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info('Closing connections.')
        file_config_manager.stop()
        pusher.stop()
        server.stop()
        # Cushion wait.
        gevent.sleep(1)
