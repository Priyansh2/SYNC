import sys
import os
import hashlib
import socket
import time
import re
import glob
import subprocess
import select
import random
import tqdm
import stat
import humanize
from datetime import datetime
from os import name as nm



PORT = 1445
HOST = 'localhost'
BUFFER_SIZE = 1024
UDP_BUFFER_SIZE = 32678
HASH_BUFFER_SIZE = 4096
class server():
	def __init__(self):
		try:
			self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			self.serversocket.bind((HOST, PORT))
			self.serversocket.listen(5)
		except socket.error as e:
			print("Error: Connection `!!")

	def get_hash(self,f):
		hash_function = hashlib.md5()
		with open(f, "rb") as file:
			for chunk in iter(lambda: file.read(HASH_BUFFER_SIZE), b""):
				hash_function.update(chunk)
		return hash_function.hexdigest()

	def get_file_info(self,file_list):
		# Declare a resultant string to store final output of all the files that were modified in this time interval
		result_string = []
		# Extracting required information: filename, filesize, last modified time string, type of file using awk
		for f in file_list:
			if f == '':
				break

			bash_command = subprocess.check_output(['ls -l '+f+' | awk \'{print  $9, $5, $6, $7, $8}\' '], shell=True).decode("utf-8")
			'''
			Eg outputs:
				1.	b'./main.py 1720 Jul 17 04:15\n'
				2.	b'./b.txt 13 Jul 17 04:15\n'
				3.	b'./a.txt 0 Jul 17 04:15\n'
			'''

			# removing the trailing newline character
			if decoded_bash_command[-1] == '\n':
				decoded_bash_command = decoded_bash_command[:-1]
			split_command = re.split(" ", decoded_bash_command)
			#Note: uncomment below code block for getting only filenames
			'''temp_command = split_command[0].split("/")
			split_command[0] = temp_command[-1]'''

			result_string+=split_command[:2]
			result_string.append(" ".join(str(x) for x in split_command[2:]))

			#file types
			p = subprocess.Popen('file '+f, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			res, errors = p.communicate()
			'''
			eg output:
				1. b'./main.py: Python script, ASCII text executable\n'
				2.	b'./b.txt: ASCII text, with no line terminators\n'
				3.	b'./a.txt: empty \n'

				File types:
				1. Python script, ASCII text executable
				2. ASCII text, with no line terminators
				3. empty (for empty file)
			'''

			file_type = res.decode().split()[1:]
			file_type = " ".join(str(x) for x in file_type)
			result_string.append(file_type)
			result_string.append("\n")
		return result_string

	def get_metadata(self,f):
		data = []
		# Attach last modified timestamp
		modtime = os.path.getmtime(f) ##last modified time in seconds
		'''
			TIME FORMAT:
			%m -> month
			%d -> day
			%Y -> year
			%I -> hours in 12-hour clock
			%M -> minutes
			%S -> seconds
			%p -> AM/PM
		'''
		data.append(time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(modtime))) ## get time in pretty output.
		data.append(self.get_hash(f))
		return data


	def run(self):
		while True:
			try:
				# Connect with the client
				client, addr = self.serversocket.accept()
				print("Connected with {} :  {}".format(addr[0], str(addr[1])))

				# Receive the command from the client
				rec_command = client.recv(BUFFER_SIZE).decode()
				print("Received: Command Line ==> {}".format(rec_command))
				rec_command = rec_command.split(" ")
				pwd = os.getcwd() #store current working directory
				os.chdir(pwd)

				if (rec_command[0]=="ls"):
					output = subprocess.check_output(["ls"])
					client.send(output)

				elif (rec_command[0] == "lls"):
					'''eg:
					-rwxrwxrwx 1 root root    0 Jul 17 04:12 a.txt
					-rwxrwxrwx 1 root root   13 Jul 17 04:12 b.txt
					-rwxrwxrwx 1 root root 1750 Jul 17 04:12 main.py'''

					output = subprocess.check_output(["ls", "-l"])
					#print(output.decode("utf-8"))
					client.send(output)


				elif (rec_command[0] == "index"):

					# index shorlist <starttimestamp> <endtimestamp>
					if (rec_command[1] == "shortlist"):
						starttime = rec_command[2]+' '+rec_command[3]
						endtime = rec_command[4]+' '+rec_command[5]
						# eg: find . -type f -newermt "2017-11-06 17:30:00" ! -newermt "2017-11-06 22:00:00" (search all files (not directories) which are modified after startime and exclude all files which are modified after endtime ==> files that are modified between start(inclusive) and endtime(exclusive))

						output = subprocess.check_output(('find', pwd, '-type', 'f', '-newermt', starttime, '!', '-newermt', endtime)).decode("utf-8")
						output = output.split("\n") # eg output: ['./main.py', './b.txt', './a.txt', '']

						if len(output) == 1:
							client.send(output[0].encode())
							client.close()
							return
						result_string = self.get_file_info(output)
						result_string = " ".join(str(x) for x in result_string)
						client.send(result_string.encode("utf-8"))

					# index longlist
					elif (rec_command[1] == "longlist"):
						result_string = []
						output = subprocess.check_output(('find', pwd, '-type', 'f')).decode("utf-8")# recursively finds all files
						output = output.split('\n')
						if len(output) == 1 && output[0].strip()=="":
							client.send(output[0].encode())
							client.close()
							return
						result_string = self.get_file_info(output)
						result_string = " ".join(str(x) for x in result_string)
						client.send(result_string.encode('utf-8'))


					# index regex patten
					elif (rec_command[1] == "regex"):
						matched_files = glob.glob(rec_command[2], recursive=True)  # see gfg and official python doc for more information
						if len(matched_files) == 1 && matched_files[0].strip()=="":
							client.send(" ".encode())
							client.close()
							return
						result_string = self.get_file_info(matched_files)
						result_string = " ".join(str(x) for x in result_string)
						client.send(result_string.encode())

				elif (rec_command[0] == "hash"):

					# hash verify <filename>
					if (rec_command[1] == "verify"):
						if (not os.path.isfile(rec_command[2])):
							client.send("WRONG".encode())
							continue

						data = self.get_metadata(rec_command[2])
						data = " ".join(str(x) for x in data)
						# Send the list in the form of a string to the client, ENCODED!!!
						client.send(data.encode())

					# hash checkall
					elif (rec_command[1] == "checkall"):
						# file_list = os.listdir(".")
						# Execute command to find all the files ONLY! Otherwise upper command yielded directories, and an error persisted.
						file_list = subprocess.check_output(('find', pwd,  '-type', 'f')).decode("utf-8")
						file_list = file_list.split('\n')
						del file_list[-1] ##delete the last newline character
						list = []
						for f in file_list:
							#only_filename = f.split("/")
							#list.append(only_filename[-1])
							list.append(f)
							list.append(get_metadata(f))
							list.append("\n")
						list = " ".join(str(x) for x in list)
						client.send(list.encode())

				elif (rec_command[0] == "download"):

					if (not os.path.isfile(rec_command[2])):
						client.send("WRONG".encode())
						continue

					filesize = os.path.getsize(rec_command[2])
					client.send(str(filesize).encode())
					progress = tqdm.tqdm(range(filesize), f"Sending {rec_command[2]}", unit="B", unit_scale=True, unit_divisor=BUFFER_SIZE)

					if (rec_command[1] == "TCP"):
						f_list = []
						filename = rec_command[2]
						with open(filename,"rb") as f:
							while True:
								data= f.read(BUFFER_SIZE)
								if not data:
									break
								client.send(data)
								progress.update(len(data))


					elif (rec_command[1] == "UDP"):
						udp_client_port = rec_command[4]
						udp_client_host = rec_command[3]
						server_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
						f_list = []
						filename = rec_command[2]

						with open(filename,"rb") as f:
							while True:
								data= f.read(UDP_BUFFER_SIZE)
								if not data:
									break
								server_udp_socket.sendto(l,(udp_client_host,udp_client_port))
								progress.update(len(data))

				elif (rec_command[0] == "downloaddata"):
					f_list = []
					f_list.append(rec_command[2]) #filename
					f_list = self.get_metadata(rec_command[2])
					f_list = " ".join(str(x) for x in f_list)
					client.send(f_list.encode())


				elif (rec_command[0] == "modified"):
					filename = rec_command[1]
					last_modified_time = str(os.path.getmtime(filename))
					client.send(last_modified_time.encode())


				elif (rec_command[0] == "filepermission"):
					filename = rec_command[1]
					permission_str = str(os.lstat(filename).st_mode)
					client.send(permission_str.encode())
				client.close()


			except socket.error as e:
				print("Error: Connection refused!!")

if __name__=="__main__":
	Server = server()
	Server.run()
	Server.serversocket.close()