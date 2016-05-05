import socket
import time
import sys
import os
sys.path.append("/sw/lib/python2.6/site-packages/")
import os.path


path = '/home/caroline/Desktop/test/'
OTCP_IP='127.0.0.1'
ODATA_TCP_PORT=7953
OCTRL_TCP_PORT=7961

def files_to_send(repetition, num_channels, num_slices):
	to_send = []
	for r in range(1, repetition+1):
		for e in range(1,num_channels+1):
			for s in range(1,num_slices+1):
				#'$TYP-R0001-E1-S004.imgdat'
				f_name = path+'$TYP-R%s-E%s-S%s.imgdat'%(str(r).zfill(4),e,str(s).zfill(3))
				to_send.append(f_name)
	return to_send

def send_data(aquisition_type, tr, num_slices, num_channels, repetition, delay):

	print "about to open comm with AFNI"
	# open the output ports to send data to AFNI
	# first is the control channel
	try:
		ocs=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	except Exception, e:
		print 'New socket failed! %s'%(e)
		sys.exit(1)

	try:
		ocs.connect((OTCP_IP,OCTRL_TCP_PORT))
	except Exception, e:
		print 'Connect %s (%d) failed! %s'%(OTCP_IP,OCTRL_TCP_PORT,e)
		ocs.close()
		sys.exit(1)

	print 'sending tcp:%s:%d\x00\n'%(OTCP_IP,ODATA_TCP_PORT)

	# send connection string to AFNI
	try:
		ocs.send('tcp:%s:%d\x00'%(OTCP_IP,ODATA_TCP_PORT))
	except Exception, e:
		print 'send to %s (%d) failed! %s'%(OTCP_IP,OCTRL_TCP_PORT,e)
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
			ods.connect((OTCP_IP,ODATA_TCP_PORT))
			ocf=True
		except Exception, e:
			print 'Connect to (%s, %d) failed! %s'%(OTCP_IP,ODATA_TCP_PORT,e)
			ocf=False
			ocf_count=ocf_count+1
			if( ocf_count > 20 ):
				print "Connection failed",ocf_count,"times"
				ods.close()
				sys.exit(1)

	print "Connection (",OTCP_IP,",",ODATA_TCP_PORT,") to AFNI established"
	# open the input ports to receive data from rtfeedme/scanner

	AFNI_cmd_string="ACQUISITION_TYPE 2D+zt\n"
	AFNI_cmd_string+="TR %f\n"%(tr)
	AFNI_cmd_string+="XYFOV %d %d %f\n"%(220,220,144)
	AFNI_cmd_string+="ZNUM %d\n"%(num_slices)
	AFNI_cmd_string+="XYZAXES A-P R-L I-S\n"
	AFNI_cmd_string+="DATUM %s\n"%("short")
	AFNI_cmd_string+="XYMATRIX %d %d\n"%(64,64)
	AFNI_cmd_string+="NUM_CHAN %d\n"%(num_channels)
	AFNI_cmd_string+='\0'
	print "command string",AFNI_cmd_string
	ods.send(AFNI_cmd_string) 

	to_send = files_to_send(repetition, num_channels, num_slices)
	for f in to_send:
		print 'try to send', f
		while True:
			if os.path.isfile(f):
				with open(f) as data:
					data = data.read()
					ods.send(data)
					print 'sent',f
					break
			else:
				time.sleep(delay)
	ods.close()

def parse_params(args):
	if len(args) != 6:
		print 'Usage:'
		print '    python test_img.py aquisition_type, tr, num_slices, num_channels, repetition, delay'
		print 'aquisition_type: 2D+z, 2D+zt, 3D, 3D+t'
		print 'tr: int'
		print 'num_slices: int'
		print 'num_channels: int'
		print 'repetition: int'
		print 'delay: float'
		print 'example:'
		print '    python test_img.py 2D+zt 2 48 4 20 0.125'
		sys.exit()

	else:
		if args[0] not in ['2D+z', '2D+zt','3D', '3D+t']:
			print 'aquisition type must be one of the following:'
			print '2D+z, 2D+zt, 3D, 3D+t'
			sys.exit()

		try:
			x = float(args[1])
		except Exception, e:
			print 'tr must be int or float'
			sys.exit()
		if not args[2].isdigit():
			print 'num_slices must be integer'
			sys.exit()
		if not args[3].isdigit():
			print 'num_channels must be integer'
			sys.exit()
		if not args[4].isdigit():
			print 'repetition must be integer'
			sys.exit()
		try:
			x = float(args[5])
		except Exception, e:
			print 'delay must be float'
			sys.exit()

		return args[0], float(args[1]), int(args[2]), int(args[3]), int(args[4]), float(args[5])

if __name__ == "__main__":
	a_type, tr, num_slices, num_channels, repetition, delay = parse_params(sys.argv[1:])
	send_data(a_type, tr, num_slices, num_channels, repetition, delay)
