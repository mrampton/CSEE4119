#!/usr/bin/env python
import sys
import time
import socket
import select
import threading

BUFFSIZE = 2048

def main(argv):
	[HOST, PORT] = argv[1:3]

	if HOST and PORT:
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			sock.connect((HOST, int(PORT)))
		except socket.error:
			print "Connection refused",
			exit(-1)

		while True:

			try:
				data = sock.recv(BUFFSIZE) 
				if data.strip() == "quit":
					break

				r,w,e = select.select([sock],[],[], 0.01)
				if r:
					data = data + sock.recv(BUFFSIZE)

				response = raw_input(data)
				if response:
					sock.sendall(response)
				else: 
					sock.sendall(" ")

			except KeyboardInterrupt:
				print "\nClosing Simple Chat Client"
				break

		sock.close()

if __name__ == '__main__':
	main(sys.argv)