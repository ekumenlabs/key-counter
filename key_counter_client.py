from multiprocessing import Process, Value
import socket
import time
import sh


KEYBOARD_ID = '8'
SHOW_INTERVAL = 3  # seconds

CONNECTION_ADDR = 'localhost'
CONNECTION_PORT = 55555
CONNECTION_TIMEOUT = 2.0  # seconds


###############################################################################

def send_count(value):
    sock = socket.socket(type=socket.SOCK_DGRAM)
    message = str(value)
    sock.connect((CONNECTION_ADDR, CONNECTION_PORT))
    sock.send(message)


###############################################################################

def show_counter(counter):
    current_value = counter.value
    while True:
        time.sleep(SHOW_INTERVAL)
        if counter.value != current_value:
            current_value = counter.value
            send_count(current_value)


###############################################################################

def key_counter(counter):
    def incr_counter(line):
        if "press" in line:
            counter.value += 1
    sh.xinput('test', KEYBOARD_ID, _out=incr_counter).wait()


###############################################################################

if __name__ == '__main__':
    counter = Value('L', 0)

    counter_process = Process(target=key_counter, args=(counter,))
    # counter_process.daemon = True
    shower_process = Process(target=show_counter, args=(counter,))
    # shower_process.daemon = True

    shower_process.start()
    counter_process.start()
