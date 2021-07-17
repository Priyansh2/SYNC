import sys
import os
import hashlib
import socket
import time
import re
import glob
import subprocess
import select
import cmd
import rlcompleter
import atexit
import random
import shlex
import tqdm
import stat
import humanize
from datetime import datetime
from os import name as nm

if nm == 'nt':
	from pyreadline import Readline
	readline = Readline()
else:
	import readline

readline.parse_and_bind('tab: complete') # tab completion
histfile = os.path.join(os.path.dirname(os.path.realpath(__file__)), '.pythonhistory') # history file


try:
	readline.read_history_file(histfile)
except IOError:
	print("ok!!")
	pass

atexit.register(readline.write_history_file, histfile)
del histfile, readline, rlcompleter


HOST = 'localhost' #TCP
PORT = 1445 #TCP
UDP_HOST = 'localhost'
UDP_PORT = 1403

BUFFER_SIZE = 1024
UDP_BUFFER_SIZE = 32678
HASH_BUFFER_SIZE = 4096
class client:
	def __init__(self):
		self.init_time = datetime.now()

	def download(self, input_command, file_str):
		if (input_command[1] == "TCP"):
			# Create a new client socket for connections with the server.
			try:
				cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				cli_socket.connect((HOST, PORT))
			except socket.error as e:
				print("Error: Connection refused!!")

			input_temp_command = " ".join(str(x) for x in input_command)
			cli_socket.send(input_temp_command.encode('utf-8'))
			data = cli_socket.recv(BUFFER_SIZE).decode()

			if (data== 'WRONG'):
				print("TCP: File do not exist!!. Enter the correct file name/path")
				return

			filesize = int(data)

			progress = tqdm.tqdm(range(filesize), f"Receiving {input_command[2]}", unit="B", unit_scale=True, unit_divisor=BUFFER_SIZE)

			# Open a file_str and receive all the data in that file
			with open(file_str, 'wb') as f:
				while True:
					data = cli_socket.recv(BUFFER_SIZE)
					if not data:
						break
					f.write(data)
					progress.update(len(data))

			# Set file permissions. BONUS!
			filep = self.get_file_permission(["filepermission", input_command[2]])
			filep = int(filep)
			try:
				os.chmod(file_str, int_filep)
				print("Set file permissions of {} to {}".format(file_str, oct(filep)))
				# oct output eg: 0o100644 ==> Here  last 3 octal digit i.e, 644 represents the file permission mask and upper parts i.e, 0o100 tells the file type so to get the file's permission we can extract last 3 octal digit -> oct(int_filep)[-3:]
			except:
				print("TCP: Insufficient read permissions. Unable to access file {}".format(input_command[2]))


			print('TCP: Download successfull!!')
			cli_socket.close()


			# Create a new socket function for receiving metadata : filename, filesize, timestamp, md5 hash
			try:
				cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				cli_socket.connect((HOST, PORT))
			except socket.error as e:
				print("Error: Connection refused!!")

			# download metadata: filename, filesize, timestamp, md5hash
			cmd = "downloaddata TCP "+input_command[2]
			cli_socket.send(cmd.encode())
			file_metadata = cli_socket.recv(BUFFER_SIZE).decode()
			cli_socket.close()

			file_metadata = file_metadata.split(" ")
			filesize = humanize.naturalsize(filesize)
			filename = input_command[2]
			print("The filesize and hash of the file {} is {} and {} , last modified on {} {} {}.".format(filename, filesize, file_metadata[3], file_metadata[0], file_metadata[1], file_metadata[2]))

			#print(file_metadata)


		elif (input_command[1] == "UDP"):
			file_str = "udp_"+file_str
			# create a TCP socket for sending command arguements
			try:
				cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				cli_socket.connect((HOST, PORT))
			except socket.error as e:
				print("Error: Connection refused!!")


			# Create a new UDP client socket server for connections with the original server.
			cli_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			udp_socket_info  = str(UDP_HOST)+" "+str(UDP_PORT)
			cli_udp_socket.bind((UDP_HOST, UDP_PORT))
			cli_udp_socket.settimeout(30) # Set time-out on the UDP socket.


			input_temp_command = " ".join(str(x) for x in input_command).strip() + " " + udp_socket_info
			cli_socket.send(input_temp_command.encode('utf-8'))
			data = cli_socket.recv(BUFFER_SIZE).decode()
			cli_socket.close()

			if (data== 'WRONG'):
				print("UDP: File do not exist!!. Enter the correct file name/path")
				return

			filesize = int(data)
			progress = tqdm.tqdm(range(filesize), f"Receiving {input_command[2]}", unit="B", unit_scale=True, unit_divisor=BUFFER_SIZE)


			# Open a new file file_str and receive all the data in that file
			with open(file_str, 'wb') as fudp:
				while True:
					try:
						data, addr = cli_udp_socket.recvfrom(UDP_BUFFER_SIZE)
					except socket.timeout:
						print("Error: UDP Timeout!!")
						break
					fudp.write(data)
					progress.update(len(data))
					if not data or data =="":
						break

			cli_udp_socket.close()
			print('UDP: Verifying downloaded file...')


			# Verify the calculated hash with the received file hash
			# Create a new socket function for receiving file metadata: filename, filesize, timestamp, md5 hash
			try:
				cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				cli_socket.connect((HOST, PORT))
			except socket.error as e:
				print("Error: Connection refused!!")


			cmd = "downloaddata TCP "+input_command[2]
			cli_socket.send(cmd.encode())
			file_metadata = cli_socket.recv(BUFFER_SIZE).decode()
			file_metadata = file_metadata.split(" ")
			cli_socket.close()


			file_hash = file_metadata[3]
			hash_function = hashlib.md5()
			with open(file_str, "rb") as file:
				for chunk in iter(lambda: file.read(HASH_BUFFER_SIZE), b""):
					hash_function.update(chunk)
			udp_hash = hashfunction.hexdigest()

			print("UDP: Md5 cheksum of downloaded file ==> {}".format(udp_hash))

			if(file_hash == udp_hash):
				filep = self.get_file_permission(["filepermission", input_command[2]])
				filep = int(filep)

				try:
					os.chmod(file_str, int_filep)
					print("Set file permissions of {} to {}".format(file_str, oct(filep)))
					# oct output eg: 0o100644 ==> Here  last 3 octal digit i.e, 644 represents the file permission mask and upper parts i.e, 0o100 tells the file type so to get the file's permission we can extract last 3 octal digit -> oct(int_filep)[-3:]
				except:
					print("TCP: Insufficient read permissions. Unable to access file {}".format(input_command[2]))
				print("UDP: Download successfull!!")


				filesize = humanize.naturalsize(filesize)
				filename = input_command[2]
				print("The filesize and hash of the file {} is {} and {} , last modified on {} {} {}.".format(filename, filesize, file_metadata[3], file_metadata[0], file_metadata[1], file_metadata[2]))


			else:
				print("UDP: Corrupted downloaded file")


	def hash(self, input_command):
		# Create a new client socket for connections with the server.
		try:
			cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			cli_socket.connect((HOST, PORT))
		except socket.error as e:
			print("Error: Connection refused!!")

		if (input_command[1] == "verify"):
			filename = input_command[2]
			input_command = " ".join(str(x) for x in input_command)
			cli_socket.send(input_command.encode('utf-8'))
			cli_output = cli_socket.recv(BUFFER_SIZE).decode()


			if (cli_output == 'WRONG'):
				print("hash <verify>: File do not exist!!. Enter the correct file name/path")
				return


			cli_output = cli_output.split(" ")
			print("The hash of the file {} is {} , last modified on {} {} {}.".format(filename, cli_output[3], cli_output[0], cli_output[1], cli_output[2]))
			#print(cli_output)
			cli_socket.close()

		elif (input_command[1] == "checkall"):
			input_command = " ".join(str(x) for x in input_command)
			cli_socket.send(input_command.encode('utf-8'))
			cli_output = cli_socket.recv(BUFFER_SIZE).decode()
			cli_output = cli_output.split("\n")
			print("|            Filename            | Last Modified Time |            Md5 Checksum            |\n")
			for i in cli_output:
				if i.strip() == "":
					continue
				temp = i.strip().split()
				print("|            ",temp[0],"            | ",temp[1]," |            ",temp[2],"            |")
			cli_socket.close()

	def index(self, input_command):
		# Create a new client socket for connections with the server.
		try:
			cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			cli_socket.connect((HOST, PORT))
		except socket.error as e:
			print("Error: Connection refused!!")


		input_command = " ".join(str(x) for x in input_command)
		cli_socket.send(input_command.encode('utf-8'))
		cli_output = cli_socket.recv(BUFFER_SIZE).decode()

		if (len(cli_output.split()) == 0):
			cli_socket.close()
			return


		cli_output =cli_output.split("\n")
		print("|     Filename     | FileSize |     Last Modified Time     |              FileType              |\n")
		for i in cli_output:
			if i.strip() == "":
				continue
			temp = i.strip().split()
			print("|     ",temp[0],"     | ",humanize.naturalsize(int(temp[1]))," |     ",temp[2],"     |              ",temp[3],"              |")
		cli_socket.close()


	def getlist(self, input_command):
		# Create a new client socket for connections with the server.
		try:
			cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			cli_socket.connect((HOST, PORT))
		except socket.error as e:
			print("Error: Connection refused!!")


		input_command = " ".join(str(x) for x in input_command)
		cli_socket.send(input_command.encode('utf-8'))
		cli_output = cli_socket.recv(BUFFER_SIZE).decode().split("\n")
		cli_socket.close()


		del cli_output[0] # Remove eg: total 100
		del cli_output[-1] # Remove the new line character

		return cli_output

	def get_file_permission(self, input_command):
		# Create a new client socket for connections with the server.
		try:
			cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			cli_socket.connect((HOST, PORT))
		except socket.error as e:
			print("Error: Connection refused!!")


		input_command = " ".join(str(x) for x in input_command)
		cli_socket.send(input_command.encode('utf-8'))
		filep = cli_socket.recv(BUFFER_SIZE).decode()
		cli_socket.close()

		return filep

	def get_last_modified_time(self, input_command):
		# Create a new client socket for connections with the server.
		try:
			cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			cli_socket.connect((HOST, PORT))
		except socket.error as e:
			print("Error: Connection refused!!")


		input_command = " ".join(str(x) for x in input_command)
		cli_socket.send(input_command.encode('utf-8'))
		cli_output = cli_socket.recv(BUFFER_SIZE).decode()
		cli_socket.close()

		return cli_output


	def sync(self):
		# Retrieve the files and directories names in remote folder (client shared directory)
		local_file_list = os.listdir(".")
		lls_list = self.getlist(["lls"])
		temp_list = []
		# Retrieve the files and directories names in server folder (other client's shared directory)
		server_file_list = []
		for element in lls_list:
			temp_list = element.split(" ")
			server_file_list.append(temp_list[-1])

		# Iterate over the elements and download missing files from server to remote folder
		for element in server_file_list:
			if not element or element == '' or element in local_file_list:
				break
			self.download(["download", "TCP", element], element)
			print("Successfully download file {}".format(element))

		# Iterate over the elements and download recently modified filesas per question to remote folder
		local_file_list = os.listdir(".")
		for element in server_file_list:
			if not element:
				continue

			server_hash = self.hash(["hash", "verify", element])[-1]
			# Compute the hash function for local file

			hash_function = hashlib.md5()
			with open(element, "rb") as file:
				for chunk in iter(lambda: file.read(HASH_BUFFER_SIZE), b""):
					hash_function.update(chunk)
			local_hash = hash_function.hexdigest()

			server_last_modified = int(self.get_last_modified_time(["modified", element]))
			client_last_modified = int(str(os.path.getmtime(element)))
			# compare lastmodified times of files in client_folder and server_folder
			# Any file is said to be recently modified if its lastmodified time (seconds ) is greater than its previous version
			# We will download files from server to client folder. Similarly, the other client (acting as server) will do the same thing for its server (our client acting as server)

			if (client_last_modified > server_last_modified):
				continue
			else:
				if(local_hash != server_hash):
					self.download(["download", "TCP", element], element)
					print("Successfully download file {}".format(element))

	def run(self):
		while True:
			print('Client > ', end=" ", flush=True)
			# Time-out for automatic sync. User is not allowed to perform any action until sync is completed.
			# This is to avoid file locking (read online)
			i, o, e = select.select([sys.stdin], [], [], 100)

			if (i):
				## Parse commands
				input_command = sys.stdin.readline().strip()
				input_command = input_command.split(" ")

				if (len(input_command) == 1):

					# ls command output handling
					if(input_command[0] == "ls"):
						file_list = os.listdir(".")
						for f in file_list:
							print(f)

					# lls is the long-list output (output of ls -l) from the server directory
					elif (input_command[0] == "lls"):
						lls_list = self.getlist(input_command)
						for f in lls_list:
							print(f)

					# force sync with command line
					elif (input_command[0] == "sync"):
						self.sync()

				elif (input_command[0] == "index"):
					self.index(input_command)

				elif (input_command[0] == "hash"):
					self.hash(input_command)

				elif (input_command[0] == "download"):
					file_str = 'received_file_' + str(random.randrange(1, 1000)) + input_command[2].split("/")[-1]
					while(os.path.isfile(file_str) is True):
						file_str = 'received_file_' + str(random.randrange(1, 1000)) + input_command[2].split("/")[-1]
					self.download(input_command, file_str)

				else:
					print("No such command!!")
					print("Choose one among the below commands:")
					print("""1. ls\n2. lls\n3. index <flag> [args]...\n4. hash <flag> [args]...\n5. download <flag> [args]...\n6. sync""")
			else:
				# automatic sync after every 100 seconds
				self.sync()
				if nm == "nt":
					os.system("cls")
				else:
					os.system("clear")


if __name__=="__main__":
	Client = client()
	Client.run()
