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

    while True:
        try:
            print(next_seq, base)
            print(list(send_buffer.keys()))
            if packet is None:
                packet = make_packet(next_seq, bytes(), 0)
                send_buffer[next_seq] = packet
                next_seq = next_seq + 1
                send_socket.sendto(packet, (address, port))
                if timer is None:
                    timer = datetime.datetime.now()

            elif datetime.datetime.now() > timer + datetime.timedelta(seconds=0.5):
                curr_num = min(send_buffer.keys())
                print("time out, resend the packet {}".format(curr_num))
                packet = send_buffer[curr_num]
                csum, rsum, ack_seq, flag, data = extract_packet(packet)
                print("curr resending packet's flag:{}".format(flag))
                if flag == 2:
                    break
                send_socket.sendto(packet, (address, port))
                timer = datetime.datetime.now()

            message = send_socket.recv(MAX_SIZE)
            if message != None:
                print("I have received the ack")
                # extract the contents from ack_pkt
                csum, rsum, ack_seq, flag, data = extract_packet(message)

                # if flag == 2:
                #     break
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
                        print("retransmit the packet with ack_num")
                        packet = send_buffer[ack_seq]
                        send_socket.sendto(packet, (address, port))
                        ack_cnt = 0

        except Exception:
            try:
                if next_seq <= base + cwnd:
                    data = f.next()
                    packet = make_packet(next_seq, data, 1)
                    send_buffer[next_seq] = packet
                    next_seq = next_seq + 1
                    send_socket.sendto(packet, (address, port))
            except Exception:
                packet = make_packet(base, bytes(), 2)
                send_buffer[base] = packet
                send_socket.sendto(packet, (address, port))
                # print("Sending break")
                # break

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









