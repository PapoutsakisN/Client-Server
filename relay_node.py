import socket
import sys
import subprocess
import re
import time
import shutil
import requests

RECV_BUFFER_SIZE = 1024 
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#open a socket and ask in which port we are going to connect
socketNO=raw_input('>Give the Socket number u want to connect(0-65535) ')
server_address = ('', int(socketNO))
server_error=False#flag if the server doesnt respond 
LatencyRelay=0#holds the Latency No
print "starting up on %s port %s" % server_address
sock.bind(server_address)
sock.listen(1)#listens if the client connects


print "waiting for a connection..."
connection, client_address = sock.accept()
	
data=connection.recv(RECV_BUFFER_SIZE)
print "Connection Established\n"
print "####Connection Information####"

requestlist=data.split(' ')#prints the information about the connection and the node
print "ID Node: "+requestlist[2]
print "Server : "+requestlist[1]
print "Ping Number "+requestlist[0]
print "\nSending Ping and Traceroute to given server...."
#PING
cmdping = "ping -c"+requestlist[0]+" "+requestlist[1]+" | tail -1| awk '{print $4}' | cut -d '/' -f 2"
try:	
	LatencyRelay=float(subprocess.check_output(cmdping,shell=True).strip('\n'))
except Exception:
	print ">>>Problem with server no responding to ping test"
	server_error=True
if server_error==False:
	print "####Results####"
	print "LatencyRelay: %f"%LatencyRelay
#HOPS
cmdhops = "traceroute "+requestlist[1]+">RelayTrace"+requestlist[2]+".txt" #to requestlist[2] periexei to id tou node
subprocess.check_output(cmdhops,shell=True)

tracefile=open('RelayTrace'+requestlist[2]+'.txt',"r")
counter=0
linecounter=0
for line in tracefile:#Count the hops
	linecounter=linecounter+1
	if '* * *' in line:
		if linecounter is 31: 
			print ">>>Problem server not responding to Traceroute test"#same with client
			server_error=True
		continue
	counter=counter+1

relayHops=counter-1
if server_error:
	relayHops=0
else:
	print "Average RTT: "+str(relayHops)+"\n"

cmdrm = "rm RelayTrace"+requestlist[2]+".txt" #deletes the file we dont need
subprocess.check_output(cmdrm,shell=True)
#sends back the data
if server_error:
	print "Informing Client about the errors..."
else:	
	print "Sending Back the ping and traceroute information..."
connection.sendall(str(relayHops)+' '+str(LatencyRelay)+' '+str(requestlist[2]))

sock.listen(1)
print "Waiting for instructions..."

connection, client_address = sock.accept()#waiting for instructions 
data = connection.recv(RECV_BUFFER_SIZE)#if the client chooses this node
if data=='0':#the file ll be downloaded from here else
	print "I am not usefull anymore"
else:#it closes the connection and the node
	print "I am the choosen one"
	response = requests.get(data, stream=True)
	if response.status_code == 200:
		print "Downloading..."
		with open('file', 'wb') as out_file:
			shutil.copyfileobj(response.raw, out_file)
		del response
		f=open('file','rb')
		l=f.read(1024)
		while(l):
			connection.send(l)
			l=f.read(1024)
		f.close()
		cmdrm2 = "rm file" #deletes the file we dont need
		subprocess.check_output(cmdrm2,shell=True)
		print "The file was sent"
connection.close()
sock.close()
