1. Basic Sender: used to send the file

	Run python Sender.py Inputfile ReceiverAddress ReceiverPort
	Run python Receiver.py Inputfile ReceiverAddress ReceiverPort

	The sender's address and port are 127.0.0.1, 8088
	The Inputfile is put in the same directory with Sender.py
	The output file will be stored in the same directory with Receiver.py

2. Receiver: used to receive the file

3. utils.py: some tools and channel used in the program.

4. Sender2, Receiver2: used to send and receive the files

	Run python Sender2.py Inputfile ReceiverAddress ReceiverPort SenderAddress SenderPort Outputfile
	Run python Receiver2.py Inputfile SenderAddress SenderPort ReceiverAddress ReceiverPort Outputfile

	Inputfile: file to send
	ReceiverAddress: address for receiver
	ReceiverPort: port for receiver
	SenderAddress: address for sender
	SenderPort: port for sender
	Outputfile: received file

	eg:
		python Sender2.py test1.txt 129.236.236.74 8888 127.0.0.1 8088 output1.txt
		python Receiver2.py test2.txt 127.0.0.1 8088 129.236.236.74 8888 output2.txt

	And I implement cogestion control and timeout control in the Sender2.py, Receiver2.py

