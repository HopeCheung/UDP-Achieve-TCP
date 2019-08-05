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
                csum, rsum, seqnum, flag, data = extract_packet(message)

                # packet corrupted
                if csum != rsum:
                    ack = make_ack(nextseq)
                    local_socket.sendto(ack, address)
                    continue
                print("I have received the ack_seq:{}".format(seqnum))

                # receive ack packet
                if flag == ACK_OPCODE:
                    if seqnum > base:
                        print("update the base with ack_seq {}".format(seqnum))
                        base = seqnum
                        ack_cnt = 0
                        for num in send_buffer:
                            if num < seqnum:
                                send_buffer.pop(num)
                        if base != next_seq:
                            timer = datetime.datetime.now()

                    else:
                        ack_cnt = ack_cnt + 1
                        if ack_cnt == 3:
                            print("retransmit the packet with ack_num {}".format(ack_seq))
                            packet = send_buffer[seqnum]
                            local_socket.sendto(packet, (address, port))
                            ack_cnt = 0

                # receive data packet
                else:
                    print("Received the packet")
                    # for the initial packet
                    if nextseq == -1:
                        # if packet is not corrupted
                        if csum == rsum:
                            # case when initial packet is sent out of order
                            if flag == DATA_OPCODE or flag == END_OPCODE:
                                print("out of order seq", seqnum)
                                continue

                            nextseq = (seqnum + 1) & 0xffffffff
                            # else packet is in order
                            ack = make_ack(nextseq)  # another method from utils
                            print("initial seq", seqnum, flag)
                            local_socket.sendto(ack, address)
                            r.write(data)

                            # if initial packet is the last packet
                            if flag == SPECIAL_OPCODE:
                                break

                    # case when packet recieved out of order
                    elif seqnum > nextseq:
                         # if seqnum received is inside window
                        if seqnum < nextseq + WND_SIZE:
                            # put the out of order data into buffer
                            print("nextseq is ", nextseq, " so put seqnum ", seqnum, " in buffer")
                            receiver_buffer[seqnum] = (data, flag)
                        ack = make_ack(nextseq)
                        local_socket.sendto(ack, address)

                    elif seqnum == nextseq:
                        nextseq = (seqnum + 1) & 0xffffffff
                        ack = make_ack(nextseq)
                        print("current seqnum", seqnum, flag)
                        local_socket.sendto(ack, address)
                        r.write(data)

                        # if it's the last packet, and buffer is empty, don't wait anymore
                        if flag == END_OPCODE:
                            print("\n last packet received.")
                            break

                        # else, cumulatively ack the buffered packets
                        while nextseq in receiver_buffer:
                            data, flag = receiver_buffer[nextseq]
                            # yield stored data
                            r.write(data)

                            receiver_buffer.pop(nextseq)
                            nextseq = (nextseq + 1) & 0xffffffff
                            ack = make_ack(nextseq)
                            print("removed seqnum", nextseq - 1, flag)
                            print("nextseq is now ", nextseq)
                            local_socket.sendto(ack, address)

                            if flag == END_OPCODE:
                                print("\n last packet received.")
                                break

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









