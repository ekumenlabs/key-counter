from multiprocessing import Process, Value
import argparse
import socket
import time
import json
import sh

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__file__)


###############################################################################

def send_count(server_addr, server_port, user, value):
    sock = socket.socket(type=socket.SOCK_DGRAM)
    data = {'user': user, 'count': value}
    message = json.dumps(data)
    sock.connect((server_addr, server_port))
    sock.send(message)


###############################################################################

def publish_count(counter, interval, send_count):
    """Use send_count() to send the data to server.

    Data is sent at "interval", but only if new data is collected.
    """
    current_value = counter.value
    try:
        while True:
            time.sleep(interval)
            if counter.value != current_value:
                current_value = counter.value
                send_count(current_value)
    except KeyboardInterrupt:
        logger.info("Stoping send-counter process.")


###############################################################################

def key_counter(counter, keyboard_id):
    def incr_counter(line):
        if "press" in line:
            counter.value += 1
    try:
        sh.xinput('test', keyboard_id, _out=incr_counter).wait()
    except KeyboardInterrupt:
        logger.info("Stopping key-counter process.")


###############################################################################

CONNECTION_PORT = 55555
INTERVAL = 2.0  # seconds

if __name__ == '__main__':
    # TODO: handle the exceptions.

    # Parse the arguments for host, port and username.
    parser = argparse.ArgumentParser()
    parser.add_argument("user", help="the username to associate data to")
    parser.add_argument("keyboard_id", type=int,
                        help='the "ID" as returned by "xinput list"')
    parser.add_argument("server", help="server hostname or address")
    parser.add_argument(
        "-p", "--port", type=int,
        help=("server port (defaults to %s)" % CONNECTION_PORT))
    parser.add_argument(
        "-i", "--interval", type=float,
        help=("publishing interval, in seconds (defaults to %s)" % INTERVAL))
    args = parser.parse_args()
    if not args.port:
        args.port = CONNECTION_PORT
    if not args.interval:
        args.interval = INTERVAL

    # Specify the processing functions.
    def send_data(value):
        return send_count(args.server, args.port, args.user, value)

    # Setup shared data structures.
    counter = Value('L', 0)

    logger.info("Sending data to %s:%s" % (args.server, args.port))
    Process(target=key_counter, args=(counter, args.keyboard_id)).start()
    Process(target=publish_count, args=(counter, args.interval,
                                        send_data)).start()
