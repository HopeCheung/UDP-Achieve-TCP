from socket import *
from utils import *
import time, datetime, struct, sys, random

SEND_OPCODE = 5

def operate(input_file, address, port, local_socket, output_file):
    print("Process Start...")

    f = read_file(input_file, chunk_size=DATA_LENGTH)
    r = open(output_file, "wb+")
    local_socket.settimeout(0.01)

    # parameters for sender
    next_seq = 0
    base = 0
    packet = None
    cwnd = 1
    threshold = WND_SIZE
    timer = None
    send_buffer = {}
    ack_cnt = 0
    FIN_S = 0
    FIN_cnt = 0
    FIN_R = 0
    timeout = datetime.timedelta(seconds=0.5)

    # parameters to control timeout
    alpha, Beta = 0.125, 0.25
    EstimateRTT = 500000
    DevRTT = 0
    time_slots = {}

    # parameters for receiver
    receiver_buffer = {}  # buffer for storing out of order packets
    nextseq = -1  # initial next sequence number

    while True:
        try:
            # If it's the first time to send packet, send an initial packet
            if packet is None:
                packet = make_packet(next_seq, bytes(), 0)
                send_buffer[next_seq] = packet
                next_seq = next_seq + 1
                local_socket.sendto(packet, (address, port))
                # If the timer didn't start, start timer
                if timer is None:
                    timer = datetime.datetime.now()

            # if timeout, retransmit the packet with smallest num
            elif datetime.datetime.now() > timer + timeout:
                # make sure that the sender can stop when there are no more packets to send
                if FIN_S == 1:
                    # send the final packet with flag = 2
                    packet = make_packet(base, bytes(), 2)
                    local_socket.sendto(packet, (address, port))
                    timeout = datetime.timedelta(seconds=0.5)
                    local_socket.settimeout(0.5)
                    timer = datetime.datetime.now()
                    FIN_cnt = FIN_cnt + 1
                    # Wait for 5 seconds, then stop the end
                    if FIN_cnt >= 10:
                        break
                    continue

                # if no more data to send, and no more data to receive, stop the end
                elif FIN_S == 2:
                    if FIN_R == 1:
                        break
                    timeout = datetime.timedelta(seconds=0.5)
                    local_socket.settimeout(0.5)
                    timer = datetime.datetime.now()
                    continue

                # time out, resend the packet with seqnum = base
                packet = send_buffer[base]
                local_socket.sendto(packet, (address, port))
                # restart the timer
                timer = datetime.datetime.now()
                # if loss event happen, set window size = 1, and set threshold to half of window size
                threshold = int(cwnd / 2) if cwnd != 1 else 1
                cwnd = 1
                time_slots = {}

            # receive the packet from the socket
            message_orig = local_socket.recv(MAX_SIZE)
            message = channel(message_orig)

            # when drop-packet happen
            if message == None:
                continue

            elif message != None:
                # FIN_cnt used to stop the timer when there are no more data to receive
                FIN_cnt = 0
                # extract the contents from ack_pkt
                csum, rsum, seqnum, flag, data = extract_packet(message)

                # packet corrupted, ask for the packet again
                if csum != rsum:
                    ack = make_ack(nextseq)
                    local_socket.sendto(ack, (address, port))
                    continue

                # the initial packet is end, set FIN_S = 2, which means no more data to send
                if flag == SEND_OPCODE and FIN_S == 1:
                    FIN_S = 2
                    if FIN_R == 1:
                        break
                    # send the last packet with falg=2
                    packet = make_packet(base, bytes(), 2)
                    local_socket.sendto(packet, (address, port))
                    continue

                # receive ack packet
                elif flag == ACK_OPCODE:
                    # Congestion Control
                    if cwnd >= threshold:
                        # if window size is larger than threshold, increase by one 
                        cwnd = cwnd + (1. / cwnd)
                    else:
                        # double the window size
                        cwnd = cwnd + 1

                    # Timeout Control
                    if seqnum in time_slots:
                        # caculate the new timeout
                        SampleRTT = datetime.datetime.now() - time_slots[seqnum]
                        SampleRTT = SampleRTT.seconds * 1000000 + SampleRTT.microseconds
                        # estimate RTT
                        EstimateRTT = (1 - alpha) * EstimateRTT + SampleRTT * alpha
                        # dev for RTT
                        DevRTT = (1 - Beta) * DevRTT + Beta * abs(SampleRTT - EstimateRTT)
                        timeout = datetime.timedelta(microseconds=int(EstimateRTT + 4 * DevRTT))
                        time_slots.pop(seqnum)

                    # if ack is correct
                    if seqnum > base:
                        # update the base
                        base = seqnum
                        ack_cnt = 0
                        # clear the packet in window with seqnum smaller than ack_seq
                        for num in send_buffer:
                            if num < seqnum:
                                send_buffer.pop(num)
                        # restart the timer
                        if base != next_seq:
                            timer = datetime.datetime.now()

                    # after receive three duplicate packets, retranmit the packet 
                    else:
                        ack_cnt = ack_cnt + 1
                        if ack_cnt == 3:
                            packet = send_buffer[seqnum]
                            local_socket.sendto(packet, (address, port))
                            ack_cnt = 0
                            # if loss event happen, set window size = 1, and set threshold to half of window size
                            threshold = int(cwnd / 2) if cwnd != 1 else 1
                            cwnd = 1
                            time_slots = {}

                # receive data packet
                else:
                    # for the initial packet
                    if nextseq == -1:
                        # if packet is not corrupted
                        if csum == rsum:
                            # case when initial packet is sent out of order
                            if flag == DATA_OPCODE or flag == END_OPCODE:
                                continue

                            nextseq = (seqnum + 1) & 0xffffffff
                            # else packet is in order
                            ack = make_ack(nextseq)  # another method from utils
                            local_socket.sendto(ack, (address, port))
                            r.write(data)

                            # if initial packet is the last packet
                            if flag == SPECIAL_OPCODE:
                                FIN_R = 1
                                if FIN_S == 2:
                                    break
                                packet = make_packet(base, bytes(), 5)
                                local_socket.sendto(packet, (address, port))
                                continue

                    # case when packet recieved out of order
                    elif seqnum > nextseq:
                         # if seqnum received is inside window
                        if seqnum < nextseq + WND_SIZE:
                            # put the out of order data into buffer
                            receiver_buffer[seqnum] = (data, flag)
                        ack = make_ack(nextseq)
                        local_socket.sendto(ack, (address, port))

                    elif seqnum == nextseq:
                        nextseq = (seqnum + 1) & 0xffffffff
                        ack = make_ack(nextseq)
                        local_socket.sendto(ack, (address, port))
                        r.write(data)

                        # if it's the last packet, and buffer is empty, don't wait anymore
                        if flag == END_OPCODE:
                            FIN_R = 1
                            if FIN_S == 2:
                                break
                            packet = make_packet(base, bytes(), 5)
                            local_socket.sendto(packet, (address, port))
                            continue

                        # else, cumulatively ack the buffered packets
                        while nextseq in receiver_buffer:
                            data, flag = receiver_buffer[nextseq]
                            # write the data into file
                            r.write(data)

                            receiver_buffer.pop(nextseq)
                            nextseq = (nextseq + 1) & 0xffffffff
                            ack = make_ack(nextseq)
                            local_socket.sendto(ack, (address, port))

                            if flag == END_OPCODE:
                                # if no more data to send and no more data to receive, stop the end
                                FIN_R = 1
                                if FIN_S == 2:
                                    break
                                packet = make_packet(base, bytes(), 5)
                                local_socket.sendto(packet, (address, port))
                                continue

        except Exception:
            try:
                # send the packet if the next_seq < base + window_size
                if next_seq <= base + int(cwnd):
                    data = f.next()
                    packet = make_packet(next_seq, data, 1)
                    send_buffer[next_seq] = packet
                    # next_seq plus 1
                    next_seq = next_seq + 1
                    time_slots[next_seq] = datetime.datetime.now()
                    local_socket.sendto(packet, (address, port))
            except Exception:
                # if there are no more data, send the data left in window
                if len(send_buffer.keys()) != 0:
                    if base == next_seq and FIN_S == 0:
                        FIN_S = 1
                    continue
                else:
                    FIN_S = 1
                    continue

def usage():
    print("Usage: python Sender2.py Inputfile ReceiverAddress ReceiverPort SenderAddress SenderPort Outputfile")
    exit()

def main():
    if len(sys.argv) < 7:
        usage()
        sys.exit(-1)

    start_time = time.clock()
    input_file = sys.argv[1]
    address = sys.argv[2]
    port = int(sys.argv[3])
    local_address = sys.argv[4]
    local_port = int(sys.argv[5])
    output_file = sys.argv[6]

    # create UDP socket to send file
    local_socket = socket(AF_INET, SOCK_DGRAM)
    local_socket.bind((local_address, local_port))
    operate(input_file, address, port, local_socket, output_file)

if __name__ == '__main__':
    main()










