from multiprocessing import Process, Value
import socket
import time
import json
import sh

import logging
logger = logging.getLogger('client')


KEYBOARD_ID = '8'
USER = 'etoccalino'

SHOW_INTERVAL = 3  # seconds

CONNECTION_ADDR = 'localhost'
CONNECTION_PORT = 55555
CONNECTION_TIMEOUT = 2.0  # seconds


###############################################################################

def send_count(value):
    sock = socket.socket(type=socket.SOCK_DGRAM)
    data = {'user': USER, 'count': value}
    message = json.dumps(data)
    sock.connect((CONNECTION_ADDR, CONNECTION_PORT))
    sock.send(message)


###############################################################################

def show_counter(counter):
    current_value = counter.value
    try:
        while True:
            time.sleep(SHOW_INTERVAL)
            if counter.value != current_value:
                current_value = counter.value
                send_count(current_value)
    except KeyboardInterrupt:
        logger.info("Stoping send-counter process.")


###############################################################################

def key_counter(counter):
    def incr_counter(line):
        if "press" in line:
            counter.value += 1
    try:
        sh.xinput('test', KEYBOARD_ID, _out=incr_counter).wait()
    except KeyboardInterrupt:
        logger.info("Stopping key-counter process.")


###############################################################################

if __name__ == '__main__':
    # TODO: handle the exceptions.

    counter = Value('L', 0)
    Process(target=key_counter, args=(counter,)).start()
    Process(target=show_counter, args=(counter,)).start()
