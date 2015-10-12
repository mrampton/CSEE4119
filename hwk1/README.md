# CSEE4119
Computer Networks
Mark Rampton
Assignment 1: Simple Chat Server and Client

Server: 
	$ ./server.py 8881

Client:
	$ ./client.py <server ip> 8881


Note: 	Client is not displaying messages as they are recieved. I was testing 
	with netcat and the experience is much better...

	Client with netcat:

	$ netcat <server ip> 8881