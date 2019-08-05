from socket import *
from utils import *
import time, datetime, struct, sys, random

storage = {}

def send(file_name, address, port, send_socket):
    f = read_file(file_name, chunk_size=DATA_LENGTH)
    send_socket.settimeout(0.01)
    next_seq = 0
    base = 0
    packet = None
    cwnd  = WND_SIZE
    timer = None
    send_buffer = {}
    ack_cnt = 0
    FIN = 0
    FIN_cnt = 0
    timeout = datetime.timedelta(seconds=0.5)

    while True:
        try:
            if packet is None:
                packet = make_packet(next_seq, bytes(), 0)
                send_buffer[next_seq] = packet
                next_seq = next_seq + 1
                send_socket.sendto(packet, (address, port))
                if timer is None:
                    timer = datetime.datetime.now()

            elif datetime.datetime.now() > timer + timeout:
                if FIN == 1:
                    #print("the last packet is {}".format(base))
                    packet = make_packet(base, bytes(), 2)
                    send_socket.sendto(packet, (address, port))
                    if FIN_cnt  < 10:
                        FIN_cnt = FIN_cnt + 1
                        continue
                    else:
                        break

                #print("time out, resend the packet {}, the next_seq is {}".format(base, next_seq))
                packet = send_buffer[base]
                send_socket.sendto(packet, (address, port))
                timer = datetime.datetime.now()

            message = send_socket.recv(MAX_SIZE)

            if message == None:
                #print("Ack packet dropped")
                continue
            elif message != None:
                #print("Before change window:{}".format(cwnd))
                # extract the contents from ack_pkt
                csum, rsum, ack_seq, flag, data = extract_packet(message)
                if csum != rsum:
                    #print("Ack packet corrupted")
                    continue
                #print("I have received the ack_seq:{}".format(ack_seq))

                if ack_seq > base:
                    #print("update the base with ack_seq {}".format(ack_seq))
                    base = ack_seq
                    ack_cnt = 0
                    for num in send_buffer:
                        if num < ack_seq:
                            send_buffer.pop(num)
                    if base != next_seq:
                        timer = datetime.datetime.now()

                else:
                    ack_cnt = ack_cnt + 1
                    if ack_cnt == 3:
                        #print("retransmit the packet with ack_num {}".format(ack_seq))
                        packet = send_buffer[ack_seq]
                        send_socket.sendto(packet, (address, port))
                        ack_cnt = 0

        except Exception:
            try:
                if next_seq <= base + int(cwnd):
                    data = f.next()
                    packet = make_packet(next_seq, data, 1)
                    send_buffer[next_seq] = packet
                    next_seq = next_seq + 1
                    send_socket.sendto(packet, (address, port))
            except Exception:
                if len(send_buffer.keys()) != 0:
                    if base == next_seq and FIN == 0:
                        #print("first step to close connection")
                        FIN = 1
                    continue
                else:
                    FIN = 1
                    continue


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

if __name__ == '__main__':
    main()










