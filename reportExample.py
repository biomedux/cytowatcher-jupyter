from __future__ import print_function
from ipywidgets import *
import ipywidgets as wg
from IPython.display import display
import time

import matplotlib
import numpy as np
import matplotlib.pyplot as plt

from datetime import datetime, timedelta

from os import listdir
from os.path import isfile, join
import re

import ast # string list to list
from firebase import firebase

firebase = firebase.FirebaseApplication("https://culturesystem-5f82b.firebaseio.com/")

timefmt = '%Y-%m-%d %H:%M:%S'
channels = []
freqs = []
period = 0
deadline = 0
begintime = 0
rid = 0 #no. record line
secs = []
z = []


# result Box
rptChk = []
label = []
for i in range(8):
	rptChk.append(wg.Checkbox(value = False, width = '30px', height = '30px'))
	label.append(wg.Label(value=str(i), width = '30px', height = '10px'))

rptChannels = wg.VBox( [ wg.HBox([label[i] for i in range (8)]), wg.HBox([rptChk[i] for i in range (8)]) ])

radioBtn = wg.RadioButtons(options=['Z','R', 'C'], value = 'Z', disabled = False)

selBtn = wg.Dropdown(options=[str(-i) for i in range(11)], value='0', disabled=False, button_style='', width='50px')

rptControls_layout = Layout(display='flex', flex_flow='row', justify_content='space-around', align_items='center')
rptControls = wg.Box([rptChannels, radioBtn, selBtn], layout=rptControls_layout)
display(rptControls)

fig = plt.figure(figsize=(9.5, 6), facecolor='w', edgecolor='k')
fig.suptitle('this is the figure title', fontsize=12)
ax = fig.add_subplot(1, 1, 1)
# ax.hold()
fig.show()

def plotdata():
	global channels, secs, rid, z
	fig.clear()
	ax = fig.add_subplot(1, 1, 1)
	# ax.hold(True)
	maxv = 0
	dval = 0
	for id in range(len(channels)):
		if (rptChk[channels[id]].value == True):
			res=[]

			for i in range(len(z)):
				ri = z[i][id][0].real
				ii = z[i][id][0].imag

				if radioBtn.value == 'Z':
					dval = np.sqrt(ri * ri + ii * ii)
				elif radioBtn.value == 'R':
					dval = ri
				else:
					w = 2 * np.pi * freqs[0]
					dval = -1 / (w * ii) * 1e9
				if maxv < dval: maxv = dval
				res.append(dval)

			ax.plot(secs, res)
			#print(id,len(secs),len(res))
	ax.axis([0, secs[-1], 0, maxv * 1.1]) # secs is already ready
	fig.show()

def gvarFromFile(fname):
	global channels, freqs, period, deadline, begintime, rid, secs, z

	# firebase
	MAX_EXP = firebase.get('/MAX_EXP', None)
	PATH = '/device_number/exp' + str(MAX_EXP)
	setupData = firebase.get(PATH + '/setup/', None)

	channels = setupData['channels']
	channels = ast.literal_eval(channels)
	nc = len(channels)	# number of channels

	freqs = setupData['freqs']
	freqs = ast.literal_eval(freqs)
	nf = len(freqs)		# number of freqs

	period = setupData['period']
	deadline = setupData['deadline']
	begintime = setupData['begintime']
	# print(channels, freqs, period, deadline, begintime)

	secs = []
	z = []
	data = firebase.get(PATH + '/dataCounter/', None)
	for x in data:
		checkTime = str(x).split('/')[1]
		tdelta = datetime.strptime(checkTime, timefmt) - datetime.strptime(begintime, timefmt)
		rsec = tdelta.days * 24 * 3600 + tdelta.seconds
		secs.append(rsec)

		impData = str(x).split('/')[0]
		impData = ast.literal_eval(impData)	# convert to complex type
		z.append(impData)
		# print(z)
	# firebase end

def on_file_change(change):
	global channels, freqs, period, deadline, begintime, rid, secs, z
	fid = -int(change['new'])
	#data file listup
	files = [f for f in os.listdir('.') if re.match('LabGCS', f)]
	files.sort(reverse=True)
	nof = len(files)
	selBtn.options = [str(-i) for i in range(nof)]
	fname = files[fid]
	#print(files)
	#print(fname)
	#now call globalsFromFile and plotdata------
	gvarFromFile(fname)
	# before doing this rptChk's are set
	for i in range(8):
		rptChk[i].disabled = True
		rptChk[i].value = False
	for ic in channels:
		rptChk[ic].disabled = False
		rptChk[ic].value = True
	plotdata()

def on_check_change(change):
	chk=[]
	for i in range(8):
		if rptChk[i].value == True:
			chk.append(i)
	#print(chk)
	plotdata()

def on_radio_change(change):
	plotdata()
	#print(change['new'])

#initially most recent data file open
change={'new': '0'}
on_file_change(change)
selBtn.observe(on_file_change, names='value')
for i in range(8):
	rptChk[i].observe(on_check_change, names='value')
radioBtn.observe(on_radio_change, names='value')
