#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# plain_reader
# read data from plainstate-files

import os,re,time,threading,sqlite3

class plain_reader(object):
	def __init__(self,cfg):
		self.cfg = cfg
		self.threads = {}
		self.active = True
		self.cfg.log('[plain_reader] START reader')
		if cfg.plainreader_use:
			for varname in cfg.plainreader.keys():
				self.threads[varname] = threading.Thread(target=self.monitor, args=(self,varname,cfg.plainreader[varname],))
				self.threads[varname].start()
		return
		
	def stop(self):
		self.cfg.log('[plain_reader] STOPPING threads')
		self.active = False
		for thread in self.threads.keys():
			self.cfg.log('[plain_reader] WAIT for thread %s'%(thread),'D')
			self.threads[thread].join()
	
	def monitor(self,caller,varname,options):
		self.cfg = caller.cfg
		self.data = ''
		self.cfg.log('[plain_reader] START monitoring %s'%(options['file']),'D')
		lastrun = 0
		while caller.active:
			if time.time() >= (lastrun + int(options['interval'])):
				self.data = self.update(varname,options['file'],options['type'])
				lastrun = time.time()
			time.sleep(1)
		self.cfg.log('[plain_reader] STOP monitoring %s'%(options['file']),'D')
		return
	
	def update(self,varname,plain_file,type = 'smart'):
		#type: force = send all data, smart = send changed data
		self.cfg.log('[plain_reader] CHECK %s'%(plain_file),'D')
		with open(plain_file,'r') as f:
			data = f.readline().strip()
			stamp = int(time.time())
			liteconn = sqlite3.connect(self.cfg.sqlite_path, check_same_thread = False)
			s_c = liteconn.cursor()
			s_c.execute("SELECT value FROM state WHERE varname LIKE '%s'"%(varname))
			db_data = s_c.fetchone()
			if db_data:
				if db_data[0] != data or type == 'force':
					s_c.execute("UPDATE state SET value = '%s',stamp = %s WHERE varname LIKE '%s'"%(data,stamp,varname))
					liteconn.commit()
					self.cfg.log('[plain_reader] data in %s updated: %s'%(varname,data),'D')
				else:
					self.cfg.log('[plain_reader] data in %s unchanged: %s'%(varname,db_data),'D')
			else:
				s_c.execute("INSERT INTO state (varname,value,stamp) VALUES ('%s','%s',%s)"%(varname,data,stamp))
				liteconn.commit()
				self.cfg.log('[plain_reader] data in %s inserted: %s'%(varname,db_data),'W')
			liteconn.close()
		return data
