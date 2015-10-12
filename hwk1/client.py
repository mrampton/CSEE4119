#!/usr/bin/env python
import re
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

		# import ipdb; ipdb.set_trace()
		thread = MessagesThread(await_server_response, sock.dup())
		thread.daemon = True
		thread.start()

		login_prompt = '^[0-9]?\s?(Username|Password|Command):\s+'

		while True:
			try:
				# print "Command: "
				# r,w,e = select.select([sock], [], [], 1)
				# data = None
				# if r:
				# data = sock.recv(BUFFSIZE) 
				# print data.strip(),
				data = sock.recv(BUFFSIZE) 
				# m = re.match(login_prompt, data)
				# if m:
				# 	# print data.strip(),
				# 	pass
				# else:
				# 	print "hmm"
				# 	print data

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


########################################
# woker thread; delivers messages to users
########################################

class MessagesThread(threading.Thread):
    def __init__(self, target, *args):
        self._target = target
        self._args = args
        threading.Thread.__init__(self)
 
 	def join(self, timeout=None):
 		self.stoprequest.set()
 		super(FuncThread, self).join(timeout)

    def run(self):
        self._target(*self._args)

def await_server_response(sock):
	
	while True:
		time.sleep(1)
		r,w,e = select.select([sock], [], [], 1)
		data = None
		if r:
			data = sock.recv(BUFFSIZE) 
			print data.strip()


if __name__ == '__main__':
	main(sys.argv)