#!/usr/bin/env python

import sys
import socket
import threading
import time
import SocketServer

BUFFSIZE        = 1024
BLOCK_TIME      = 0
MAX_ATTEMPTS    = 1

class User():

	def __init__(self, name, ip, logged_in=True):
		self.name           = name
		self.last_login     = time.time()
		self.last_ip        = ip
		self.logged_in      = logged_in
		self.blocked_until  = None

	def log_in(self, ip):
		self.last_login     = time.time()
		self.last_ip        = ip
		self.logged_in      = True

	def log_out(self):
		self.logged_in      = False

	def block_ip(self, ip):
		self.last_ip        = ip
		self.blocked_until  = time.time() + BLOCK_TIME


class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):

	logged_in = {}  
	lock = threading.Lock()

	def help(self):
		msg = [
			"------------------------------------------------------------------",
			"whoelse                            List other connected users",
			"wholast <minutes>                  List users who have logged in",
			"                                   recently",
			"broadcast message <message>        Broadcast <message> to all users",
			"broadcast message <user> <user>    Broadcast <message> to list of users",
			"... <user> message <message>",
			"broadcast message <user> <message> Private <message> to a <user>",
			"logout                             Log out this user",
			"help                               Display this message",
			"------------------------------------------------------------------\n"
			]
		return "\n".join(msg)

	def is_logged_in(self, username):

		try:
			return self.logged_in[username].logged_in
		except KeyError:
			return False

	def log_out(self, username):

		lock = threading.Lock()
		with self.lock:
			self.logged_in[username].log_out()

	def log_in(self, username):
		user = None
		# lock = threading.Lock()
		with self.lock:
			try:
				user = self.logged_in[username]
				if user.logged_in:
					return False
				user.log_in(self.current_ip())
				self.request.sendall("I am in try!\n")

			except:
				self.request.sendall("I am in except KeyError\n")
				self.logged_in[username] = User(username, self.current_ip())

		return True

	def current_ip(self):
		return self.request.getpeername()[0]

	def currently_blocked(self, username):
		last_login = None
		last_ip = None
		user = None

		try:
			user = self.logged_in[username]
		except KeyError:
			return False

		if ((user.blocked_until > time.time() and user.last_ip == self.current_ip())
				or user.logged_in):
			print "{}: blocked until {}".format(time.ctime(), time.ctime(user.blocked_until))
			return True

		return False

	def block_user(self, username):
		
		ip = self.current_ip()
		lock = threading.Lock()

		with self.lock:
			try:
				user = self.logged_in[username].block_ip(ip)
			except KeyError:
				user = User(username, ip)
				user.block_ip(ip)
				self.logged_in[username] = user
			
	def authenticate(self):
		credentials = self.server.credentials
		user = None
		attempts = 0
		while attempts < MAX_ATTEMPTS:
			user_prompt = "%d Username: " % attempts
			pass_prompt = "%d Password: " % attempts

			self.request.sendall(user_prompt)
			username = (self.request.recv(BUFFSIZE)).strip()
			

			if username:
					
				self.request.sendall(pass_prompt)
				password = (self.request.recv(BUFFSIZE)).strip()

				try:
					if self.currently_blocked(username):
						break

					if credentials[username] == password:
						user = username


						if self.log_in(user):
							self.request.sendall("Welcome to simple chat server!\n")
						else: # oops, someone beat you to login
							user = None
						break
				except KeyError:
					pass
				
				attempts += 1
				
		if attempts == MAX_ATTEMPTS:
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
				
				if data.strip() == "quit":
					self.log_out(user)
					user = None
				if data.strip() == "help":
					self.request.sendall(self.help())
			else:
				user = self.authenticate()
		
class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):

	RUNNING = True 
	credentials = {}

	def import_credentials(self):

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