#!/usr/bin/env python3
# -*- coding: utf-8 -*-

### mmdvm_parser.py ###
'''
	sucht das zuletzt veränderte MMDVM-Logfile im Log-Ordner
	und wartet auf neue Zeilen im Log
'''

##################
## IMPORTS

import os, sys, time, glob, re, sqlite3, configparser, argparse, socket
import tail
import threading
from datetime import datetime
import mmdvm_tools as mt
import mysql.connector as mc
import plain_reader as pr


##################
## GLOBALS



##################
## DEFINE CLASSES

class conf(object):
	## Config-Handler
	def __init__(self,filename = 'mmdvm_parser.ini'):
		config = configparser.ConfigParser()
		config.read(filename)

		if not os.path.isfile(filename):
			print("[CONF] file '%s' not exists - using defaults"%filename)
			config.add_section('General')
			config.add_section('MMDVM')
			config.add_section('SQLite')
			config.add_section('PlainState')
			config.add_section('DMRGateway')
			config.add_section('PlainReader')

		self.filename = filename
		self.name = config['General'].get('Name',filename)
		self.debug = config['General'].getboolean('Debug',False)
		self.debug_level = config['General'].getint('Debug_level',1)
		self.parse = config['General'].getboolean('Parse',True)
		self.status_display = config['General'].getint('StatusDisplayTime',60)

		self.log_use = config['Log'].getboolean('Use',False)
		self.log_path = config['Log'].get('Path','var/log/')
		self.log_prefix = config['Log'].get('Prefix','mmdvmdash')
		self.log_level = config['Log'].getint('Level',1)

		self.mmdvm_log_path = config['MMDVM'].get('Path','/var/log/mmdvm')
		self.mmdvm_log_prefix = config['MMDVM'].get('Prefix','MMDVM')
		self.mmdvm_ini = config['MMDVM'].get('Ini','')
		self.loaddmrids = config['MMDVM'].getboolean('LoadDMRIds',False)

		self.dmrgateway_use = config['DMRGateway'].getboolean('Use',False)
		self.dmrgateway_ini = config['DMRGateway'].get('Ini','')

		self.sqlite_use = config['SQLite'].getboolean('Use',False)
		self.sqlite_path = config['SQLite'].get('File','mmdvm.db')
		self.sqlite_clear = config['SQLite'].getboolean('Clear',False)
		self.sqlite_history = config['SQLite'].getboolean('History',True)

		self.mysql_use = config['MySQL'].getboolean('Use',False)
		self.mysql_db = config['MySQL'].get('DB','dash')
		self.mysql_host = config['MySQL'].get('Host','localhost')
		self.mysql_port = config['MySQL'].get('Port','3306')
		self.mysql_user = config['MySQL'].get('User','dash')
		self.mysql_pass = config['MySQL'].get('Pass','secret')
		self.mysql_clear = config['MySQL'].getboolean('Clear',False)
		self.mysql_history = config['MySQL'].getboolean('History',True)
		self.mysql_mirror = config['MySQL'].getboolean('Mirror',False)
		
		self.state_use = config['PlainState'].getboolean('Use',False)
		self.state_path = config['PlainState'].get('Path','./')
		self.state_vars = config['PlainState'].get('Vars','')
		
		self.plainreader_use = config['PlainReader'].getboolean('Use',False)
		self.plainreader = {}
		if self.plainreader_use:
			for varname,options in config.items('PlainReader'):
				if varname != 'use':
					option = options.split(',')
					options = {}
					try:
						options['file'] = option[0]
					except:
						options['file'] = '/dev/null'
					try:
						options['interval'] = option[1]
					except:
						options['interval'] = 60
					try:
						options['type'] = option[2]
					except:
						options['type'] = 'smart'
					self.plainreader[varname] = options
	def log(self,line,type='I'):
		#type: I=Info. W=Warn, E=Error
		#cfg.log_level = 1 = Error, 2 = Error+Warn, 3 = Error+Warn+Info 4 = Debug
		if type == 'D': level = 4
		if type == 'I': level = 3
		if type == 'W': level = 2
		if type == 'E': level = 1
		if self.debug and level <= cfg.debug_level:
			print(type+': '+line)
		if self.log_use and level <= cfg.log_level:
			logname = time.strftime('%Y-%m-%d')
			logtime = time.strftime('%Y-%m-%d %H:%M:%S')
			with open(self.log_path+'/'+self.log_prefix+'_'+logname+'.log','a') as f:
				f.write(type+': '+logtime+' '+line+'\n')

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
				cfg.log("[SQlite] writing state-data %s:%s"%(varname,str(value)))
				litedb.state(varname,value)
				litedb.state('TimeStamp',int(MMDVM.Status['TimeStamp']))
			if cfg.mysql_use and not cfg.mysql_mirror and not MMDVM.FullParse:
				cfg.log("[MySQL] writing state-data %s:%s"%(varname,str(value)))
				mydb.state(varname,value)
				mydb.state('TimeStamp',int(MMDVM.Status['TimeStamp']))
			if cfg.state_use and (varname in cfg.state_vars) and not MMDVM.FullParse:
				cfg.log("[Plain] writing state-data %s:%s"%(varname,str(value)))
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

class notify_changes(object):
	## Notifier
	def __init__(self,cfg,vars):
		for varname in vars:
			cfg.log("[notify] register vars %s"%(varname),'D')
			setattr(self,varname,'')
			setattr(self,varname+'_callback',vars[varname])
		self.cfg = cfg
		self.active = True
		self.thread = threading.Thread(target=self.run, args=(self,vars,))
		self.thread.start()
		return
	
	def run(self,caller,vars):
		while caller.active:
			for varname in vars:
				if getattr(self,varname) != MMDVM.Status.get(varname,''):
					MMDVM.Status['LastStateChange'] = "%s changed: %s >> %s"%(varname,getattr(self,varname),MMDVM.Status[varname])
					MMDVM.Status['LastStateChangeStamp'] = int(time.time())
					self.cfg.log("[notify] callback %s value %s"%(getattr(self,varname+'_callback',vars[varname]),MMDVM.Status['LastStateChange']),'D')
					globals()[getattr(self,varname+'_callback')](MMDVM.Status['LastStateChange'])
					setattr(self,varname,MMDVM.Status[varname])
			time.sleep(1)
		self.cfg.log('[notify] STOP thread')
		return
	
	def stop(self):
		self.cfg.log('[notify] STOPPING thread')
		self.active = False
		self.cfg.log('[notify] WAIT for thread','D')
		self.thread.join()
		return

class db_mirror(object):
	## db-mirror-Handle
	def __init__(self):
		self.mirror()
	
	def mirror(self):
		me = threading.currentThread()
		while getattr(me, "aktiv", True):
			tables = ['state','dmr_lastheard','dmr_history','dmr_state']
			for table in tables:
				mystamp = self.mysql_stamp(table)
				if not mystamp:
					cfg.log("[mysql_mirror] ERROR getting stamp from '%s'"%table,'E')
					continue
				if mystamp < self.sqlite_stamp(table):
					cfg.log("[mysql_mirror] copy new data to '%s'"%table,'D')
					self.copy(table, mystamp)
			time.sleep(1)

	def execute(self,sqlquery):
		try:
			myconn = mc.connect(host = cfg.mysql_host, port = cfg.mysql_port, user = cfg.mysql_user, passwd = cfg.mysql_pass, db = cfg.mysql_db)
			m_c = myconn.cursor()
			for result in m_c.execute(sqlquery, multi = True):
				pass
			myconn.commit()
			myconn.close()
			cfg.log("[mysql_mirror] copy data to '%s' successful"%cfg.mysql_host,'D')
		except:
			cfg.log("[mysql_mirror] ERROR while copy data to '%s'"%cfg.mysql_host,'E')
		return
	
	def select(self,table,from_stamp):
		liteconn = sqlite3.connect(cfg.sqlite_path, check_same_thread = False)
		s_c = liteconn.cursor()
		s_c.execute("SELECT * FROM %s WHERE stamp > %s"%(table,from_stamp))
		s_result = s_c.fetchall()
		return s_result
	
	def sqlite_stamp(self,table_name):
		liteconn = sqlite3.connect(cfg.sqlite_path, check_same_thread = False)
		s_c = liteconn.cursor()
		s_c.execute("SELECT stamp FROM %s ORDER BY stamp DESC LIMIT 1"%(table_name))
		return s_c.fetchone()[0]
	
	def mysql_stamp(self,table_name):
		try:
			myconn = mc.connect(host = cfg.mysql_host, port = cfg.mysql_port, user = cfg.mysql_user, passwd = cfg.mysql_pass, db = cfg.mysql_db)
			m_c = myconn.cursor()
			m_c.execute("SELECT stamp FROM %s ORDER BY stamp DESC LIMIT 1"%(table_name))
			return m_c.fetchone()[0]
		except:
			cfg.log("[mysql_mirror] ERROR while getting stamp from '%s'"%cfg.mysql_host,'E')
			return False

	def copy(self,table_name,from_stamp):
		sql = ''
		for row in self.select(table_name,from_stamp):
			if table_name == 'state':
				#id,stamp,varname,value
				stamp = row[1]
				varname = row[2]
				value = row[3]
				sql += "DELETE FROM state WHERE varname = '%s';\n"%(varname)
				sql += "INSERT INTO state (stamp,varname,value) VALUES (%i,'%s','%s');\n"%(stamp,varname,value)
			elif table_name == 'dmr_state':
				#id,stamp,slot,state,source,caller,target,loss,ber,duration,rssi
				stamp = row[1]
				slot = row[2]
				state = row[3]
				source = row[4]
				caller = row[5]
				target = row[6]
				loss = row[7]
				ber = row[8]
				duration = row[9]
				rssi = row[10]
				sql += "DELETE FROM dmr_state WHERE slot = %s;\n"%(slot)
				sql += "INSERT INTO dmr_state (stamp,slot,state,source,caller,target,loss,ber,duration,rssi) VALUES (%i,%i,'%s','%s','%s','%s','%s','%s','%s','%s');\n"%(stamp,slot,state,source,caller,target,loss,ber,duration,rssi)
			elif table_name == 'dmr_lastheard':
				#id,stamp,slot,source,caller,target,loss,ber,duration,rssi
				stamp = row[1]
				slot = row[2]
				source = row[3]
				caller = row[4]
				target = row[5]
				loss = row[6]
				ber = row[7]
				duration = row[8]
				rssi = row[9]
				sql += "DELETE FROM dmr_lastheard WHERE caller = '%s';\n"%(caller)
				sql += "INSERT INTO dmr_lastheard (stamp,slot,source,caller,target,loss,ber,duration,rssi) VALUES (%i,%i,'%s','%s','%s','%s','%s','%s','%s');\n"%(stamp,slot,source,caller,target,loss,ber,duration,rssi)
			elif table_name == 'dmr_history':
				#id,stamp,slot,state,source,caller,target,loss,ber,duration,rssi
				stamp = row[1]
				slot = row[2]
				state = row[3]
				source = row[4]
				caller = row[5]
				target = row[6]
				loss = row[7]
				ber = row[8]
				duration = row[9]
				rssi = row[10]
				sql += "INSERT INTO dmr_history (stamp,slot,state,source,caller,target,loss,ber,duration,rssi) VALUES (%i,%i,'%s','%s','%s','%s','%s','%s','%s','%s');\n"%(stamp,slot,state,source,caller,target,loss,ber,duration,rssi)
			else:
				return
		self.execute(sql)
		return


class db_handle(object):
	## db-Handler
	def __init__(self,type = 'sqlite'):
		if type == 'mysql':
			self.type = "MySQL"
			self.database = cfg.mysql_host
			self.writehistory = cfg.mysql_history
			self.cleardb = cfg.mysql_clear
			self.autoid = "AUTO_INCREMENT"
			try:
				self.conn = mc.connect(host = cfg.mysql_host, port = cfg.mysql_port, user = cfg.mysql_user, passwd = cfg.mysql_pass, db = cfg.mysql_db)
			except:
				cfg.log("[%s] database '%s' offline "%(self.type,self.database),'W')
				return
			self.prepare()
		else:
			self.type = "SQLite"
			self.database = cfg.sqlite_path
			self.writehistory = cfg.sqlite_history
			self.cleardb = cfg.sqlite_clear
			self.conn = sqlite3.connect(self.database, check_same_thread = False)
			self.autoid = ""
			self.prepare()
	
	def getcur(self):
		try:
			c = self.conn.cursor()
			return c
		except:
			cfg.log("[%s] database '%s' offline - trying reconnect"%(self.type,self.database),'W')
			try:
				self.conn = mc.connect(host = cfg.mysql_host, port = cfg.mysql_port, user = cfg.mysql_user, passwd = cfg.mysql_pass, db = cfg.mysql_db)
				c = self.conn.cursor()
				return c
			except:
				cfg.log("[%s] database '%s' still offline"%(self.type,self.database),'E')
				return None
	
	def prepare(self):
		cfg.log("[%s] prepare database '%s'"%(self.type,self.database))
		
		#c = self.conn.cursor()
		c = self.getcur()
		if c == None:
			return
		
		cfg.log("[%s] create if not exists 'dmr_lastheard'"%self.type,'D')
		dmrlh_cmd = '''CREATE TABLE IF NOT EXISTS dmr_lastheard (
			id INTEGER PRIMARY KEY %s,
			stamp INTEGER,
			slot INTEGER,
			source TEXT,
			caller TEXT,
			target TEXT,
			loss TEXT,
			ber TEXT,
			duration TEXT,
			rssi TEXT)'''%self.autoid
		c.execute(dmrlh_cmd)
		self.conn.commit()
		
		cfg.log("[%s] create if not exists 'dmr_state'"%self.type,'D')
		dmrstate_cmd = '''CREATE TABLE IF NOT EXISTS dmr_state (
			id INTEGER PRIMARY KEY %s,
			stamp INTEGER,
			slot INTEGER,
			state TEXT,
			source TEXT,
			caller TEXT,
			target TEXT,
			loss TEXT,
			ber TEXT,
			duration TEXT,
			rssi TEXT)'''%self.autoid
		c.execute(dmrstate_cmd)
		self.conn.commit()
		
		cfg.log("[%s] create if not exists 'dmr_history'"%self.type,'D')
		dmrhistory_cmd = '''CREATE TABLE IF NOT EXISTS dmr_history (
			id INTEGER PRIMARY KEY %s,
			stamp INTEGER,
			slot INTEGER,
			state TEXT,
			source TEXT,
			caller TEXT,
			target TEXT,
			loss TEXT,
			ber TEXT,
			duration TEXT,
			rssi TEXT)'''%self.autoid
		c.execute(dmrhistory_cmd)
		self.conn.commit()
		
		cfg.log("[%s] create if not exists 'state'"%self.type,'D')
		state_cmd = '''CREATE TABLE IF NOT EXISTS state (
			id INTEGER PRIMARY KEY %s,
			stamp INTEGER,
			varname TEXT,
			value TEXT)'''%self.autoid
		c.execute(state_cmd)
		self.conn.commit()
		
		cfg.log("[%s] create if not exists 'dmr_ids'"%self.type,'D')
		state_cmd = '''CREATE TABLE IF NOT EXISTS dmr_ids (
			id INTEGER PRIMARY KEY %s,
			caller TEXT,
			name TEXT)'''%self.autoid
		c.execute(state_cmd)
		self.conn.commit()

		if self.cleardb:
			cfg.log("[%s] clear 'dmr_lastheard'"%self.type,'W')
			c.execute("DELETE FROM dmr_lastheard;")
			c.execute("VACUUM;")
			self.conn.commit()
			cfg.log("[%s] clear 'dmr_history'"%self.type,'W')
			c.execute("DELETE FROM dmr_history;")
			c.execute("VACUUM;")
			self.conn.commit()
			cfg.log("[%s] clear 'dmr_state'"%self.type,'W')
			c.execute("DELETE FROM dmr_state;")
			c.execute("VACUUM;")
			self.conn.commit()
			cfg.log("[%s] clear 'state'"%self.type,'W')
			c.execute("DELETE FROM state;")
			c.execute("VACUUM;")
			self.conn.commit()
			cfg.log("[%s] clear 'dmr_ids'"%self.type,'W')
			c.execute("DELETE FROM dmr_ids;")
			c.execute("VACUUM;")
			self.conn.commit()
			
		cfg.log("[%s] prepare 'dmr_state'"%self.type,'D')
		stamp = int(time.time())
		c.execute("SELECT COUNT(*) FROM dmr_state WHERE slot = 1")
		if c.fetchone()[0] == 0 :
			c.execute("INSERT INTO dmr_state (stamp,slot,state,source,caller,target,loss,ber,duration,rssi) VALUES (%s, 1, 'idle', 'HOST', '', '', '', '', '', '')"%stamp)
			self.conn.commit()
		c.execute("SELECT COUNT(*) FROM dmr_state WHERE slot = 2")
		if c.fetchone()[0] == 0 :
			c.execute("INSERT INTO dmr_state (stamp,slot,state,source,caller,target,loss,ber,duration,rssi) VALUES (%s, 2, 'idle', 'HOST', '', '', '', '', '', '')"%stamp)
			self.conn.commit()
		
		c.close()
		return
	
	def dmrslotstate(self,stamp,slot,state = 'idle',source = '',call = '',target = '',loss = '',ber = '',duration = '',rssi = ''):
		#c = self.conn.cursor()
		c = self.getcur()
		if c == None:
			return

		stamp = str(int(stamp))
		if (call == '' and target == ''):
			cfg.log("[%s] complete qso 'dmr_state' (%s) %s > %s"%(self.type,slot,call,target),'D')
			c.execute("UPDATE dmr_state SET stamp = %s,state='%s',source='%s',loss='%s',ber='%s',duration='%s',rssi='%s' WHERE slot = %s"%(stamp,state,source,loss,ber,duration,rssi,slot))
		else:
			cfg.log("[%s] update 'dmr_state' (%s) %s > %s"%(self.type,slot,source,target),'D')
			c.execute("UPDATE dmr_state SET stamp = %s,state='%s',source='%s',caller='%s',target='%s',loss='%s',ber='%s',duration='%s',rssi='%s' WHERE slot = %s"%(stamp,state,source,call,target,loss,ber,duration,rssi,slot))
		self.conn.commit()
		c.close()
		
		# lookup and cache dmrids
		#if cfg.loaddmrids: find_dmrid(call)
		
		return
	
	def dmrlastheard(self,stamp,slot,state,source,call,target,loss='',ber='',duration='',rssi = ''):
		#c = self.conn.cursor()
		c = self.getcur()
		if c == None:
			return

		stamp = str(int(stamp))
		if call == '' and target == '':
			cfg.log("[%s] complete qso 'dmr_lastheard' (%s) %s > %s"%(self.type,slot,call,target),'D')
			c.execute("UPDATE dmr_lastheard SET loss='%s',ber='%s',duration='%s',stamp=%s,rssi='%s' WHERE source='%s' AND slot='%s' ORDER BY stamp DESC LIMIT 1"%(loss,ber,duration,stamp,rssi,source,slot))
			self.conn.commit()
		else:
			c.execute("SELECT COUNT(*) FROM dmr_lastheard WHERE stamp=%s AND slot=%s AND source='%s' AND caller='%s' AND target='%s'"%(stamp,slot,source,call,target))
			if c.fetchone()[0] == 0 :
				c.execute("SELECT COUNT(*) FROM dmr_lastheard WHERE caller = '%s'"%call)
				if c.fetchone()[0] == 0:
					cfg.log("[%s] add 'dmr_lastheard' (%s) %s > %s"%(self.type,slot,call,target),'D')
					c.execute("INSERT INTO dmr_lastheard (stamp,slot,source,caller,target,loss,ber,duration,rssi) VALUES (%s,%s,'%s','%s','%s','%s','%s','%s','%s')"%(stamp,slot,source,call,target,loss,ber,duration,rssi))
				else:
					cfg.log("[%s] update 'dmr_lastheard' (%s) %s > %s"%(self.type,slot,call,target),'D')
					c.execute("UPDATE dmr_lastheard SET stamp = %s,slot = %s,source='%s',caller='%s',target='%s',loss='%s',ber='%s',duration='%s',rssi='%s' WHERE caller = '%s'"%(stamp,slot,source,call,target,loss,ber,duration,rssi,call))
				self.conn.commit()
			else:
				cfg.log("[%s] duplicate entry 'dmr_lastheard' (%s) %s > %s"%(self.type,slot,call,target),'D')
		
		c.execute("SELECT COUNT(*) FROM dmr_history WHERE stamp=%s AND slot=%s AND source='%s' AND caller='%s' AND target='%s'"%(stamp,slot,source,call,target))	
		if self.writehistory and c.fetchone()[0] == 0:
			cfg.log("[%s] add 'dmr_history' (%s) %s > %s"%(self.type,slot,call,target),'D')
			if call == '' and target == '':
				try:
					c.execute("SELECT caller,target FROM dmr_history WHERE source='%s' AND slot='%s' ORDER BY stamp DESC LIMIT 1"%(source,slot))
					row = c.fetchone()
					call = row[0]
					target = row[1]
				except:
					pass
			c.execute("INSERT INTO dmr_history (stamp,slot,state,source,caller,target,loss,ber,duration,rssi) VALUES (%s,%s,'%s','%s','%s','%s','%s','%s','%s','%s')"%(stamp,slot,state,source,call,target,loss,ber,duration,rssi))
			self.conn.commit()
		else:
			cfg.log("[%s] duplicate entry 'dmr_history'"%self.type,'D')
		c.close()
		return
	
	def state(self,varname,value):
		#c = self.conn.cursor()
		c = self.getcur()
		if c == None:
			return

		stamp = str(int(time.time()))
		c.execute("SELECT COUNT(*) FROM state WHERE varname='%s'"%varname)
		if c.fetchone()[0] == 0:
			cfg.log("[%s] add 'state' %s > %s"%(self.type,varname,value),'D')
			c.execute("INSERT INTO state (stamp,varname,value) VALUES (%s,'%s','%s')"%(stamp,varname,value))
		else:
			cfg.log("[%s] update 'state' %s > %s"%(self.type,varname,value),'D')
			c.execute("UPDATE state SET stamp=%s,value='%s' WHERE varname='%s'"%(stamp,value,varname))
		self.conn.commit()
		c.close()
		return
	
	def store_dmrid(self,id,call,name):
		#c = self.conn.cursor()
		c = self.getcur()
		if c == None:
			return

		c.execute("SELECT COUNT(*) FROM dmr_ids WHERE id='%s'"%id)
		if c.fetchone()[0] == 0:
			cfg.log("[%s] add 'dmr_ids' %s: %s %s"%(self.type,id,call,name),'D')
			c.execute("INSERT INTO dmr_ids (id,caller,name) VALUES (%s,'%s','%s')"%(id,call,name))
		else:
			cfg.log("[%s] update 'dmr_ids' %s: %s %s"%(self.type,id,call,name),'D')
			c.execute("UPDATE dmr_ids SET caller='%s',name='%s' WHERE id=%s"%(call,name,id))
		self.conn.commit()
		c.close()
		return
	
	def last_stamp(self,table_name):
		c = self.getcur()
		if c == None: 
			return
		
		c.execute("SELECT stamp FROM %s ORDER BY stamp DESC LIMIT 1"%(table_name))
		return c.fetchone()[0]


##################
## DEFINE FUNCTIONS


#	Line-Parser
def line_parser(line,getStamp=False):
	#global MMDVMStatus
	
	me = threading.currentThread()
	cfg.log("[Parse] getting new line from logfile %s"%(me.filename),'D')
	line = line.rstrip("\n")
	
	if getStamp:
		Stamp = mt.MMDVMTime(line)
	else:
		Stamp = False
	
	if Stamp == False:
		Stamp = int(time.time())
	
	if mt.MMDVMHostState(line):
		hoststate = mt.MMDVMHostState(line)
		cfg.log("[Parse] MMDVMHost Version: %s"%(hoststate[0]),'D')
		cfg.log("[Parse] MMDVMHost State: %s"%(hoststate[1]),'D')
		MMDVM.set('HostVersion',hoststate[1])
		MMDVM.set('HostState',hoststate[0])
	
	if mt.MMDVMModes(line):
		modes = mt.MMDVMModes(line)
		cfg.log("[Parse] Mode: %s > %s"%(modes[0],modes[1]),'D')
		MMDVM.set('Mode_'+modes[0],modes[1])
	
	if mt.MMDVMHostBuilt(line):
		built = mt.MMDVMHostBuilt(line)
		cfg.log("[Parse] MMDVMHost built: %s"%(built),'D')
		MMDVM.set('HostBuilt',built)
	
	if mt.MMDVMVersion(line):
		version = mt.MMDVMVersion(line)
		cfg.log("[Parse] MMDVM Version: %s"%(version),'D')
		MMDVM.set('Version',version)
	
	if mt.MMDVMCallsign(line):
		callsign = mt.MMDVMCallsign(line)
		cfg.log("[Parse] DMR Call: %s"%(callsign),'D')
		MMDVM.set('Callsign',callsign)
	
	if mt.MMDVMId(line):
		id = mt.MMDVMId(line)
		cfg.log("[Parse] DMR id: %s"%(id),'D')
		MMDVM.set('Id',id)
	
	if mt.DMRMasterState(line):
		masterstate = mt.DMRMasterState(line)
		cfg.log("[Parse] DMR Master: %s"%(masterstate),'D')
		MMDVM.set('DMRMasterState',masterstate)
	
	if mt.DownlinkActive(line):
		cfg.log("[Parse] Downlink by %s"%mt.DownlinkActive(line),'D')
		pass
	
	if mt.DMRReflector(line):
		ref = mt.DMRReflector(line)
		cfg.log("[Parse] DMR Reflector: %s : %s"%(ref[0],ref[1]),'D')
		MMDVM.set('DMRSlot%sReflector'%ref[0],ref[1])
	
	if mt.DMRVoice(line):
		voice = mt.DMRVoice(line)
		slot = voice[0]
		cfg.log("[Parse] DMR Voice Slot: %s Source: %s Call: %s Target: %s"%(voice[0],voice[1],voice[2],voice[3]),'D')
		MMDVM.set('DMRSlot%s'%slot,'AKTIV')
		MMDVM.set('DMRSlot%sSource'%slot,voice[1])
		MMDVM.set('DMRSlot%sCall'%slot,voice[2])
		MMDVM.set('DMRSlot%sTarget'%slot,voice[3])
		MMDVM.set('DMRSlot%sStamp'%slot,Stamp)
		if cfg.sqlite_use:
			litedb.dmrslotstate(Stamp,slot,'AKTIV',voice[1],voice[2],voice[3])
			litedb.dmrlastheard(Stamp,slot,'start',voice[1],voice[2],voice[3])
		if cfg.mysql_use and not cfg.mysql_mirror:
			mydb.dmrslotstate(Stamp,slot,'AKTIV',voice[1],voice[2],voice[3])
			mydb.dmrlastheard(Stamp,slot,'start',voice[1],voice[2],voice[3])
	
	if mt.DMRData(line):
		voice = mt.DMRData(line)
		slot = voice[0]
		cfg.log("[Parse] DMR Data Slot: %s Source: %s Call: %s Target: %s"%(voice[0],voice[1],voice[2],voice[3]),'D')
		MMDVM.set('DMRSlot%s'%slot,'ENDE')
		MMDVM.set('DMRSlot%sSource'%slot,voice[1])
		MMDVM.set('DMRSlot%sCall'%slot,voice[2])
		MMDVM.set('DMRSlot%sTarget'%slot,voice[3])
		MMDVM.set('DMRSlot%sStamp'%slot,Stamp)
		if cfg.sqlite_use:
			litedb.dmrslotstate(Stamp,slot,'ENDE',voice[1],voice[2],voice[3],'','Data',voice[4])
			litedb.dmrlastheard(Stamp,slot,'end',voice[1],voice[2],voice[3],'','Data',voice[4])
		if cfg.mysql_use and not cfg.mysql_mirror:
			mydb.dmrslotstate(Stamp,slot,'ENDE',voice[1],voice[2],voice[3],'','Data',voice[4])
			mydb.dmrlastheard(Stamp,slot,'end',voice[1],voice[2],voice[3],'','Data',voice[4])
		
	if mt.DMRVoiceLost(line):
		voice = mt.DMRVoiceLost(line)
		slot = voice[0]
		cfg.log("[Parse] DMR VoiceLost Slot: %s Source: %s Duration: %s BER: %s"%(voice[0],voice[1],voice[2],voice[3]),'D')
		MMDVM.set('DMRSlot%s'%slot,'LOST')
		MMDVM.set('DMRSlot%sSource'%slot,voice[1])
		MMDVM.set('DMRSlot%sDuration'%slot,voice[2])
		MMDVM.set('DMRSlot%sBER'%slot,voice[3])
		MMDVM.set('DMRSlot%sStamp'%slot,Stamp)
		if cfg.sqlite_use:
			litedb.dmrslotstate(Stamp,slot,'LOST',voice[1],'','','',voice[3],voice[2])
			litedb.dmrlastheard(Stamp,slot,'lost',voice[1],'','','',voice[3],voice[2])
		if cfg.mysql_use and not cfg.mysql_mirror:
			mydb.dmrslotstate(Stamp,slot,'LOST',voice[1],'','','',voice[3],voice[2])
			mydb.dmrlastheard(Stamp,slot,'lost',voice[1],'','','',voice[3],voice[2])
	
	if mt.DMRVoiceEnd(line):
		voice = mt.DMRVoiceEnd(line)
		slot = voice[0]
		cfg.log("[Parse] DMR VoiceEnd Slot: %s Source: %s Duration: %s BER: %s Loss: %s RSSI: %s"%(voice[0],voice[1],voice[2],voice[3],voice[4],voice[5]),'D')
		MMDVM.set('DMRSlot%s'%slot,'ENDE')
		MMDVM.set('DMRSlot%sSource'%slot,voice[1])
		MMDVM.set('DMRSlot%sDuration'%slot,voice[2])
		MMDVM.set('DMRSlot%sBER'%slot,voice[3])
		MMDVM.set('DMRSlot%sLoss'%slot,voice[4])
		MMDVM.set('DMRSlot%sRSSI'%slot,voice[5])
		MMDVM.set('DMRSlot%sStamp'%slot,Stamp)
		if cfg.sqlite_use:
			litedb.dmrslotstate(Stamp,slot,'ENDE',voice[1],'','',voice[4],voice[3],voice[2],voice[5])
			litedb.dmrlastheard(Stamp,slot,'end',voice[1],'','',voice[4],voice[3],voice[2],voice[5])
		if cfg.mysql_use and not cfg.mysql_mirror:
			mydb.dmrslotstate(Stamp,slot,'ENDE',voice[1],'','',voice[4],voice[3],voice[2],voice[5])
			mydb.dmrlastheard(Stamp,slot,'end',voice[1],'','',voice[4],voice[3],voice[2],voice[5])
	
	if mt.DMRNetExpired(line):
		voice = mt.DMRNetExpired(line)
		slot = voice[0]
		cfg.log("[Parse] DMR VoiceLost Slot: %s Source: %s Duration: %s BER: %s Loss: %s"%(voice[0],voice[1],voice[2],voice[3],voice[4]),'D')
		MMDVM.set('DMRSlot%s'%slot,'ENDE')
		MMDVM.set('DMRSlot%sSource'%slot,voice[1])
		MMDVM.set('DMRSlot%sDuration'%slot,voice[2])
		MMDVM.set('DMRSlot%sBER'%slot,voice[3])
		MMDVM.set('DMRSlot%sLoss'%slot,voice[4])
		MMDVM.set('DMRSlot%sStamp'%slot,Stamp)
		if cfg.sqlite_use:
			litedb.dmrslotstate(Stamp,slot,'LOST',voice[1],'','',voice[4],voice[3],voice[2])
			litedb.dmrlastheard(Stamp,slot,'lost',voice[1],'','',voice[4],voice[3],voice[2])
		if cfg.mysql_use and not cfg.mysql_mirror:
			mydb.dmrslotstate(Stamp,slot,'LOST',voice[1],'','',voice[4],voice[3],voice[2])
			mydb.dmrlastheard(Stamp,slot,'lost',voice[1],'','',voice[4],voice[3],voice[2])
	
	if mt.DMRNetLateEntry(line):
		voice = mt.DMRNetLateEntry(line)
		slot = voice[0]
		cfg.log("[Parse] DMR VoiceLate Slot: %s Source: %s Call: %s Target: %s"%(voice[0],voice[1],voice[2],voice[3]),'D')
		MMDVM.set('DMRSlot%s'%slot,'AKTIV')
		MMDVM.set('DMRSlot%sSource'%slot,voice[1])
		MMDVM.set('DMRSlot%sCall'%slot,voice[2])
		MMDVM.set('DMRSlot%sTarget'%slot,voice[3])
		MMDVM.set('DMRSlot%sStamp'%slot,Stamp)
		if cfg.sqlite_use:
			litedb.dmrslotstate(Stamp,slot,'AKTIV',voice[1],voice[2],voice[3])
			litedb.dmrlastheard(Stamp,slot,'start',voice[1],voice[2],voice[3])
		if cfg.mysql_use and not cfg.mysql_mirror:
			mydb.dmrslotstate(Stamp,slot,'AKTIV',voice[1],voice[2],voice[3])
			mydb.dmrlastheard(Stamp,slot,'start',voice[1],voice[2],voice[3])
	
	return

#	LastLog-Finder
def log_find():
	me = threading.currentThread()
	me.logfile = ''
	error = False
	while getattr(me, "aktiv", True):
		try:
			lastmod = max(glob.iglob(cfg.mmdvm_log_path+'/'+cfg.mmdvm_log_prefix+'-*'), key=os.path.getctime)
			if lastmod != me.logfile:
				logfile.set(lastmod)
				me.logfile = lastmod
				cfg.log("[%s] changing logfile %s"%(me.name,me.logfile),'D')
			error = False
		except:
			if not error:
				cfg.log("[%s] ERROR while getting lastlogfile %s"%(me.name,me.logfile),'E')
				error = True
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
				cfg.log("[%s] registering logfile %s"%(me.name,me.logfile),'D')
				if cfg.parse:
					cfg.log("[%s_parse] start parsing whole file %s will take some time ..."%(me.name,me.logfile),'W')
					try:
						MMDVM.FullParse = True
						startat = time.time()
						with open(me.logfile, encoding="ISO-8859-1") as file_:
							## added encoding, because utf-8 failed
							MMDVM.set('Parsing_File',me.logfile)
							me.filename = me.logfile
							for line in file_:
								line_parser(line,True)
						endat = time.time()
					except:
						cfg.log("[%s_parse] error while parsing whole file %s"%(me.name,me.logfile),'E')
						raise
						print("Unexpected error:", sys.exc_info()[0])
					duration = str(int((endat-startat)*10)/10)

					MMDVM.FullParse = False
					MMDVM.set('Parsing_Duration',duration)

					cfg.log("[%s_parse] finished parsing whole file %s in %s seconds"%(me.name,me.logfile,duration),'D')
				log = tail.Tail(me.logfile,cfg,me.name)
				log.register_callback(line_parser)
				log.follow()
			except:
				cfg.log("[%s] error while initialising tail %s"%(me.name,me.logfile),'E')
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
	cfg.log("[MMDVM] flushing MMDVMState",'D')
	if not 'TimeStamp' in MMDVM.Status:
		MMDVM.Status['TimeStamp'] = time.time()
	
	for varname in MMDVM.Status:
		if cfg.sqlite_use:
			if (varname == 'TimeStamp'):
				value = str(int(MMDVM.Status[varname]))
			else:
				value = MMDVM.Status[varname]
			litedb.state(varname,value)
		if cfg.mysql_use and not cfg.mysql_mirror:
			if (varname == 'TimeStamp'):
				value = str(int(MMDVM.Status[varname]))
			else:
				value = MMDVM.Status[varname]
			mydb.state(varname,value)
		if cfg.state_use and (varname in cfg.state_vars):
			cfg.log("[PlainState] writing '%s' in '%s'"%(value,cfg.state_path+'/'+varname),'D')
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
		cfg.log("[mmdvm_ini] converting to MMDVMState")
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
		cfg.log("[dmrgateway_ini] converting to MMDVMState")
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
				cfg.log("[dmrids-dat] lookfor '%s' in '%s'"%(lookfor,cfg.sqlite_path),'D')
				for line in file:
					splitline = line.split()
					dmrid = splitline[0].decode('utf-8')
					usercall = splitline[1].decode('utf-8')
					try:
						username = splitline[2].decode('utf-8')
					except:
						username = ''
					if (lookfor == usercall) or (lookfor == dmrid):
						cfg.log("[dmrids-dat] copy line to '%s'"%cfg.sqlite_path)
						litedb.store_dmrid(dmrid,usercall,username)
		except:
			raise
			cfg.log("[dmrids-dat] error opening '%s'"%MMDVM.Status['DMRIdFile'],'E')
	return

##################
## PREPARE MAIN

#	load config before parsing arguments
cfg = conf()
MMDVM.Status['DMRGateway'] = cfg.dmrgateway_use
MMDVM.FullParse = False





#sys.exit()





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
	cfg.log("[CONF] reload from '%s'"%args.config,'W')
	cfg = conf(args.config)
if (args.mmdvm_config):
	cfg.log("[CONF] use MMDVMHost-Config from '%s'"%args.mmdvm_config,'W')
	cfg.mmdvm_ini = args.mmdvm_config
if (args.debug): 
	cfg.log("[CONF] set debug = True",'W')
	cfg.debug = True
if (args.nodebug): 
	cfg.log("[CONF] set debug = False",'W')
	cfg.debug = False
if (args.parse): 
	cfg.log("[CONF] set parse = True",'W')
	cfg.parse = True
if (args.noparse): 
	cfg.log("[CONF] set parse = False",'W')
	cfg.parse = False
if (args.sqlite_clear): 
	cfg.log("[CONF] set sqlite:clear = True",'W')
	cfg.sqlite_clear = True
if (args.nosqlite): 
	cfg.log("[CONF] disable sqlite (sqlite: use = False)",'W')
	cfg.sqlite_use = False

#	load sqlite
if cfg.sqlite_use:
	cfg.log("[MAIN] using SQLite '%s'"%cfg.sqlite_path)
	litedb = db_handle()

#	load mysql
if cfg.mysql_use:
	if cfg.mysql_mirror and cfg.sqlite_use:
		cfg.log("[MAIN] using MySQL '%s' in mirror-mode"%cfg.mysql_host)
		mydb = db_handle(type = 'mysql')
		t_dbmirror = threading.Thread(target=db_mirror, name='mysql-mirror')
		cfg.log("[MAIN] starting thread '%s'"%t_dbmirror.name,'D')
		t_dbmirror.start()
	else:
		cfg.log("[MAIN] using MySQL '%s' in direct-mode"%cfg.mysql_host)
		mydb = db_handle(type = 'mysql')

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
cfg.log("[MAIN] starting thread '%s'"%t_logfind.name,'D')
t_logfind.start()

t_tail = threading.Thread(target=tail_follow, name='Tail')
cfg.log("[MAIN] starting thread '%s'"%t_tail.name,'D')
t_tail.start()

notify = notify_changes(cfg,notify_vars)

if cfg.plainreader_use:
	plainreader = pr.plain_reader(cfg)

print("going to main loop ... in 10 seconds ...")
time.sleep(10)

while True:
	try:
		#cfg.log("[MAIN] current logfile is %s"%logfile.get())
		
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
			#os.system('clear')
			
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
		cfg.log("[MAIN] request QUIT by Keyboard",'W')
		t_logfind.aktiv = False
		t_logfind.join()
		t_tail.aktiv = False
		t_tail.join()
		notify.stop()
		if cfg.plainreader_use:
			plainreader.stop()
		if cfg.mysql_use and cfg.mysql_mirror:
			t_dbmirror.aktiv = False
			t_dbmirror.join()
		sys.exit(1)
		
	except:
		try:
			MMDVM.set('Parser','ENDE')
		except:
			pass
		cfg.log("[MAIN] QUIT after ERROR",'E')
		t_logfind.aktiv = False
		t_logfind.join()
		t_tail.aktiv = False
		t_tail.join()
		notify.stop()
		if cfg.plainreader_use:
			plainreader.stop()
		if cfg.mysql_use and cfg.mysql_mirror:
			t_dbmirror.aktiv = False
			t_dbmirror.join()
		raise
		sys.exit(0)
