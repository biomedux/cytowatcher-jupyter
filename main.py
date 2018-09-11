from firebase import firebase
import rpyc
import numpy as np
import ast
import threading


conn = rpyc.connect('localhost', 18861, config = {'allow_pickle': True})


DEVICE_NUMBER = '/Device_0/'	# device serial number

RecordingInfo = {
	'isPaused': False,
	'channels': [],
	'freqs': [],
	'period': 0,
	'deadline': 0
}

firebase = firebase.FirebaseApplication("https://culturesystem-5f82b.firebaseio.com/")
dataCounter = 0
exp = ''
getData = 0
getCommand = 0
deviceState = 'initializing'
recordState = 'record_off'
timefmt = '%Y-%m-%d %H:%M:%S'
cnt = 0

def monitorCommand():
	global getData
	global getCommand
	global deviceState
	global recordState
	global exp
	global cnt

	getData = firebase.get(DEVICE_NUMBER + '/', None)
	getCommand = getData['COMMAND']
	deviceState = getData['DeviceState']
	# recordState = getData['RecordState']
	setupData = getData['setup']
	cnt += 1

	if (getCommand != 0):
		if (getCommand == 'start'):
			if (deviceState == 'setup_ok'):
				max_exp = firebase.get(DEVICE_NUMBER + 'MAX_EXP', None)
				max_exp += 1
				firebase.put(DEVICE_NUMBER, 'MAX_EXP', max_exp)
				exp = 'exp' + str(max_exp)
				print('max_exp : ' + exp)

				firebase.put(DEVICE_NUMBER, 'DeviceState', 'running')
				print('recording start')
				conn.root.recording()

		elif (getCommand == 'stop'):
			conn.root.finish()

		elif (getCommand == 'setup'):
			channels = setupData['channels']
			channels = ast.literal_eval(channels)
			RecordingInfo['channels'] = channels

			freqs = setupData['freqs']
			freqs = ast.literal_eval(freqs)
			RecordingInfo['freqs'] = freqs

			period = setupData['period']
			RecordingInfo['period'] = period

			deadline = setupData['deadline']
			RecordingInfo['deadline'] = deadline

			conn.root.setup(RecordingInfo)
			print("setup ok")

		getCommand = 0
		firebase.put(DEVICE_NUMBER, '/COMMAND', getCommand)	# command reset

	# restart the timer
	threading.Timer(5, monitorCommand).start()

	print(cnt)

# monitorCommand()

if (__name__ == "__main__"):
	monitorCommand()

	while True:
		pass
