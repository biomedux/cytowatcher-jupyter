# -*- coding:utf-8 -*-

import rpyc
import datetime, time, threading
import fileinput

from ctypes import *
from dwfconstants import *
import math
import time
import matplotlib.pyplot as plt
import sys

import fitSine as fs
import numpy as np
import copy

import dwf

import ast
from firebase.firebase import FirebaseApplication

#######
MODE = 'release' # 'debug', 'release'

firebase = FirebaseApplication("https://culture3-pso.firebaseio.com/")

# GUIDE
# -- firebase.put(path, key, value)
# -- firebase.get(path, None)

dataCounter = 0
exp = ''
timefmt = '%Y-%m-%d %H:%M:%S'

getData = 0
command = 0
deviceState = 'initializing'
recordState = 'off'
getSetup = {}
setupData = {
	'channels': 0,
	'freqs': 0,
	'period': 0,
	'deadline': 0,
	'experiment_name': 0,
}
pauseFlag = False

# initBaseForm = ['COMMAND', 'DEVICESTATE', 'RECORDSTATE', 'SETUP']
tryCount = 0

def initFirebase():
	print(" ### Firebase initializing")

	CONTROL = {'COMMAND': 0,
				'DEVICESTATE': 'ready',
				'RECORDSTATE': 'off',
				'SETUP': 0,
				'PAUSE': False,
				}

	firebase.put('/CONTROL', '/', CONTROL)

	# print(" ### Check Device Connect")
	# channels = range(8) # all channels
	# freqs = [4000] # default frequency
	# Z = dwf.measureImpedance(channels, freqs)
	#
	# if (Z == None):
	# 	print(" ### ERROR!! - CHECK CHIP FAILED")
	# 	return
	# else:
	# 	print(" ### Device Connect State - OK")

	print(" ### Init complete")

def monitorCommand():
	global getData
	global command
	global deviceState
	global recordState
	global getSetup
	global tryCount
	global firebase
	global pauseFlag

	tryCount += 1
	# 1000회 이상 파이어베이스에 접근하게되면 허용한계 초과로 에러나옴
	if (tryCount > 100):
		firebase = FirebaseApplication("https://culture3-pso.firebaseio.com/")
		tryCount = 0

	print("Monitoring.....")
	try:
		getData = firebase.get('/CONTROL', None)
	except Exception as e:
		print(e, type(e))
		monitorCommand()

	command = getData['COMMAND']
	deviceState = getData['DEVICESTATE']
	recordState = getData['RECORDSTATE']
	getSetup = getData['SETUP']
	pauseFlag = getData['PAUSE']

	if (command != 0):
		if (command == 'start'):
			print("## 'start' command receive")

			if (getSetup != 0):
				tempKeys = [str(x) for x in getSetup.keys()]

				if (deviceState != 'ready'):
					print("## Device state is not ready")
				elif (cmp(sorted(tempKeys), sorted(setupData.keys()))):
					print("## Setup form does not match.")
					print("  -- setup form : channels, freqs, period, deadline, experiment_name")
				else:
					setupData['channels'] = getSetup['channels']
					setupData['freqs'] = getSetup['freqs']
					setupData['period'] = getSetup['period']
					setupData['deadline'] = getSetup['deadline']
					setupData['experiment_name'] = getSetup['experiment_name']
					print("## Experiment setup - OK")

					firebase.put('/CONTROL', 'DEVICESTATE', 'running')
					conn=rpyc.connect('localhost',18861,config={'allow_pickle': True})
					conn.root.recording()

		elif (command == 'stop'):
			print("## 'stop' command receive")
			CS.finishRequest = True
			initFirebase()

			while(CS.finishRequest == True):
				pass
			print("  -- device is stopped")

		# TODO[1] : 디바이스에서 커맨드를 만지지 않고 서버쪽에서 만질수 있도록 수정해야함.
		command = 0
		firebase.put('/CONTROL', '/COMMAND', command)	# command reset

	# restart the timer
	threading.Timer(5, monitorCommand).start()

initFirebase()
monitorCommand()
dataCounter = 0

class CS(rpyc.Service):
	global getData
	global command
	global deviceState
	global getSetup
	global setupData

	finishRequest = False
	isBusy = False
	deadline = 0

	def recording(self):
		global dataCounter
		global recordState
		global pauseFlag
		global firebase
		global tryCount

		tryCount += 1
		if (tryCount > 100):
			firebase = FirebaseApplication("https://culture3-pso.firebaseio.com/")
			tryCount = 0

		if (recordState == 'off'):
			# recordState = 'on'	# 여기서 바꿔도 되나?
			firebase.put('/CONTROL', 'RECORDSTATE', 'on')
			cur = datetime.datetime.now()
			btime = cur.strftime(timefmt)

			if (MODE == 'debug'):
				CS.deadline = cur + datetime.timedelta(minutes = setupData['deadline']) # Release--when debugging, deadline = minutes, change to days
			else:
				CS.deadline = cur + datetime.timedelta(days = setupData['deadline']) # Release--when debugging, deadline = minutes, change to days
			# setupData['deadline'] = deadline
			print(setupData)

			firebase.put('/' + setupData['experiment_name'], 'setup', setupData)
			firebase.put('/' + setupData['experiment_name'] + '/setup', 'begintime', btime)

			# dictionary should be expanded because the dictionary seems unsafe
			self.saveMessage("Recording is started")
			print("recording start")
			dataCounter = 0

			time.sleep(5)

		if (pauseFlag):
			print(" ### PAUSE request arrived!")

			while (pauseFlag):
				print(" ## PAUSE")
				recordState = 'off'
				firebase.put('/CONTROL', 'RECORDSTATE', recordState)
				time.sleep(5)
			else:
				print(" ### UNPAUSE request arrived!")
				recordState = 'on'
				firebase.put('/CONTROL', 'RECORDSTATE', recordState)
				print(" ## UNPAUSE")

		now = datetime.datetime.now()
		# Release correction required
		if (now < CS.deadline) and (CS.finishRequest == False):
			if recordState == 'on':
				# measure(channels, Freqs) and recording
				channels = ast.literal_eval(setupData['channels'])
				freqs = ast.literal_eval(setupData['freqs'])
				CS.isBusy = True
				Z = dwf.measureImpedance(channels, freqs)

				cur = datetime.datetime.now()

				Z_list = []
				for ic in range(len(channels)):
					Z_list.append([Z[ic][0]])

				firebase.put('/' + setupData['experiment_name'] + '/data', str(dataCounter), str(Z_list) + '/' + str(cur.strftime(timefmt)))
				dataCounter += 1

				CS.isBusy = False
				print(cur)

			if (MODE == 'debug'):
				period = setupData['period'] * 1			# debug mode (sec)
			else:
				period = setupData['period'] * 60			# release mode (minute)

			t = threading.Timer(period, self.recording)
			t.start()
		else:
			if (now >= CS.deadline):
				self.saveMessage('deadline passed and finished!')
				print('deadline passed and finished!')
			if ( CS.finishRequest == True):
				self.saveMessage('finish request arrive finished!')
				print('finish request arrive finished!')
				CS.finishRequest = False

			firebase.put('/CONTROL', 'DEVICESTATE', 'ready')
			firebase.put('/CONTROL', 'RECORDSTATE', 'off')

	def saveMessage(self, msg):
		cur = datetime.datetime.now()
		firebase.put('/LOG', cur.strftime(timefmt), msg)

	def finish(self):
		if (recordState == 'on'):
			print('finish request arrived')
			CS.finishRequest = True
		else:
			self.saveMessage('finish request--Culture Server is not on recording!')
			print('finish request--Culture Server is not on recording!')

	def checkChip(self):
		global pauseFlag
		global deviceState

		if (pauseFlag == True or deviceState == 'ready'):
			print('check chip request arrived')
			channels = range(8) # all channels
			freqs = [4000] # default frequency
			Z = dwf.measureImpedance(channels, freqs)

			return Z
		else:
			# self.saveMessage('checkChip--Culture Server is on recording! Finish first')
			print('checkChip--Culture Server is on recording! Finish first')

	def measureImpedance(self, channel, freq):
		return dwf.measureImpedance([channel], [freq])

	def getScopeData(self, ch, fr):
		if recordState == 'off':
			print('scope data request arrived')
			CS.isBusy = True
			data0, data1 = dwf.getScopeData(ch, fr)
			CS.isBusy = False
			return data0, data1
		else:
			self.saveMessage('get scope data--Culture Server is on recording! Finish first')
			print('get scope data--Culture Server is on recording! Finish first')

if __name__ == "__main__":
	from rpyc.utils.server import ThreadedServer
	t = ThreadedServer(CS, port = 18861, protocol_config = {"allow_public_attrs": True, "allow_pickle": True})
	t.start()
