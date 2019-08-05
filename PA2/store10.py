from socket import *
from utils import *
import time, datetime, struct, sys, random

storage = {}

def operate(input_file, address, port, local_socket, output_file):
    print("Process Start...")

    f = read_file(input_file, chunk_size=DATA_LENGTH)
    r = open(output_file, "wb+")
    local_socket.settimeout(0.01)

    # parameters for sender
    next_seq = 0
    base = 0
    packet = None
    cwnd = WND_SIZE
    timer = None
    send_buffer = {}
    ack_cnt = 0
    FIN = 0
    FIN_cnt = 0
    timeout = datetime.timedelta(seconds=0.5)

    # parameters for receiver
    receiver_buffer = {}  # buffer for storing out of order packets
    nextseq = -1  # initial next sequence number

    while True:
        try:
            if packet is None:
                packet = make_packet(next_seq, bytes(), 0)
                send_buffer[next_seq] = packet
                next_seq = next_seq + 1
                local_socket.sendto(packet, (address, port))
                if timer is None:
                    timer = datetime.datetime.now()

            elif datetime.datetime.now() > timer + timeout:
                if FIN == 1:
                    print("the last packet is {}".format(base))
                    packet = make_packet(base, bytes(), 2)
                    local_socket.sendto(packet, (address, port))
                    if FIN_cnt  < 10:
                        FIN_cnt = FIN_cnt + 1
                        continue
                    else:
                        print("second step to close connection")
                        FIN = 2
                        continue
                elif FIN == 2:
                    break

                print("time out, resend the packet {}, the next_seq is {}".format(base, next_seq))
                packet = send_buffer[base]
                local_socket.sendto(packet, (address, port))
                timer = datetime.datetime.now()

            message_orig = local_socket.recv(MAX_SIZE)
            #message = channel(message_orig)
            message = message_orig

            if message == None:
                print("Ack packet dropped")
                continue
            elif message != None:
                print("Before change window:{}".format(cwnd))
                # extract the contents from ack_pkt
                csum, rsum, ack_seq, flag, data = extract_packet(message)
                if csum != rsum:
                    ack = make_ack(nextseq)
                    local_socket.sendto(ack, address)
                    continue
                print("I have received the ack_seq:{}".format(ack_seq))

                if flag == ACK_OPCODE:
                    if ack_seq > base:
                        print("update the base with ack_seq {}".format(ack_seq))
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
                            print("retransmit the packet with ack_num {}".format(ack_seq))
                            packet = send_buffer[ack_seq]
                            local_socket.sendto(packet, (address, port))
                            ack_cnt = 0

        except Exception:
            try:
                if next_seq <= base + int(cwnd):
                    data = f.next()
                    packet = make_packet(next_seq, data, 1)
                    send_buffer[next_seq] = packet
                    next_seq = next_seq + 1
                    local_socket.sendto(packet, (address, port))
            except Exception:
                if len(send_buffer.keys()) != 0:
                    print("Now the base is {}".format(base))
                    if base == next_seq and FIN == 0:
                        print("first step to close connection")
                        FIN = 1
                    continue
                else:
                    FIN = 1
                    continue


def usage():
    print("Usage: python Sender2.py Inputfile ReceiverAddress ReceiverPort Outputfile")
    exit()

def main():
    if len(sys.argv) < 5:
        usage()
        sys.exit(-1)

    start_time = time.clock()
    input_file = sys.argv[1]
    address = sys.argv[2]
    port = int(sys.argv[3])
    output_file = sys.argv[4]

    # create UDP socket to receive file on
    local_socket = socket(AF_INET, SOCK_DGRAM)
    local_socket.bind(("127.0.0.1", 8088))
    operate(input_file, address, port, local_socket, output_file)

if __name__ == '__main__':
    main()
# send_socket = socket(AF_INET, SOCK_DGRAM)
# send_socket.bind(("127.0.0.1", 8088))
# send("test.txt", "129.236.236.174", 8888, send_socket)









