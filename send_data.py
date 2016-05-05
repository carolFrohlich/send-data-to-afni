import socket
import time
import sys
import os
sys.path.append("/sw/lib/python2.6/site-packages/")
import os.path
import glob
import shutil
import json

path = '/home/caroline/Desktop/test/'
control_port = 7961
data_port = 7953
ip = "127.0.0.1"


def files_to_send(repetition, num_channels, num_slices):
	to_send = []
	for r in range(1, repetition+1):
		for e in range(1,num_channels+1):
			for s in range(1,num_slices+1):
				#'$TYP-R0001-E1-S004.imgdat'
				f_name = path+'$TYP-R%s-E%s-S%s.imgdat'%(str(r).zfill(4),e,str(s).zfill(3))
				to_send.append(f_name)
	return to_send

#aquisition_type, tr, num_slices, num_channels, repetition, delay
def send_data(config_file):
	#load config file
	config = json.load(open(config_file))

	print "about to open comm with AFNI"
	# open the output ports to send data to AFNI
	# first is the control channel
	try:
		ocs=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	except Exception, e:
		print 'New socket failed! %s'%(e)
		sys.exit(1)

	try:
		ocs.connect((ip, control_port))
	except Exception, e:
		print 'Connect %s (%d) failed! %s'%(ip, control_port,e)
		ocs.close()
		sys.exit(1)

	print 'sending tcp:%s:%d\x00\n'%(ip, data_port)

	# send connection string to AFNI
	try:
		ocs.send('tcp:%s:%d\x00'%(ip, data_port))
	except Exception, e:
		print 'send to %s (%d) failed! %s'%(ip, data_port,e)
		ocs.close()
		sys.exit(1)
	ocs.close()

	# next is the data channel
	try:
		ods=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	except Exception, e:
		print 'New socket failed! %s'%(e)
		ods.close()
		sys.exit(1)

	# for some reason have to wait before connection
	time.sleep(1)

	# we put the connection in a loop to make sure it happens
	ocf=False
	ocf_count=0
	while ocf==False:
		try:
			ods.connect((ip, data_port))
			ocf=True
		except Exception, e:
			print 'Connect to (%s, %d) failed! %s'%(ip, data_port,e)
			ocf=False
			ocf_count=ocf_count+1
			if( ocf_count > 20 ):
				print "Connection failed",ocf_count,"times"
				ods.close()
				sys.exit(1)

	print "Connection (",ip,",",data_port,") to AFNI established"
	# open the input ports to receive data from rtfeedme/scanner

	fov = config["xyfov"]
	xym = config["xy_matrix"]

	AFNI_cmd_string="ACQUISITION_TYPE %s\n"%(config["aquisition_type"])
	AFNI_cmd_string+="TR %f\n"%(config["TR"])
	AFNI_cmd_string+="XYFOV %d %d %f\n"%(fov[0], fov[1], fov[2])
	AFNI_cmd_string+="ZNUM %d\n"%(config["num_slices"])
	AFNI_cmd_string+="XYZAXES %s\n"%(config["xyz_axes"])
	AFNI_cmd_string+="DATUM %s\n"%(config["datum"])
	AFNI_cmd_string+="XYMATRIX %d %d\n"%(xym[0],xym[1])
	AFNI_cmd_string+="NUM_CHAN %d\n"%(config["num_channels"])
	AFNI_cmd_string+="ZORDER %s\n"%(config["slice_order"])
	AFNI_cmd_string+='\0'
	print "command string",AFNI_cmd_string
	ods.send(AFNI_cmd_string) 

	run = 1
	while True:
		print "starting to send new dataset"
		send_dataset(ods, config)

		#put all files somewhere
		os.mkdir(path+"run"+str(run))
		for o in glob.glob(path+"*.imgdat"):
			shutil.move(o, path+"run"+str(run))
		run+=1
	

def send_dataset(ods, config):
	to_send = files_to_send(config["repetition"], config["num_channels"], config["num_slices"])
	#wait for the first file to be ready
	while True:
		f = to_send[0]
		print 'try to send first file', f
		if os.path.isfile(f):
			with open(f) as data:
				data = data.read()
				ods.send(data)
				print 'sent',f
				break

	#try to send remaining files until finish
	wait_next_dataset = config["TR"]*2

	for f in to_send[1:]:
		#print 'try to send', f
		start = time.time()
		while True:
			if os.path.isfile(f):
				with open(f) as data:
					data = data.read()
					ods.send(data)
					#print 'sent',f
					break
			else:
				time.sleep(config["delay"])
				#if it takes more than 2 TRs to send next file
				#this dataset finished and we can wait for the next one
				wait = time.time() - start
				if wait >= wait_next_dataset:
					print "finish dataset"
					return
					#TODO: tell afni this dataset finished
	#ods.close()


if __name__ == "__main__":
	send_data("config.json")
