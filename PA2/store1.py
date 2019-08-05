from socket import *
from utils import *
import time, datetime, struct, sys, random

def send(file_name, address, port, send_socket):
    f = read_file(file_name, chunk_size=DATA_LENGTH)
    send_socket.settimeout(0.01)
    next_seq = 0
    base = 0
    packet = None
    cwnd  = WND_SIZE
    timer = None
    send_buffer = {}

    while True:
        try:
            if packet is None:
                packet = make_packet(next_seq, bytes(), 0)
                next_seq = next_seq + 1
                send_buffer[next_seq] = packet
                send_socket.sendto(packet, (address, port))
                if timer is None:
                    timer = datetime.datetime.now()

            elif datetime.datetime.now() > timer + datetime.timedelta(seconds=0.5):
                curr_num = min(send_buffer.keys())
                packet = make_packet(base, send_buffer[curr_num], 1)
                send_socket.sendto(packet, (address, port))
                timer = datetime.datetime.now()

            elif send_socket.recv(MAX_SIZE) != None:
                message = send_socket.recv(MAX_SIZE)
                # extract the contents from ack_pkt
                csum, rsum, ack_seq, flag, data = extract_packet(message)
                print(data)
                if ack_seq in send_buffer:
                    send_buffer.pop(ack_seq)

                if ack_seq > base:
                    base = ack_seq
                    if base != next_seq:
                        timer = datetime.datetime.now()

            if next_seq <= base + cwnd:
                data = f.next()
                packet = make_packet(next_seq, data, 1)
                next_seq = next_seq + 1
                send_buffer[next_seq] =packet
                send_socket.sendto(packet, (address, port))

        except Exception as err:
            print(err)
            break

def usage():
    print("Usage: python Sender.py Inputfile ReceiverAddress ReceiverPort")
    exit()

def main():
    if len(sys.argv) < 4:
        usage()
        sys.exit(-1)

    start_time = time.clock()
    file_name = sys.argv[1]
    address = sys.argv[2]
    port = int(sys.argv[3])

    # create UDP socket to receive file on
    send_socket = socket(AF_INET, SOCK_DGRAM)
    send_socket.bind(("127.0.0.1", 8088))
    send(file_name, address, port, send_socket)

# if __name__ == '__main__':
#     main()
send_socket = socket(AF_INET, SOCK_DGRAM)
send_socket.bind(("127.0.0.1", 8088))
send("test.txt", "129.236.236.174", 8888, send_socket)









