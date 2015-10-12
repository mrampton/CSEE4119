#!/usr/bin/env python
import re
import sys
import errno
import socket
import select
import threading
import time
import SocketServer

BUFFSIZE        = 2048
TIME_OUT		= 60 * 30
BLOCK_TIME      = 10
MAX_ATTEMPTS    = 3

def main(argv):

	HOST, PORT = "", int(argv[1])

	server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
	server.daemon = True
	server.import_credentials()

	thread = MessagesThread(await_user_messages)
	thread.daemon = True
	thread.start()

	try:
		server.serve_forever()
	except IOError, e:
		if e.errno == 32: pass
	except (KeyboardInterrupt):
		print "\nShutting down SimpleChatServer"
		ThreadedTCPServer.running = False

	server.shutdown()
	server.server_close()
	exit(0)

class User():

	def __init__(self, name, ip, socket, logged_in=True):
		self.name           = name
		self.last_login     = None
		self.last_ip        = ip
		self.logged_in      = logged_in
		self.blocked_until  = None
		self.socket			= None

	def log_in(self, ip, socket):
		self.last_login     = time.time()
		self.last_ip        = ip
		self.logged_in      = True
		self.socket			= socket

	def log_out(self):
		self.logged_in      = False
		self.socket			= None

	def block_ip(self, ip):
		self.last_ip        = ip
		self.blocked_until  = time.time() + BLOCK_TIME


class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):

	logged_in 		= {}  
	message_queue 	= {}
	lock 			= threading.Lock()

	########################################
	# user status and helper methods
	########################################

	def is_logged_in(self, username):

		try:
			return self.logged_in[username].logged_in
		except KeyError:
			return False

	def log_out(self, username):
		with self.lock:
			self.logged_in[username].log_out()
		return None

	def log_in(self, username):
		user = None
		ip = self.current_ip()
		with self.lock:
			try:
				user = self.logged_in[username]
				if user.logged_in:
					return False
				user.log_in(ip, self.request)
			except KeyError:
				user = User(username, ip, self.request)
				user.log_in(ip, self.request)
				self.logged_in[username] = user

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
			return True

		return False

	def block_user(self, username):
		
		ip = self.current_ip()
		with self.lock:
			try:
				user = self.logged_in[username].block_ip(ip)
			except KeyError:
				user = User(username, ip, self.request, False)
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

	########################################
	# user commands are handled below
	########################################

	def help(self):
		msg = [
			"------------------------------------------------------------------",
			"whoelse                            List other connected users",
			"wholast <number>                   Users who logged in during last",
			"                                   <number> of minutes",
			"broadcast message <message>        Broadcast <message> to all users",
			"broadcast user <user> <user>       Broadcast <message> to list of users",
			"... <user> message <message>",
			"message <user> <message>           Private <message> to a <user>",
			"logout                             Log out this user",
			"help                               Display this message",
			"------------------------------------------------------------------\n"
			]
		return "\n".join(msg)

	def wholast(self, username, time_ago):
		response = ""
		for name, user in self.logged_in.items():
			if time_ago > 0 and user.last_login:
				if name != username and user.last_login > (time.time() - time_ago * 60):
					response += "{}\n".format(name)
		return response

	def whoelse(self, username):
		response = ""
		for name, user in self.logged_in.items():
			if name != username and user.logged_in:
				response += "{}\n".format(name)
		return response

	def broadcast_all(self, frm, message):
		with self.lock:
			for to, user in self.logged_in.items():
				if to != frm:
					msg = "{}: {}".format(frm, message)
					try:
						self.message_queue[to].append(msg)
					except KeyError:
						self.message_queue[to] = [msg]
		return None

	def broadcast_users(self, frm, users, message):
		with self.lock:
			for to, user in self.logged_in.items():
				if to != frm and to in users:
					msg = "{}: {}".format(frm, message)
					try:
						self.message_queue[to].append(msg)
					except KeyError:
						self.message_queue[to] = [msg]
		return None

	def message_user(self, frm, to, message):
		return self.broadcast_users(frm, [to], message)

	########################################
	# command parser
	########################################

	def parse_command(self, user, data):
		response 		= ""		

		# [command, minutes]
		wholast 		= '^\s*(wholast)\s+([0-9]{1,3})\s*$'
		# [command, message]
		broadcast_all 	= '^\s*(broadcast\s+message)\s+(.*)$'
		# [command, [users], command, message]
		broadcast_users = '^\s*(broadcast\s+user)\s+(.*)\s(message)\s+(.*)$' 
		# [command, user, message]
		message_user	= '^\s*(message)\s+(\S+)(.*)$'

		m = None	
		if data == "help":
			return self.help()
		if data == "whoelse":
			return self.whoelse(user)

		m = re.match(wholast, data)
		if m:
			return self.wholast(user, int(m.group(2)))

		m = re.match(broadcast_all, data)
		if m:
			return self.broadcast_all(user, m.group(2))

		m = re.match(broadcast_users, data)
		if m:
			return self.broadcast_users(user, m.group(2).split(), m.group(4))

		m = re.match(message_user, data)
		if m:
			return self.message_user(user, m.group(2), m.group(3))

		return "Your command is not recognized; type 'help' for help\n"

	########################################
	# returns messages for the passed in user
	########################################

	@classmethod
	def messages_for(cls, user):
		messages = ""
		with cls.lock:
			try:
				messages = cls.message_queue[user]
				if messages:
					cls.message_queue[user] = []
					return "\n".join(messages) + "\n"
			except KeyError:
				pass
		return None

	########################################
	# HandlerRequest methods overridden here
	########################################

	def setup(self):
		self.request.settimeout(TIME_OUT)

	def handle(self):
		user = None

		while ThreadedTCPServer.running:
			prompt = "Command: "
			thread = None
			if user:
				# self.request.sendall(prompt)

				try:
					data = self.request.recv(BUFFSIZE)
					if not data: 
						print "Just logged out", user
						user = self.log_out(user)
						break

					data = data.strip()

					if data == "logout":
						user = self.log_out(user)
						
					response = None
					if data and data != 'logout':
						response = self.parse_command(user, data)

					if response:
						self.request.sendall(response + "\n" + prompt)
					else:
						self.request.sendall(prompt)
	
				except socket.timeout:
					self.request.sendall("Your connection has timed out\n")
					user = self.log_out(user)

			else:
				try:
					user = self.authenticate()
					if user: 
						self.request.sendall(prompt)
					else:
						self.request.sendall("\nThere was a problem logging you in\n")
						break
				except (IOError, socket.timeout):
					break


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

def await_user_messages():
	while ThreadedTCPServer.running:

		time.sleep(0.5)
		for name, user in ThreadedTCPRequestHandler.logged_in.items():
			messages = ThreadedTCPRequestHandler.messages_for(name)

			if messages: 
				messages = '\n' + messages + 'Command: '
				user.socket.sendall(messages)

########################################
# TCPServer, inlcude ThreadingMixIn
########################################
		
class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):

	running = True 
	credentials = {}

	def import_credentials(self):
		for line in open('./user_pass.txt'):
			user, pw = line.split(" ")
			self.credentials[user] = pw.strip()


if __name__ == '__main__':
	main(sys.argv)