#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# mmdvm_tools
# functions to parse mmdvm log

import os,re,time,configparser

class mmdvm_ini(object):
	def __init__(self,cfg):
		self.error = ''
		
		if not os.path.isfile(cfg.mmdvm_ini):
			print("[mmdvm_ini] file '%s' not found"%cfg.mmdvm_ini)
			self.found = False
			self.error = 'file not found'
			return
		
		if cfg.debug: print("[mmdvm_ini] parsing '%s'"%cfg.mmdvm_ini)
		ini = configparser.ConfigParser(strict = False)
		ini.read(cfg.mmdvm_ini)
		self.found = True
		self.filename = cfg.mmdvm_ini
		self.callsign = ini['General'].get('Callsign','')
		self.id = ini['General'].get('Id','')
		self.duplex = ini['General'].getboolean('Duplex',False)
		
		self.info_lat = ini['Info'].getfloat('Latitude',0)
		self.info_lon = ini['Info'].getfloat('Longitude',0)
		self.info_rxfreq = ini['Info'].getint('RXFrequency',0)
		self.info_txfreq = ini['Info'].getint('TXFrequency',0)
		self.info_power = ini['Info'].getint('Power',0)
		self.info_height = ini['Info'].getint('Height',0)
		self.info_loc = ini['Info'].get('Location','')
		self.info_desc = ini['Info'].get('Description','')
		self.info_url = ini['Info'].get('URL','')
		
		self.log_path = ini['Log'].get('FilePath','')
		self.log_prefix = ini['Log'].get('FileRoot','')
		
		self.dmr_id_file = ini['DMR Id Lookup'].get('File','')
		self.dmr_enable = ini['DMR'].getboolean('Enable',False)
		self.dmr_colorcode = ini['DMR'].getint('ColorCode',1)
		self.dmr_selfonly = ini['DMR'].getboolean('SelfOnly',False)
		self.dmr_net_enable = ini['DMR Network'].getboolean('Enable',False)
		self.dmr_net_address = ini['DMR Network'].get('Address','')
		self.dmr_net_port = ini['DMR Network'].get('Port','')
		self.dmr_net_slot1 = ini['DMR Network'].getboolean('Slot1',False)
		self.dmr_net_slot2 = ini['DMR Network'].getboolean('Slot2',False)
		
		self.dstar_enable = ini['D-Star'].getboolean('Enable',False)
		self.ysf_enable = ini['System Fusion'].getboolean('Enable',False)
		self.p25_enable = ini['P25'].getboolean('Enable',False)
		
		return

class dmrgateway_ini(object):
	def __init__(self,cfg):
		self.error = ''
		
		if not os.path.isfile(cfg.dmrgateway_ini):
			print("[dmrgateway_ini] file '%s' not found"%cfg.dmrgateway_ini)
			self.found = False
			self.error = 'file not found'
			return
		
		if cfg.debug: print("[dmrgateway_ini] parsing '%s'"%cfg.dmrgateway_ini)
		ini = configparser.ConfigParser(strict = False)
		ini.read(cfg.dmrgateway_ini)
		self.found = True
		self.filename = cfg.dmrgateway_ini
		
		self.info_lat = ini['Info'].getfloat('Latitude',0)
		self.info_lon = ini['Info'].getfloat('Longitude',0)
		self.info_rxfreq = ini['Info'].getint('RXFrequency',0)
		self.info_txfreq = ini['Info'].getint('TXFrequency',0)
		self.info_power = ini['Info'].getint('Power',0)
		self.info_height = ini['Info'].getint('Height',0)
		self.info_loc = ini['Info'].get('Location','')
		self.info_desc = ini['Info'].get('Description','')
		self.info_url = ini['Info'].get('URL','')
		
		self.log_path = ini['Log'].get('FilePath','')
		self.log_prefix = ini['Log'].get('FileRoot','')
		
		self.dmr_networks = [string for string in ini.sections() if 'DMR Network' in string]
		self.dmr_net_enable = {}
		self.dmr_net_name = {}
		self.dmr_net_address = {}
		self.dmr_net_port = {}
		
		for dmrnet in self.dmr_networks:
			if cfg.debug: print("[dmrgateway_ini] found '%s'"%dmrnet)
			self.dmr_net_enable[dmrnet] = ini[dmrnet].getboolean('Enabled',False)
			self.dmr_net_name[dmrnet] = ini[dmrnet].get('Name','')
			self.dmr_net_address[dmrnet] = ini[dmrnet].get('Address','')
			self.dmr_net_port[dmrnet] = ini[dmrnet].get('Port','')
		
		
		return

def MMDVMId(line):
	#Id: 123456
	if re.search("Id: ", line):
		startId = line.find("Id: ")+4
		id = line[startId:]
		return id
	else:
		return False	
	
def MMDVMCallsign(line):
	#Callsign: DB0USD
	if re.search("Callsign: ", line):
		startCall = line.find("Callsign: ")+10
		callsign = line[startCall:]
		return callsign
	else:
		return False	

def MMDVMHostState(line):
	#MMDVMHost-20170719 is starting
	#MMDVMHost-20170719 is running
	#MMDVMHost-20170719 exited
	if re.search("MMDVMHost-.* is starting", line):
		state = 'is starting'
		startVer = line.find("MMDVMHost-")+10
		endVer = line.find(state)
		version = line[startVer:endVer-1]
		return [state,version]
	elif re.search("MMDVMHost-.* is running", line):
		state = 'is running'
		startVer = line.find("MMDVMHost-")+10
		endVer = line.find(state)
		version = line[startVer:endVer-1]
		return [state,version]
	elif re.search("MMDVMHost-.* exited", line):
		state = 'exited'
		startVer = line.find("MMDVMHost-")+10
		endVer = line.find(state)
		version = line[startVer:endVer-1]
		return [state,version]
	else:
		return False
	
def MMDVMHostBuilt(line):
	#Built 11:34:43 Sep  4 2017 (GitID #5d98d9d)
	if re.search("Built ",line):
		startVer = line.find("Built ")+6
		version = line[startVer:]
		return version
	else:
		return False

def MMDVMVersion(line):
	#MMDVM protocol version: 1, description: MMDVM 20160906 TCXO
	if re.search("MMDVM protocol version: .*, description:", line):
		startVer = line.find("version: ")+9
		startBuild = line.find(", description: ")+15
		endBuild = line.find(" (")
		version = line[startVer:startBuild]
		build = line[startBuild:endBuild]
		return build
	else:
		return False

def MMDVMTime(line):
	if re.search("^.{1}: ",line):
		stamp = line[3:26]
		stamp = time.strptime(stamp,"%Y-%m-%d %H:%M:%S.%f")
		#stamp = time.gmtime(time.mktime(stamp))
		stamp = time.localtime(time.mktime(stamp))
		stamp = int(time.mktime(stamp))
		return stamp
	else:
		return False

def MMDVMModes(line):
	'''
	I: 2017-10-25 09:17:20.036     Duplex: yes
	I: 2017-10-25 09:17:20.036     Timeout: 240s
	I: 2017-10-25 09:17:20.036     D-Star: disabled
	I: 2017-10-25 09:17:20.037     DMR: enabled
	I: 2017-10-25 09:17:20.037     YSF: disabled
	I: 2017-10-25 09:17:20.037     P25: disabled'''
	if line.find("DMR: enabled") != -1:
		return ['DMR',True]
	elif line.find("YSF: enabled") != -1:
		return ['YSF',True]
	elif line.find("P25: enabled") != -1:
		return ['P25',True]
	elif line.find("D-Star: enabled") != -1:
		return ['D-Star',True]
	elif line.find("DMR: disabled") != -1:
		return ['DMR',False]
	elif line.find("YSF: disabled") != -1:
		return ['YSF',False]
	elif line.find("P25: disabled") != -1:
		return ['P25',False]
	elif line.find("D-Star: disabled") != -1:
		return ['D-Star',False]
	else:
		return False

def DMRMasterState(line):
	if re.search("(DMR, Logged into the master successfully)|(DMR, Closing DMR Network)", line):
		if line.find("successfully") != -1:
			return 'OPEN'
		elif line.find("Closing") != -1:
			return 'CLOSED'
		elif line.find("Opening") != -1:
			return 'CONN'
	else:
		return False

def DownlinkActive(line):
	#Downlink Activate received from DO1HSP
	if re.search("Downlink Activate received from",line):
		startCall = line.rfind(" ")+1
		call = line[startCall:]
		return call
	else:
		return False

def DMRVoice(line):
	#RF# DMR Slot 2, received RF voice header from DO1HSP to 5000
	#NET# DMR Slot 2, received network voice header from DO1HSP to TG 9990
	#if re.search("received RF voice header from",line):
	if re.search("received .* voice header from",line):
		source = '--'
		if line.find("RF voice") != -1:
			source = 'RF'
		if line.find("network voice") != -1:
			source = 'NET'
		startSlot = line.find("Slot ")+5
		startCall = line.rfind("from ")+5
		startTarget = line.rfind("to ")+3
		lenCall = startTarget-startCall-4
		slot = line[startSlot:startSlot+1]
		call = line[startCall:startCall+lenCall]
		target = line[startTarget:]
		return [slot,source,call,target]
	else:
		return False
	
def DMRData(line):
	#DMR Slot 2, received network data header from DG7ABL to TG 8, 5 blocks
	if re.search("received .* data header from",line):
		source = '--'
		if line.find("RF data") != -1:
			source = 'RF'
		if line.find("network data") != -1:
			source = 'NET'
		startSlot = line.find("Slot ")+5
		startCall = line.rfind("from ")+5
		startTarget = line.rfind("to ")+3
		lenCall = startTarget-startCall-4
		slot = line[startSlot:startSlot+1]
		call = line[startCall:startCall+lenCall]
		targetblock = line[startTarget:]
		target = targetblock.split(", ")[0]
		blocks = targetblock.split(", ")[1]
		return [slot,source,call,target,blocks]
	else:
		return False

def DMRVoiceLost(line):
	#DMR Slot 2, RF voice transmission lost, 0.8 seconds, BER: 8.8%
	if re.search("voice transmission lost",line):
		if line.find("RF") != -1:
			source = 'RF'
		if line.find("network voice") != -1:
			source = 'NET'
		info = line.split(", ")
		slot = info[0][-1]
		msg = info[1]
		duration = info[2]
		ber = info[3].replace("BER: ","")
		
		return [slot,source,duration,ber]
	else:
		return False

def DMRNetExpired(line):
	#DMR Slot 1, network watchdog has expired, 2.0 seconds, 60% packet loss, BER: 0.0%
	if re.search("network watchdog has expired",line):
		source = 'NET'
		info = line.split(", ")
		slot = info[0][-1]
		msg = info[1]
		try:
			duration = info[2]
			loss = info[3].replace(" packet loss","")
			ber = info[4].replace("BER: ","")
		except:
			duration = '?'
			loss = '?'
			ber = '?'
		return [slot,source,duration,ber,loss]
	else:
		return False	

def DMRNetLateEntry(line):
	#received network late entry from DO1HGS to TG 262
	if re.search("received network late entry",line):
		source = 'NET'
		startSlot = line.find("Slot ")+5
		startCall = line.rfind("from ")+5
		startTarget = line.rfind("to ")+3
		lenCall = startTarget-startCall-4
		slot = line[startSlot:startSlot+1]
		call = line[startCall:startCall+lenCall]
		target = line[startTarget:]
		return [slot,source,call,target]
	else:
		return False

def DMRVoiceEnd(line):
	#DMR Slot 2, received RF end of voice transmission, 3.7 seconds, BER: 3.2%
	if re.search("received .* end of voice transmission",line):
		if line.find("RF end") != -1:
			source = 'RF'
		if line.find("network end") != -1:
			source = 'NET'
		info = line.split(", ")
		slot = info[0][-1]
		msg = info[1]
		if source == 'RF':
			duration = info[2]
			loss = ''
			ber = info[3].replace("BER: ","")
		elif source == 'NET':
			duration = info[2]
			loss = info[3].replace(" packet loss","")
			ber = info[4].replace("BER: ","")
		return [slot,source,duration,ber,loss]
	else:
		return False
	
def DMRReflector(line):
	#DMR Slot 2, received network voice header from 4031 to TG 9
	if re.search("DMR Slot [0-9], received network voice header from 4[0-9]{3} to .*",line):
		startSlot = line.find("Slot ")+5
		slot = line[startSlot:startSlot+1]
		startRef = line.find("from ")+5
		ref = line[startRef:startRef+4]
		startTarget = line.find("to ")+3
		target = line[startTarget:]
		
		if ref == "4000": ref = "UNLINKED"

		return [slot,ref,target]
	else:
		return False


