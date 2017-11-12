#!/usr/bin/env python3
# -*- coding: utf-8 -*-

### mmdvm_parser.py ###
'''
	sucht das zuletzt veränderte MMDVM-Logfile im Log-Ordner
	und wartet auf neue Zeilen im Log
	Optional:	parsing der kompletten Datei
				speichern der Statusinformationen und Heard-Infos in sqlite-db
				speichern der Statusinformationen in PlainText-Files
	
	toDo:		parsing der MMDVM.ini
				parsing der DMRGateway.ini
'''

##################
## IMPORTS

import os, sys, time, glob, re, sqlite3, configparser, argparse, socket
import tail
import threading
from datetime import datetime
import mmdvm_tools as mt


##################
## GLOBALS



##################
## DEFINE CLASSES

class conf(object):
	## Config-Handler
	def __init__(self,filename = 'mmdvm_parser.ini'):
		config = configparser.ConfigParser(inline_comment_prefixes='#')
		config.read(filename)

		if not os.path.isfile(filename):
			print("[CONF] file '%s' not exists - using defaults"%filename)
			config.add_section('General')
			config.add_section('MMDVM')
			config.add_section('SQLite')
			config.add_section('PlainState')
			config.add_section('DMRGateway')

		self.filename = filename
		self.name = config['General'].get('Name',filename)
		self.debug = config['General'].getboolean('Debug',False)
		self.parse = config['General'].getboolean('Parse',True)
		self.status_display = config['General'].getint('StatusDisplayTime',60)

		self.log_path = config['MMDVM'].get('Path','/var/log/mmdvm')
		self.log_prefix = config['MMDVM'].get('Prefix','MMDVM')
		self.mmdvm_ini = config['MMDVM'].get('Ini','')
		self.loaddmrids = config['MMDVM'].getboolean('LoadDMRIds',False)

		self.dmrgateway_use = config['DMRGateway'].getboolean('Use',False)
		self.dmrgateway_ini = config['DMRGateway'].get('Ini','')

		self.sqlite_use = config['SQLite'].getboolean('Use',False)
		self.sqlite_path = config['SQLite'].get('File','mmdvm.db')
		self.sqlite_clear = config['SQLite'].getboolean('Clear',False)
		self.sqlite_history = config['SQLite'].getboolean('History',True)

		self.state_use = config['PlainState'].getboolean('Use',False)
		self.state_path = config['PlainState'].get('Path','./')
		self.state_vars = config['PlainState'].get('Vars','')

class MMDVM(object):
	## MMDVM-Status-Vars
	Status = {}
	
	def set(varname,value):
		if not (varname in MMDVM.Status):
			MMDVM.Status[varname] = ''
		if not (MMDVM.Status[varname] == value):
			MMDVM.Status['TimeStamp'] = time.time()
			MMDVM.Status[varname] = value
			if cfg.sqlite_use and not MMDVM.FullParse: 
				print("copy in db")
				litedb.state(varname,value)
				litedb.state('TimeStamp',int(MMDVM.Status['TimeStamp']))
			if cfg.state_use and (varname in cfg.state_vars) and not MMDVM.FullParse:
				print("copy in plain")
				with open(cfg.state_path+'/'+varname,'w') as f:
					f.write(value)


class logfilename(object):
	## Logfile-Var
	def __init__(self):
		self.file = ''
		
	def set(self,filename):
		self.file = filename

	def get(self):
		return self.file

class notifychanges(object):
	## Notifier
	name = 'Notify'
	def __init__(self,vars):
		for varname in vars:
			if cfg.debug: print("[%s] register vars %s"%(self.name,varname))
			setattr(self,varname,'')
			setattr(self,varname+'_callback',vars[varname])
		self.notify(vars)
	
	def notify(self,vars):
		me = threading.currentThread()
		while getattr(me, "aktiv", True):
			for varname in vars:
				if getattr(self,varname) != MMDVM.Status.get(varname,''):
					MMDVM.Status['LastStateChange'] = "%s changed: %s >> %s"%(varname,getattr(self,varname),MMDVM.Status[varname])
					MMDVM.Status['LastStateChangeStamp'] = int(time.time())
					if cfg.debug: print("[%s] callback %s value %s"%(self.name,getattr(self,varname+'_callback',vars[varname]),MMDVM.Status['LastStateChange']))
					globals()[getattr(self,varname+'_callback')](MMDVM.Status['LastStateChange'])
					setattr(self,varname,MMDVM.Status[varname])
			time.sleep(1)
		return

class sqlite_db(object):
	## SQLite-Handler
	def __init__(self):
		self.database = cfg.sqlite_path
		self.writehistory = cfg.sqlite_history
		self.cleardb = cfg.sqlite_clear
		self.conn = sqlite3.connect(self.database, check_same_thread = False)
		self.prepare()
	
	def prepare(self):
		if cfg.debug: print("[SQLite] prepare database '%s'"%self.database)
		
		c = self.conn.cursor()
		
		if cfg.debug: print("[SQLite] create if not exists 'dmr_lastheard'")
		dmrlh_cmd = '''CREATE TABLE IF NOT EXISTS dmr_lastheard (
			id INTEGER PRIMARY KEY,
			stamp INTEGER,
			slot INTEGER,
			source TEXT,
			call TEXT,
			target TEXT,
			loss TEXT,
			ber TEXT,
			duration TEXT)'''
		c.execute(dmrlh_cmd)
		self.conn.commit()
		
		if cfg.debug: print("[SQLite] create if not exists 'dmr_state'")
		dmrstate_cmd = '''CREATE TABLE IF NOT EXISTS dmr_state (
			id INTEGER PRIMARY KEY,
			stamp INTEGER,
			slot INTEGER,
			state TEXT,
			source TEXT,
			call TEXT,
			target TEXT,
			loss TEXT,
			ber TEXT,
			duration TEXT)'''
		c.execute(dmrstate_cmd)
		self.conn.commit()
		
		if cfg.debug: print("[SQLite] create if not exists 'dmr_history'")
		dmrhistory_cmd = '''CREATE TABLE IF NOT EXISTS dmr_history (
			id INTEGER PRIMARY KEY,
			stamp INTEGER,
			slot INTEGER,
			state TEXT,
			source TEXT,
			call TEXT,
			target TEXT,
			loss TEXT,
			ber TEXT,
			duration TEXT)'''
		c.execute(dmrhistory_cmd)
		self.conn.commit()
		
		if cfg.debug: print("[SQLite] create if not exists 'state'")
		state_cmd = '''CREATE TABLE IF NOT EXISTS state (
			id INTEGER PRIMARY KEY,
			stamp INTEGER,
			varname TEXT,
			value TEXT)'''
		c.execute(state_cmd)
		self.conn.commit()
		
		if cfg.debug: print("[SQLite] create if not exists 'dmr_ids'")
		state_cmd = '''CREATE TABLE IF NOT EXISTS dmr_ids (
			id INTEGER PRIMARY KEY,
			call TEXT,
			name TEXT)'''
		c.execute(state_cmd)
		self.conn.commit()

		if self.cleardb:
			if cfg.debug: print("[SQLite] clear 'dmr_lastheard'")
			c.execute("DELETE FROM dmr_lastheard;")
			c.execute("VACUUM;")
			self.conn.commit()
			if cfg.debug: print("[SQLite] clear 'dmr_history'")
			c.execute("DELETE FROM dmr_history;")
			c.execute("VACUUM;")
			self.conn.commit()
			if cfg.debug: print("[SQLite] clear 'dmr_state'")
			c.execute("DELETE FROM dmr_state;")
			c.execute("VACUUM;")
			self.conn.commit()
			if cfg.debug: print("[SQLite] clear 'state'")
			c.execute("DELETE FROM state;")
			c.execute("VACUUM;")
			self.conn.commit()
			if cfg.debug: print("[SQLite] clear 'dmr_ids'")
			c.execute("DELETE FROM dmr_ids;")
			c.execute("VACUUM;")
			self.conn.commit()
			
		if cfg.debug: print("[SQLite] prepare 'dmr_state'")
		stamp = int(time.time())
		if c.execute("SELECT COUNT(*) FROM dmr_state WHERE slot = 1").fetchone()[0] == 0 :
			c.execute("INSERT INTO dmr_state (stamp,slot,state,source,call,target,loss,ber,duration) VALUES (%s, 1, 'idle', 'HOST', '', '', '', '', '')"%stamp)
			self.conn.commit()
		if c.execute("SELECT COUNT(*) FROM dmr_state WHERE slot = 2").fetchone()[0] == 0 :
			c.execute("INSERT INTO dmr_state (stamp,slot,state,source,call,target,loss,ber,duration) VALUES (%s, 2, 'idle', 'HOST', '', '', '', '', '')"%stamp)
			self.conn.commit()
		
		c.close()
		return
	
	def dmrslotstate(self,stamp,slot,state = 'idle',source = '',call = '',target = '',loss = '',ber = '',duration = ''):
		c = self.conn.cursor()
		stamp = str(int(stamp))
		if (call == '' and target == ''):
			if cfg.debug: print("[SQLite] complete qso 'dmr_state' (%s) %s > %s"%(slot,call,target))
			c.execute("UPDATE dmr_state SET stamp = %s,state='%s',source='%s',loss='%s',ber='%s',duration='%s' WHERE slot = %s"%(stamp,state,source,loss,ber,duration,slot))
		else:
			if cfg.debug: print("[SQLite] update 'dmr_state' (%s) %s > %s"%(slot,source,target))
			c.execute("UPDATE dmr_state SET stamp = %s,state='%s',source='%s',call='%s',target='%s',loss='%s',ber='%s',duration='%s' WHERE slot = %s"%(stamp,state,source,call,target,loss,ber,duration,slot))
		self.conn.commit()
		c.close()
		
		# lookup and cache dmrids
		#if cfg.loaddmrids: find_dmrid(call)
		
		return
	
	def dmrlastheard(self,stamp,slot,state,source,call,target,loss='',ber='',duration=''):
		c = self.conn.cursor()
		stamp = str(int(stamp))
		if call == '' and target == '':
			if cfg.debug: print("[SQLite] complete qso 'dmr_lastheard' (%s) %s > %s"%(slot,call,target))
			c.execute("UPDATE dmr_lastheard SET loss='%s',ber='%s',duration='%s',stamp=%s WHERE source='%s' AND slot='%s' ORDER BY stamp DESC LIMIT 1"%(loss,ber,duration,stamp,source,slot))
			self.conn.commit()
		else:
			if c.execute("SELECT COUNT(*) FROM dmr_lastheard WHERE stamp=%s AND slot=%s AND source='%s' AND call='%s' AND target='%s'"%(stamp,slot,source,call,target)).fetchone()[0] == 0 :
				if c.execute("SELECT COUNT(*) FROM dmr_lastheard WHERE call = '%s'"%call).fetchone()[0] == 0:
					if cfg.debug: print("[SQLite] add 'dmr_lastheard' (%s) %s > %s"%(slot,call,target))
					c.execute("INSERT INTO dmr_lastheard (stamp,slot,source,call,target,loss,ber,duration) VALUES (%s,%s,'%s','%s','%s','%s','%s','%s')"%(stamp,slot,source,call,target,loss,ber,duration))
				else:
					if cfg.debug: print("[SQLite] update 'dmr_lastheard' (%s) %s > %s"%(slot,call,target))
					c.execute("UPDATE dmr_lastheard SET stamp = %s,slot = %s,source='%s',call='%s',target='%s',loss='%s',ber='%s',duration='%s' WHERE call = '%s'"%(stamp,slot,source,call,target,loss,ber,duration,call))
				self.conn.commit()
			else:
				if cfg.debug: print("[SQLite] duplicate entry 'dmr_lastheard' (%s) %s > %s"%(slot,call,target))
			
		if self.writehistory and c.execute("SELECT COUNT(*) FROM dmr_history WHERE stamp=%s AND slot=%s AND source='%s' AND call='%s' AND target='%s'"%(stamp,slot,source,call,target)).fetchone()[0] == 0:
			if cfg.debug: print("[SQLite] add 'dmr_history' (%s) %s > %s"%(slot,call,target))
			if call == '' and target == '':
				row = c.execute("SELECT call,target FROM dmr_history WHERE source='%s' AND slot='%s' ORDER BY stamp DESC LIMIT 1"%(source,slot)).fetchone()
				call = row[0]
				target = row[1]
			c.execute("INSERT INTO dmr_history (stamp,slot,state,source,call,target,loss,ber,duration) VALUES (%s,%s,'%s','%s','%s','%s','%s','%s','%s')"%(stamp,slot,state,source,call,target,loss,ber,duration))
			self.conn.commit()
		else:
			if cfg.debug: print("[SQLite] duplicate entry 'dmr_history'")
		c.close()
		return
	
	def state(self,varname,value):
		c = self.conn.cursor()
		stamp = str(int(time.time()))
		if c.execute("SELECT COUNT(*) FROM state WHERE varname='%s'"%varname).fetchone()[0] == 0:
			if cfg.debug: print("[SQLite] add 'state' %s > %s"%(varname,value))
			c.execute("INSERT INTO state (stamp,varname,value) VALUES (%s,'%s','%s')"%(stamp,varname,value))
		else:
			if cfg.debug: print("[SQLite] update 'state' %s > %s"%(varname,value))
			c.execute("UPDATE state SET stamp=%s,value='%s' WHERE varname='%s'"%(stamp,value,varname))
		self.conn.commit()
		c.close()
		return
	
	def store_dmrid(self,id,call,name):
		c = self.conn.cursor()
		if c.execute("SELECT COUNT(*) FROM dmr_ids WHERE id='%s'"%id).fetchone()[0] == 0:
			if cfg.debug: print("[SQLite] add 'dmr_ids' %s: %s %s"%(id,call,name))
			c.execute("INSERT INTO dmr_ids (id,call,name) VALUES (%s,'%s','%s')"%(id,call,name))
		else:
			if cfg.debug: print("[SQLite] update 'dmr_ids' %s: %s %s"%(id,call,name))
			c.execute("UPDATE dmr_ids SET call='%s',name='%s' WHERE id=%s"%(call,name,id))
		self.conn.commit()
		c.close()
		return


##################
## DEFINE FUNCTIONS


#	Line-Parser
def line_parser(line,getStamp=False):
	#global MMDVMStatus
	
	me = threading.currentThread()
	if cfg.debug: print("[Parse] getting new line from logfile %s"%(me.filename))
	line = line.rstrip("\n")
	
	if getStamp:
		Stamp = mt.MMDVMTime(line)
	else:
		Stamp = False
	
	if Stamp == False:
		Stamp = int(time.time())
	
	if mt.MMDVMHostState(line):
		hoststate = mt.MMDVMHostState(line)
		if cfg.debug: print("[Parse] MMDVMHost Version: %s"%(hoststate[0]))
		if cfg.debug: print("[Parse] MMDVMHost State: %s"%(hoststate[1]))
		MMDVM.set('HostVersion',hoststate[1])
		MMDVM.set('HostState',hoststate[0])
		#if cfg.sqlite_use:
		#	litedb.state('HostVersion',hoststate[1])
		#	litedb.state('HostState',hoststate[0])
		#	litedb.state('TimeStamp',str(int(Stamp)))
	
	if mt.MMDVMModes(line):
		modes = mt.MMDVMModes(line)
		if cfg.debug: print("[Parse] Mode: %s > %s"%(modes[0],modes[1]))
		MMDVM.set('Mode_'+modes[0],modes[1])
		#if cfg.sqlite_use:
		#	litedb.state('Mode_'+modes[0],modes[1])
		#	litedb.state('TimeStamp',str(int(Stamp)))
	
	if mt.MMDVMHostBuilt(line):
		built = mt.MMDVMHostBuilt(line)
		if cfg.debug: print("[Parse] MMDVMHost built: %s"%(built))
		MMDVM.set('HostBuilt',built)
		#if cfg.sqlite_use:
		#	litedb.state('HostBuilt',built)
		#	litedb.state('TimeStamp',str(int(Stamp)))
	
	if mt.MMDVMVersion(line):
		version = mt.MMDVMVersion(line)
		if cfg.debug: print("[Parse] MMDVM Version: %s"%(version))
		MMDVM.set('Version',version)
		#if cfg.sqlite_use:
		#	litedb.state('Version',version)
		#	litedb.state('TimeStamp',str(int(Stamp)))
	
	if mt.MMDVMCallsign(line):
		callsign = mt.MMDVMCallsign(line)
		if cfg.debug: print("[Parse] DMR Call: %s"%(callsign))
		MMDVM.set('Callsign',callsign)
		#if cfg.sqlite_use:
		#	litedb.state('Callsign',callsign)
		#	litedb.state('TimeStamp',str(int(Stamp)))
	
	if mt.MMDVMId(line):
		id = mt.MMDVMId(line)
		if cfg.debug: print("[Parse] DMR id: %s"%(id))
		MMDVM.set('Id',id)
		#if cfg.sqlite_use:
		#	litedb.state('Id',id)
		#	litedb.state('TimeStamp',str(int(Stamp)))
	
	if mt.DMRMasterState(line):
		masterstate = mt.DMRMasterState(line)
		if cfg.debug: print("[Parse] DMR Master: %s"%(masterstate))
		MMDVM.set('DMRMasterState',masterstate)
		#if cfg.sqlite_use:
		#	litedb.state('DMRMasterState',masterstate)
		#	litedb.state('TimeStamp',str(int(Stamp)))
	
	if mt.DownlinkActive(line):
		if cfg.debug: print("[Parse] Downlink by %s"%mt.DownlinkActive(line))
		pass
	
	if mt.DMRReflector(line):
		ref = mt.DMRReflector(line)
		if cfg.debug: print("[Parse] DMR Reflector: %s : %s"%(ref[0],ref[1]))
		MMDVM.set('DMRSlot%sReflector'%ref[0],ref[1])
		#if cfg.sqlite_use:
		#	litedb.state('DMRSlot%sReflector'%ref[0],ref[1])
		#	litedb.state('TimeStamp',str(int(Stamp)))
		#if cfg.state_use:
		#	with open(cfg.state_path+'/dmr.reflector','w') as f:
		#		f.write(ref[1])
	
	if mt.DMRVoice(line):
		voice = mt.DMRVoice(line)
		slot = voice[0]
		if cfg.debug: print("[Parse] DMR Voice Slot: %s Source: %s Call: %s Target: %s"%(voice[0],voice[1],voice[2],voice[3]))
		MMDVM.set('DMRSlot%s'%slot,'AKTIV')
		MMDVM.set('DMRSlot%sSource'%slot,voice[1])
		MMDVM.set('DMRSlot%sCall'%slot,voice[2])
		MMDVM.set('DMRSlot%sTarget'%slot,voice[3])
		MMDVM.set('DMRSlot%sStamp'%slot,Stamp)
		if cfg.sqlite_use:
			litedb.dmrslotstate(Stamp,slot,'AKTIV',voice[1],voice[2],voice[3])
			litedb.dmrlastheard(Stamp,slot,'start',voice[1],voice[2],voice[3])
		#	litedb.state('TimeStamp',str(int(Stamp)))
	
	if mt.DMRVoiceLost(line):
		voice = mt.DMRVoiceLost(line)
		slot = voice[0]
		if cfg.debug: print("[Parse] DMR VoiceLost Slot: %s Source: %s Duration: %s BER: %s"%(voice[0],voice[1],voice[2],voice[3]))
		MMDVM.set('DMRSlot%s'%slot,'LOST')
		MMDVM.set('DMRSlot%sSource'%slot,voice[1])
		MMDVM.set('DMRSlot%sDuration'%slot,voice[2])
		MMDVM.set('DMRSlot%sBER'%slot,voice[3])
		MMDVM.set('DMRSlot%sStamp'%slot,Stamp)
		if cfg.sqlite_use:		
			litedb.dmrslotstate(Stamp,slot,'LOST',voice[1],'','','',voice[3],voice[2])
			litedb.dmrlastheard(Stamp,slot,'lost',voice[1],'','','',voice[3],voice[2])
		#	litedb.state('TimeStamp',str(int(Stamp)))
	
	if mt.DMRVoiceEnd(line):
		voice = mt.DMRVoiceEnd(line)
		slot = voice[0]
		if cfg.debug: print("[Parse] DMR VoiceEnd Slot: %s Source: %s Duration: %s BER: %s Loss: %s"%(voice[0],voice[1],voice[2],voice[3],voice[4]))
		MMDVM.set('DMRSlot%s'%slot,'ENDE')
		MMDVM.set('DMRSlot%sSource'%slot,voice[1])
		MMDVM.set('DMRSlot%sDuration'%slot,voice[2])
		MMDVM.set('DMRSlot%sBER'%slot,voice[3])
		MMDVM.set('DMRSlot%sLoss'%slot,voice[4])
		MMDVM.set('DMRSlot%sStamp'%slot,Stamp)
		if cfg.sqlite_use:
			litedb.dmrslotstate(Stamp,slot,'ENDE',voice[1],'','',voice[4],voice[3],voice[2])
			litedb.dmrlastheard(Stamp,slot,'end',voice[1],'','',voice[4],voice[3],voice[2])
		#	litedb.state('TimeStamp',str(int(Stamp)))
	
	if mt.DMRNetExpired(line):
		voice = mt.DMRNetExpired(line)
		slot = voice[0]
		if cfg.debug: print("[Parse] DMR VoiceLost Slot: %s Source: %s Duration: %s BER: %s Loss: %s"%(voice[0],voice[1],voice[2],voice[3],voice[4]))
		MMDVM.set('DMRSlot%s'%slot,'ENDE')
		MMDVM.set('DMRSlot%sSource'%slot,voice[1])
		MMDVM.set('DMRSlot%sDuration'%slot,voice[2])
		MMDVM.set('DMRSlot%sBER'%slot,voice[3])
		MMDVM.set('DMRSlot%sLoss'%slot,voice[4])
		MMDVM.set('DMRSlot%sStamp'%slot,Stamp)
		if cfg.sqlite_use:
			litedb.dmrslotstate(Stamp,slot,'LOST',voice[1],'','',voice[4],voice[3],voice[2])
			litedb.dmrlastheard(Stamp,slot,'lost',voice[1],'','',voice[4],voice[3],voice[2])
		#	litedb.state('TimeStamp',str(int(Stamp)))
	
	if mt.DMRNetLateEntry(line):
		voice = mt.DMRNetLateEntry(line)
		slot = voice[0]
		if cfg.debug: print("[Parse] DMR VoiceLate Slot: %s Source: %s Call: %s Target: %s"%(voice[0],voice[1],voice[2],voice[3]))
		MMDVM.set('DMRSlot%s'%slot,'AKTIV')
		MMDVM.set('DMRSlot%sSource'%slot,voice[1])
		MMDVM.set('DMRSlot%sCall'%slot,voice[2])
		MMDVM.set('DMRSlot%sTarget'%slot,voice[3])
		MMDVM.set('DMRSlot%sStamp'%slot,Stamp)
		if cfg.sqlite_use:
			litedb.dmrslotstate(Stamp,slot,'AKTIV',voice[1],voice[2],voice[3])
			litedb.dmrlastheard(Stamp,slot,'start',voice[1],voice[2],voice[3])
		#	litedb.state('TimeStamp',str(int(Stamp)))
	
	#MMDVM.set('TimeStamp',Stamp)
	return

#	LastLog-Finder
def log_find():
	me = threading.currentThread()
	me.logfile = ''
	while getattr(me, "aktiv", True):
		try:
			lastmod = max(glob.iglob(cfg.log_path+'/'+cfg.log_prefix+'-*'), key=os.path.getctime)
			if lastmod != me.logfile:
				logfile.set(lastmod)
				me.logfile = lastmod
				if cfg.debug: print("[%s] changing logfile %s"%(me.name,me.logfile))
		except:
			if cfg.debug: print("[%s] error while getting lastlogfile %s"%(me.name,me.logfile))
			pass
		time.sleep(1)

#	threaded tail
def tail_follow():
	me = threading.currentThread()
	me.logfile = ''
	while getattr(me, "aktiv", True):
		if logfile.get() != me.logfile:
			try:
				log.stop()
			except:
				pass
			
			try:
				me.logfile = logfile.get()
				if cfg.debug: print("[%s] registering logfile %s"%(me.name,me.logfile))
				if cfg.parse:
					if cfg.debug: print("[%s_parse] start parsing whole file %s"%(me.name,me.logfile))
					try:
						MMDVM.FullParse = True
						startat = time.time()
						with open(me.logfile) as file_:
							MMDVM.set('Parsing_File',me.logfile)
							me.filename = me.logfile
							for line in file_:
								line_parser(line,True)
						endat = time.time()
					except:
						if cfg.debug: print("[%s_parse] error while parsing whole file %s"%(me.name,me.logfile))
						raise
						print("Unexpected error:", sys.exc_info()[0])
					duration = str(int((endat-startat)*10)/10)
					#MMDVM.set('TimeStamp',time.time())
					MMDVM.FullParse = False
					MMDVM.set('Parsing_Duration',duration)
					#flush_state()
					if cfg.debug: print("[%s_parse] finished parsing whole file %s in %s seconds"%(me.name,me.logfile,duration))
				log = tail.Tail(me.logfile,cfg.debug,me.name)
				log.register_callback(line_parser)
				log.follow()
			except:
				if cfg.debug: print("[%s] error while initialising tail %s"%(me.name,me.logfile))
				raise
		else:
			#nothin do do here
			pass
		time.sleep(1)
	try:
		log.stop()
	except:
		pass


#	Flush MMDVM-Status > SQLite & PlainText
def flush_state():
	if cfg.debug: print("[MMDVM] flushing MMDVMState")
	if not 'TimeStamp' in MMDVM.Status:
		MMDVM.Status['TimeStamp'] = time.time()
	
	for varname in MMDVM.Status:
		if cfg.sqlite_use:
			if (varname == 'TimeStamp'):
				value = str(int(MMDVM.Status[varname]))
			else:
				value = MMDVM.Status[varname]
			litedb.state(varname,value)
		if cfg.state_use and (varname in cfg.state_vars):
			if cfg.debug: print("[PlainState] writing '%s' in '%s'"%(value,cfg.state_path+'/'+varname))
			with open(cfg.state_path+'/'+varname,'w') as f:
				f.write(value)


#	print as Callback
def call_print(line):
	print(line)
	return


#	Check if Hostname resolves as localhost
def resolves_local(hostname):
	if (socket.gethostbyname(hostname) == socket.gethostbyname('localhost')):
		return True
	else:
		return False


#	parsing mmdvm-ini and set MMDVM.Status
def parse_mmdvmini():
	mmdvmini = mt.mmdvm_ini(cfg)
	if mmdvmini.found:
		if cfg.debug: print("[mmdvm-ini] converting to MMDVMState")
		MMDVM.Status['Callsign'] = mmdvmini.callsign
		MMDVM.Status['Id'] = mmdvmini.id
		MMDVM.Status['Duplex'] = mmdvmini.duplex
		
		MMDVM.Status['Mode_DMR'] = mmdvmini.dmr_enable
		MMDVM.Status['Mode_YSF'] = mmdvmini.ysf_enable
		MMDVM.Status['Mode_P25'] = mmdvmini.p25_enable
		MMDVM.Status['Mode_D-Star'] = mmdvmini.dstar_enable
		
		MMDVM.Status['DMRMasterAddress'] = mmdvmini.dmr_net_address
		MMDVM.Status['DMRMasterPort'] = mmdvmini.dmr_net_port
		
		if resolves_local(MMDVM.Status['DMRMasterAddress']):
			MMDVM.Status['DMRGateway'] = True
		
		MMDVM.Status['DMRIdFile'] = mmdvmini.dmr_id_file
		
		MMDVM.Status['Info_Latitude'] = mmdvmini.info_lat
		MMDVM.Status['Info_Longitude'] = mmdvmini.info_lon
		MMDVM.Status['Info_RXFrequency'] = mmdvmini.info_rxfreq
		MMDVM.Status['Info_TXFrequency'] = mmdvmini.info_txfreq
		MMDVM.Status['Info_Power'] = mmdvmini.info_power
		MMDVM.Status['Info_Height'] = mmdvmini.info_height
		MMDVM.Status['Info_Location'] = mmdvmini.info_loc
		MMDVM.Status['Info_Description'] = mmdvmini.info_desc
		MMDVM.Status['Info_URL'] = mmdvmini.info_url
		flush_state()
	return


#	parsing dmrgateway-ini and set MMDVM.Status
def parse_dmrgatewayini():
	dmrini = mt.dmrgateway_ini(cfg)
	if dmrini.found:
		if cfg.debug: print("[dmrgateway-ini] converting to MMDVMState")
		i = 0
		for dmrnet in dmrini.dmr_networks:
			i += 1
			MMDVM.Status['DMRGateway'] = i
			MMDVM.Status["DMRGateway_%s"%i] = dmrini.dmr_net_enable[dmrnet]
			MMDVM.Status["DMRGateway_%s_name"%i] = dmrini.dmr_net_name[dmrnet]
			MMDVM.Status["DMRGateway_%s_address"%i] = dmrini.dmr_net_address[dmrnet]
			MMDVM.Status["DMRGateway_%s_port"%i] = dmrini.dmr_net_port[dmrnet]
		flush_state()
	return


#	find a call/id in dmrids and store in database
def find_dmrid(lookfor):
	if MMDVM.Status['DMRIdFile'] != '' and cfg.sqlite_use and lookfor != '':
		try:
			with open(MMDVM.Status['DMRIdFile'],'rb') as file:
				if cfg.debug: print("[dmrids-dat] lookfor '%s' in '%s'"%(lookfor,cfg.sqlite_path))
				for line in file:
					splitline = line.split()
					dmrid = splitline[0].decode('utf-8')
					usercall = splitline[1].decode('utf-8')
					try:
						username = splitline[2].decode('utf-8')
					except:
						username = ''
					if (lookfor == usercall) or (lookfor == dmrid):
						if cfg.debug: print("[dmrids-dat] copy line to '%s'"%cfg.sqlite_path)
						litedb.store_dmrid(dmrid,usercall,username)
		except:
			raise
			if cfg.debug: print("[dmrids-dat] error opening '%s'"%MMDVM.Status['DMRIdFile'])
	return

##################
## PREPARE MAIN

#	load config before parsing arguments
cfg = conf()
MMDVM.Status['DMRGateway'] = cfg.dmrgateway_use
MMDVM.FullParse = False

#	parsing arguments
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--debug", action="store_true", help="enable debugging (overrides config)")
parser.add_argument("--nodebug", action="store_true", help="disable debugging (overrides config)")
parser.add_argument("-p", "--parse", action="store_true", help="enable parsing complete files (overrides config)")
parser.add_argument("--noparse", action="store_true", help="disable parsing complete files (overrides config)")
parser.add_argument("--sqlite_clear", action="store_true", help="enable clear sqlite on startup (overrides config)")
parser.add_argument("--nosqlite", action="store_true", help="disable sqlite (overrides config)")
parser.add_argument("-c", "--config", help="using alternative config (default uses mmdvm_parser.ini)")
parser.add_argument("-mc", "--mmdvm_config", help="using alternative mmdvm_config (default uses MMDVM.ini)")
args = parser.parse_args()

if (args.config):
	if cfg.debug: print("[CONF] reload from '%s'"%args.config)
	cfg = conf(args.config)
if (args.mmdvm_config):
	if cfg.debug: print("[CONF] use MMDVMHost-Config from '%s'"%args.mmdvm_config)
	cfg.mmdvm_ini = args.mmdvm_config
if (args.debug): 
	if cfg.debug: print("[CONF] set debug = True")
	cfg.debug = True
if (args.nodebug): 
	if cfg.debug: print("[CONF] set debug = False")
	cfg.debug = False
if (args.parse): 
	if cfg.debug: print("[CONF] set parse = True")
	cfg.parse = True
if (args.noparse): 
	if cfg.debug: print("[CONF] set parse = False")
	cfg.parse = False
if (args.sqlite_clear): 
	if cfg.debug: print("[CONF] set sqlite:clear = True")
	cfg.sqlite_clear = True
if (args.nosqlite): 
	if cfg.debug: print("[CONF] disable sqlite (sqlite: use = False)")
	cfg.sqlite_use = False

#	load sqlite
if cfg.sqlite_use:
	if cfg.debug: print("[MAIN] using SQLite '%s'"%cfg.sqlite_path)
	litedb = sqlite_db()

#	load mmdvm-ini and parse
parse_mmdvmini()

#	load dmrgateway-ini and parse only if nessesary
if MMDVM.Status['DMRGateway']:
	parse_dmrgatewayini()

#	dict for registering notify-callbacks
notify_vars = {'HostState':'call_print','DMRMasterState':'call_print','Parsing_Duration':'call_print'}

#	instance Logfile
logfile = logfilename()

#	prepare var
LastStamp = ''


#sys.exit()


##################
## MAIN CODE

MMDVM.set('Parser','AKTIV')

t_logfind = threading.Thread(target=log_find, name='LogFind')
if cfg.debug: print("[MAIN] starting thread '%s'"%t_logfind.name)
t_logfind.start()

t_tail = threading.Thread(target=tail_follow, name='Tail')
if cfg.debug: print("[MAIN] starting thread '%s'"%t_tail.name)
t_tail.start()

t_notify = threading.Thread(target=notifychanges, name='MMDVM', args=(notify_vars,))
if cfg.debug: print("[MAIN] starting thread '%s'"%t_notify.name)
t_notify.start()

#print("going to main loop ... in 10 seconds ...")
#time.sleep(10)

while True:
	try:
		if cfg.debug: print("[MAIN] current logfile is %s"%logfile.get())
		
		if (time.time()-MMDVM.Status.get('DMRSlot1Stamp',time.time())) > cfg.status_display and MMDVM.Status.get('DMRSlot1','idle') != 'idle':
			MMDVM.Status['DMRSlot1'] = 'idle'
			MMDVM.Status['TimeStamp'] = int(time.time())
			pass

		if (time.time()-MMDVM.Status.get('DMRSlot2Stamp',time.time())) > cfg.status_display and MMDVM.Status.get('DMRSlot2','idle') != 'idle':
			MMDVM.Status['DMRSlot2'] = 'idle'
			MMDVM.Status['TimeStamp'] = int(time.time())
			pass

		if LastStamp != MMDVM.Status.get('TimeStamp',''):
			LastStamp = MMDVM.Status.get('TimeStamp')
			os.system('clear')
			
			if MMDVM.Status.get('DMRSlot1','') == 'ENDE':
				dur = MMDVM.Status.get('DMRSlot1Duration')
				ber = MMDVM.Status.get('DMRSlot1BER')
				loss = MMDVM.Status.get('DMRSlot1Loss')
				stamp = time.strftime("%H:%M:%S",time.localtime(MMDVM.Status.get('DMRSlot1Stamp')))
				info1 = "%s (PL %s BER %s) %s"%(dur,loss,ber,stamp)
			else:
				info1 = ''

			if MMDVM.Status.get('DMRSlot2','') == 'ENDE':
				dur = MMDVM.Status.get('DMRSlot2Duration')
				ber = MMDVM.Status.get('DMRSlot2BER')
				loss = MMDVM.Status.get('DMRSlot2Loss')
				stamp = time.strftime("%H:%M:%S",time.localtime(MMDVM.Status.get('DMRSlot2Stamp')))
				info2 = "%s (PL %s BER %s) %s"%(dur,loss,ber,stamp)
			else:
				info2 = ''

			if MMDVM.Status.get('DMRSlot1','idle') != 'idle':
				print("DMRSlot1: [%s] %s: %s %s %s"%(MMDVM.Status.get('DMRSlot1', 'idle'),MMDVM.Status.get('DMRSlot1Source',''),MMDVM.Status.get('DMRSlot1Call', ''),MMDVM.Status.get('DMRSlot1Target', ''),info1))
			else:
				print("DMRSlot1: [%s]"%MMDVM.Status.get('DMRSlot1','idle'))

			if MMDVM.Status.get('DMRSlot2','idle') != 'idle':
				print("DMRSlot2: [%s] %s: %s %s %s"%(MMDVM.Status.get('DMRSlot2', 'idle'),MMDVM.Status.get('DMRSlot2Source',''),MMDVM.Status.get('DMRSlot2Call', ''),MMDVM.Status.get('DMRSlot2Target', ''),info2))
			else:
				print("DMRSlot2: [%s]"%MMDVM.Status.get('DMRSlot2','idle'))
	
			print("DMRSlot2: Reflector %s"%(MMDVM.Status.get('DMRSlot2Reflector', 'unknown')))

			if MMDVM.Status.get('LastStateChange', '') != '' and (time.time()-MMDVM.Status.get('LastStatusChangeStamp',0)) < cfg.status_display: 
				print("\n[Notify] %s"%MMDVM.Status['LastStateChange'])
			
		time.sleep(1)
		
	except KeyboardInterrupt:
		MMDVM.set('Parser','ENDE')
		if cfg.debug: print("[MAIN] request QUIT by Keyboard")
		t_logfind.aktiv = False
		t_logfind.join()
		t_tail.aktiv = False
		t_tail.join()
		t_notify.aktiv = False
		t_notify.join()
		sys.exit(1)
		
	except:
		try:
			MMDVM.set('Parser','ENDE')
		except:
			pass
		if cfg.debug: print("[MAIN] QUIT after ERROR")
		t_logfind.aktiv = False
		t_logfind.join()
		t_tail.aktiv = False
		t_tail.join()
		t_notify.aktiv = False
		t_notify.join()
		raise
		sys.exit(0)
