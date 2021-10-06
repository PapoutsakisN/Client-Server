import sys
import socket
import re
import subprocess
from subprocess import check_output
import thread
import threading
import requests
import shutil
import time
import facebook

RECV_BUFFER_SIZE = 1024 
global DataNodelist#contains all the data that are returned from the relay nodes
DataNodelist=['0 0 0']#its a dummy content cause the zero position is reserved for the direct connection
global DataClientlist#contains all the data gathered from the tests between client and relay nodes
DataClientlist=[]
global server_error
server_error=0
jump_flag=False
global finaltime

if __name__ == "__main__":
    try:
        arg1=sys.argv[1]
	arg2=sys.argv[2]
    except IndexError:
        print "Usage: myprogram.py <servers Text> <Relay Text>"
        sys.exit(1)


filename1=sys.argv[1]
filename2=sys.argv[2]
global pingnumb#the number you give to ping the server
endserver=raw_input('>End Server you want to connect: ').strip(' ')

found=False;
serverfile=open(filename1,"r")
for line in serverfile:#searches the server file we gave at command line and searches with the alias the URL
	if endserver in line: 
		found=True;
		break;
if found==False: 
	serverfile.close()
	sys.exit('Sorry,server not existent')

urllist=re.sub("[^\w]", " ",  line).split()#merges only the wanted pieces of the line
if len(urllist)is 4: URL=urllist[0]+'.'+urllist[1]+'.'+urllist[2]#www.japan.go.jp
else : URL=urllist[0]+'.'+urllist[1]+'.'+urllist[2]+'.'+urllist[3]#www.google.com

print "The server you asked: %s"%URL

threadLock = threading.Lock()
def send_message(ip_adrress,socketNO,cmd_message): 
#function that sends a message to given ip via the socketNO socket and receives back a message
	try:	
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		relay_adress=(ip_adrress,socketNO)
		sock.connect(relay_adress)
		sock.sendall(cmd_message)
		data=sock.recv(RECV_BUFFER_SIZE)
		tmp2list=data.split(' ')#receives the data 
		threadLock.acquire()#and uses lock to write to the datanodelist and inserts the data in the index that the id of the relay node is matched
		DataNodelist.insert(int(tmp2list[2]),data)#for example relay with id 2 will go to the index 2
		threadLock.release()#the zero index is reserved for direct 
		sock.close()
	except:
		server_error=1
		
	
def pingNtraceroute(destination,pingNumb,ident):
	#this function traceroutes and pings a given adrress
	cmdping = "ping -c"+str(pingNumb)+" "+destination+" | tail -1| awk '{print $4}' | cut -d '/' -f 2"
	data1=subprocess.check_output(cmdping,shell=True).strip('\n')#calls the linux ping command and only keeps the average rtt
	
	cmdhops = "traceroute "+destination+">Trace"+str(ident)+".txt"#calls the traceroute linux command and writes the result to a file
	subprocess.check_output(cmdhops,shell=True)
	tracefile=open('Trace'+str(ident)+'.txt',"r")#the name of the file is produced by Trace plus the identity of the relaynode
	counter=0#opens the file and counts the hops
	linecounter=0#whenever finds *** it means that the server doesnt respond and if at the 31 line of the file find stars means that the server doesnt respond so
	for line in tracefile:
		linecounter=linecounter+1#prints a problem message
		if '* * *' in line:
			if linecounter is 31:
				server_error=1
				#print "Problem server not responding to Traceroute"#close the sockets or something to prevent the crash
			continue
		counter=counter+1
	data2=str(counter-1)
	cmdrm = "rm Trace"+str(ident)+".txt" #deletes the file aw they are not any more useful
	subprocess.check_output(cmdrm,shell=True)
	threadLock.acquire() #uses thread lock and writes the data to client list depending the id of the relay node and 0 position is reserved for the direct connection
	DataClientlist.insert(ident,data2+' '+data1+' '+str(ident))
	threadLock.release()

def searchFunc(SList):#takes a list as a parameter and starting with the first node which in both lists that is used 
	search=SList[0]#contains the direct connection and searches the smallest number in between nodes and returns at the end the index with the smallest number
	index=0
	for i in range(len(SList)):
		if search>SList[i]:#so we know whick node or if the direct connection is faster
			search=SList[i]
			index=i
	return index

pingnumb=raw_input('>Give the ping number: ').strip(' ')
while True:#input check
	try:
		if int(pingnumb)<=0:
			pingnumb=raw_input('>Ping number must be greater than zero\n').strip(' ')
		else:
			break
	except:
		pingnumb=raw_input('>Must be number input Sorry\n').strip(' ')

nodeInfo=[]
nodeInfo.append('0')#puts two dummy zero data representing the direct connection
nodeInfo.append('0')
relayfile=open(filename2,"r")
relayNO=0#opens the file and takes the information about the relaynodes
for rline in relayfile:
	tmplist=rline.split(',')
	nodeInfo.append(tmplist[1])
	nodeInfo.append(tmplist[2].strip('\n'))
	relayNO=relayNO+1
relayfile.close()

print "####Relay Node Information####"

i=2#prints the information
while i<int(relayNO)*2+1:
	print "ID: "+str(i/2)
	print "RelayNode IP: "+nodeInfo[i]
	print "RelayNode Socket: "+nodeInfo[i+1]+"\n"
	i=i+2
raw_input('Continue...')
print "Sending Ping and Traceroute Directly to server and to relay nodes...."

threads=[]
x=2#opens for each node 2 threads and executes the send message and pingNtrace
#and for the direct connection opens one thread and executes only the pingntrace
for i in range(int(relayNO)):
   	t=threading.Thread(target=send_message, args=(nodeInfo[x],int(nodeInfo[x+1]),pingnumb+' '+URL+' '+str(i+1)) )
	t2=threading.Thread(target=pingNtraceroute, args=(nodeInfo[x],pingnumb,i+1))
	t.setDaemon(True)
	t2.setDaemon(True)
	threads.append(t)
	threads.append(t2)
	t.start()
	t2.start()
	x=x+2

directPnT=threading.Thread(target=pingNtraceroute, args=(URL,pingnumb,0))
directPnT.setDaemon(True)
threads.append(directPnT)
directPnT.start()
for j in range(int(relayNO)*2+1):
	threads[j].join();

UnitedDataListP=[]#holds all the ping data sorted by id and in zero index is located the direct connection
UnitedDataListT=[]# the same about traceroute data

incr=0
try:
	for incr in range(int(relayNO)+1):#unify the data from client and relay in 2 lists
		tmp2list=DataClientlist[incr].split(' ')
		tmp3list=DataNodelist[incr].split(' ')
		UnitedDataListP.insert(incr,float(tmp2list[1])+float(tmp3list[1]))
		UnitedDataListT.insert(incr,int(tmp2list[0])+int(tmp3list[0]))
	if(int(tmp3list[0])==0):
		server_error=1
except:
	print ">>>Server not responding to the tests"
	jump_flag=True


def printPing():
	
	print "==========================="
	print "The RTT"
	i=1;
	print "DirectMode->"+str(UnitedDataListP[0])
	while i<relayNO+1:
		print "RelayNode:"+str(i)+"->"+str(UnitedDataListP[i])
		i=i+1

	print "==========================="

def printRTT():
	print "==========================="
	print "The Traceroute"
	i=1;
	print "DirectMode->"+str(UnitedDataListT[0])
	while i<relayNO+1:
		print "RelayNode:"+str(i)+"->"+str(UnitedDataListT[i])
		i=i+1
	print "==========================="

pathing=0#ask the criterion we want to use
if jump_flag==False:
	if server_error==1:
		print "Cause of server not responding in TraceRoute the testing will be carried with ping"
		pathing=searchFunc(UnitedDataListP)
		if pathing==0:#we inform the user which path is faster
			print "The fastest way is the direct"
		else:
			print "The Node %d was choosen"%pathing
		printPing()
		raw_input('.....Waiting.....')
	else:
		printPing()
		printRTT()
		test_criterion=raw_input('>Give criterion for connection latency or traceroute[l/t]: ')
		while True:
			if test_criterion not in ('l','t','L','T'):
				test_criterion=raw_input('>Wrong test criterion press t or l for traceroute or latency ').strip(' ')
			else:#if the ping is selected we call search function with the ping list else with the traceroute list
				if test_criterion in('l','L'):
					pathing=searchFunc(UnitedDataListP)
					if pathing==0:#we inform the user which path is faster
						print "The fastest way is the direct"
					else:
						print "The Node %d was choosen"%pathing
				else:
					pathing=searchFunc(UnitedDataListT)
					if pathing==0:
						print "The fastest way is the direct"
					else:
						print "The %d node was choosen"%pathing
				break

		
	

def final_request(pathing,incr,addr):#the finalo request if one of the nodes is choosen 
	req_socket=socket.socket()#requests the file from this node
	host=nodeInfo[incr]#else closes the relay node
	port=int(nodeInfo[incr+1])
	req_socket.connect((host,port))
	if pathing*2==incr:
		start=time.time()
		req_socket.sendall(addr)
		
		print "Downloading..."
		with open('fileViaNode','wb') as f:
			while True:#receives the file and closes the socket
				data=req_socket.recv(1024)
				if not data:
					break
				f.write(data)
		f.close()
		req_socket.close()
		end=time.time()
		print "Your file was succesfully downloaded"
		finaltime=end-start
		print "Time: "+str(round(finaltime,4))
		return
	req_socket.sendall('0')
	req_socket.close()


downloadfile=open('files2download',"r")
for line in downloadfile:
	if endserver in line:
		down_url=line#opens the file with urls of the files in each site we want to download
		break#and matches it with the server we have asked
	elif URL in line:
		down_url=line#opens the file with urls of the files in each site we want to download
		break#and matches it with the server we have asked
downloadfile.close()

if pathing==0:#if the path that we found that is faster is the direct the dowload of the file is done from here	
	print "The request of the file is done directly with the server"
	print "Downloading..."
	
	start=time.time()
	try:
		response = requests.get(down_url.strip('\n'), stream=True)
		if response.status_code == 200:
			with open('received_file', 'wb') as out_file:
				shutil.copyfileobj(response.raw, out_file)
			del response
			end=time.time()
			print "Your file was succesfully downloaded"
			finaltime=end-start
			print "Time: "+str(round(finaltime,4))
	except:
		i=2#care for the direct mode
		while i<int(relayNO)*2+2:
			final_request(pathing,i,down_url.strip('\n'))
			i=i+2
		sys.exit('Unknown error Couldnt download ur requested file')
i=2#care for the direct mode
bonus=False
while i<int(relayNO)*2+2:
	final_request(pathing,i,down_url.strip('\n'))
	i=i+2
facebook_post=raw_input('>Do you want to post it to fb [y/n]?')
while True:
			if facebook_post not in ('y','n'):
				facebook_post=raw_input('>Type y or n ').strip(' ')
			else:
				if facebook_post in('y'):
					bonus=True
				else:
					bonus=False
				break

if bonus:

	def get_api(cfg):
		graph = facebook.GraphAPI(cfg['access_token'], version='2.2')
		return graph

	cfg = {
	    "page_id"      : "10203475715598464",
	    "access_token" : "EAACEdEose0cBAJZAxNtjUyLezB43CKDAooANBAXRLFOZA2odwkpE2pjTZAUynA7X07SdCWzb7hCoGyRgC7xNWWpQyc7nwWFa08z8coRk33QwzfCAXcbv4RKnwZBDIVzYZCuJKPkUPahJGRXw7wt9wDIjAEr1HL6ZAw9qeXIwQ4OCzdqRYCc3jEZBj5gY7kz8ZC4ZD"
	    }

	api = get_api(cfg)
	if pathing==0:
		api.put_photo(image=open("received_file",'rb').read(), message='Downloaded and Posted With Python Script for HY335')
	else:
		api.put_photo(image=open("fileViaNode",'rb').read(), message='Downloaded and Posted With Python Script for HY335')


