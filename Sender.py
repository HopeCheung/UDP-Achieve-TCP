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
            # If it's the first time to send packet, send an initial packet
            if packet is None:
                packet = make_packet(next_seq, bytes(), 0)
                send_buffer[next_seq] = packet
                next_seq = next_seq + 1
                send_socket.sendto(packet, (address, port))
                # If the timer didn't start, start timer
                if timer is None:
                    timer = datetime.datetime.now()

            # if timeout, retransmit the packet with smallest num
            elif datetime.datetime.now() > timer + timeout:
                # make sure that the sender can stop when there are no more packets to send
                if FIN == 1:
                    # send the final packet with flag = 2
                    packet = make_packet(base, bytes(), 2)
                    send_socket.sendto(packet, (address, port))
                    # Wait for 5 seconds, then stop sender
                    if FIN_cnt  < 10:
                        FIN_cnt = FIN_cnt + 1
                        continue
                    else:
                        break

                # time out, resend the packet with seqnum = base
                packet = send_buffer[base]
                send_socket.sendto(packet, (address, port))
                # restart the timer
                timer = datetime.datetime.now()

            # receive the packet from the socket
            message = send_socket.recv(MAX_SIZE)

            # when drop-packet happen
            if message == None:
                continue
            elif message != None:
                # extract the contents from ack_pkt
                csum, rsum, ack_seq, flag, data = extract_packet(message)
                # when corrupt happen
                if csum != rsum:
                    continue

                # if ack is correct
                if ack_seq > base:
                    # update the base
                    base = ack_seq
                    ack_cnt = 0
                    # clear the packet in window with seqnum smaller than ack_seq
                    for num in send_buffer:
                        if num < ack_seq:
                            send_buffer.pop(num)
                    # restart the timer
                    if base != next_seq:
                        timer = datetime.datetime.now()

                # after receive three duplicate packets, retranmit the packet 
                else:
                    ack_cnt = ack_cnt + 1
                    if ack_cnt == 3:
                        packet = send_buffer[ack_seq]
                        send_socket.sendto(packet, (address, port))
                        ack_cnt = 0

        except Exception:
            try:
                # send the packet if the next_seq < base + window_size
                if next_seq <= base + int(cwnd):
                    data = f.next()
                    packet = make_packet(next_seq, data, 1)
                    send_buffer[next_seq] = packet
                    # next_seq plus 1
                    next_seq = next_seq + 1
                    send_socket.sendto(packet, (address, port))
            except Exception:
                # if there are no more data, send the data left in window
                if len(send_buffer.keys()) != 0:
                    if base == next_seq and FIN == 0:
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

    # create UDP socket to send file
    send_socket = socket(AF_INET, SOCK_DGRAM)
    send_socket.bind(("127.0.0.1", 8088))
    send(file_name, address, port, send_socket)

if __name__ == '__main__':
    main()










