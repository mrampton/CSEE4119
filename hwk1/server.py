#!/usr/bin/env python

import sys
import socket
import threading
import time
import SocketServer
# import ipdb

BUFFSIZE = 1024

class Config():
	BLOCK_TIME = 10
	MAX_ATTEMPTS = 1

class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):

	logged_in = {} 	# {user1: {time: 500000, ip: 192.168.0.1}, user2: {etc}}

	def is_logged_in(self, user):

		return True if user in self.logged_in else False

	def currently_blocked(self, user):

		last_login = None
		last_ip = None
		try:
			last_login = self.logged_in[user]['time']
			last_ip = self.logged_in[user]['ip']
		except KeyError:
			return False

		if last_login > time.time() and last_ip == self.request.getpeername()[0]:
			print "{}: blocked until {}".format(time.ctime(), time.ctime(last_login))
			return True
		else:
			return False

	def block_user(self, user):
		self.logged_in[user] = {}
		self.logged_in[user]['time'] = (time.time() + Config.BLOCK_TIME)
		self.logged_in[user]['ip'] = self.request.getpeername()[0]

	def authenticate(self):
		credentials = self.server.credentials
		user = None
		attempts = 0
		while attempts < Config.MAX_ATTEMPTS:
			user_prompt = "%d Username: " % attempts
			pass_prompt = "%d Password: " % attempts

			self.request.sendall(user_prompt)
			username = (self.request.recv(BUFFSIZE)).strip()
			

			if username: # and not self.currently_blocked(username):
					
				self.request.sendall(pass_prompt)
				password = (self.request.recv(BUFFSIZE)).strip()

				try:
					# ipdb.set_trace()
					if self.currently_blocked(username):
						break

					if credentials[username] == password:
						user = username
						self.logged_in[user] = {
												'time'	: time.time(), 
												'ip'	: self.request.getpeername()[0]
												}
						self.request.sendall("Welcome to simple chat server!\n")
						break
				except KeyError:
					pass
				
				attempts += 1
				
		if attempts == Config.MAX_ATTEMPTS:
			self.block_user(username)

		return user

	def handle(self):
		user = None

		while ThreadedTCPServer.RUNNING:
			prompt = "Command: "
			if user:
				self.request.sendall(prompt)
				data = self.request.recv(BUFFSIZE)
				if not data:
					break
				cur_thread = threading.current_thread()
				response = "{}{}".format(prompt, data)
				if data.strip() == "quit":
					break
			else:
				user = self.authenticate()
		
class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):

	RUNNING = True 
	credentials = {}

	def import_credentials(self):
		global credentials
		for line in open('./user_pass.txt'):
			user, pw = line.split(" ")
			self.credentials[user] = pw.strip()
			print "{} has pw {}".format(user, self.credentials[user])


def main(argv):

	HOST, PORT = "localhost", int(argv[1])
	print HOST, PORT

	server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
	server.import_credentials()
	try:
		server.serve_forever()
	except (KeyboardInterrupt):
		print "Shutting down SimpleChatServer"
		ThreadedTCPServer.RUNNING = False

	server.shutdown()
	server.server_close()


if __name__ == '__main__':
	main(sys.argv)