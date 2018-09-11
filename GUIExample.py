from __future__ import print_function
from ipywidgets import *
import ipywidgets as wg
from IPython.display import display
import time
from datetime import datetime, timedelta

import matplotlib
import numpy as np
import matplotlib.pyplot as plt
import rpyc

from IPython.display import Javascript

#system parameters
OPENRESISTANCE = 20e3
timefmt = '%Y-%m-%d %H:%M:%S'

def messageBox(msg):
  pre="""require(["base/js/dialog"],
  function(dialog) {
     dialog.modal({
         title: 'Message',
         body: '"""
  post="""',
         buttons: {
            'Bye': {}
                     }
                 });
             }) """
  data = pre+msg+post
  display(Javascript(data))

info = {
          'isPaused': False,
          'channels': [],
          'freqs': [],
          'period': 0,
          'deadline': 0,
          'begintime':0
}

conn=rpyc.connect('localhost',18861,config={'allow_pickle': True})

file = open("images/blue.png","rb")
blueLed = file.read()
file.close()
file = open("images/green.png","rb")
greenLed = file.read()
file.close()
file = open("images/red.png","rb")
redLed = file.read()
file.close()
chk = []
led = []

# <setup> Box
for i in range(8):
    chk.append(wg.Checkbox(value=False))
    led.append(wg.Image(value=redLed,width=30,height=30))
    
marea = wg.Textarea(
    value='',
    placeholder='Calibration is needed',
    description='$Z$:',
    disabled=False, width='250px', height='200px'
)

checks=wg.HBox( [wg.VBox([wg.HBox([led[i],chk[i]], width='100px') for i in range (4)]),
wg.VBox([wg.HBox([led[i],chk[i]]) for i in range (4,8)], width='100px')] )
setupBtn = wg.Button(description = 'Set Up', diable=False, button_style='')
checkBtn = wg.Button(description = 'Check', diable=False, button_style='')

h_centering = Layout(display='flex',
                    flex_flow='row',
                    justify_content='center',
                    align_items='center',
                    width='100%')

v_centering = Layout(display='flex',
                    flex_flow='column',
                    align_items='center')

mdatastr = ''
marea = wg.Textarea(
    value=mdatastr,
    placeholder='Type something',
    description='$Z$:',
    disabled=False, width='250px', height='200px'
)
checkBox = wg.Box([marea,checkBtn], layout=v_centering)
freqs=wg.Text(value='',description='freq\'s:', width='80%')
period=wg.Text(value='',description='period:', width='50%')
deadline=wg.Text(value='',description='deadline:', width='50%')
inputBox = wg.VBox([freqs,period,deadline])
vchiparea = wg.Box([checks,inputBox], layout=h_centering)
setupBox = wg.Box([vchiparea,setupBtn], layout=v_centering)
initBox = wg.HBox([checkBox,setupBox])

display(initBox)
sline = wg.HTML(value='<hr>')
display(sline)

def onSetupBtnClicked(b):
    #setRecordingInfo
    status=conn.root.getStatus()
    if status['isRecording']==True:
        messageBox('Please finish first!!')
        return
    if freqs.value == '':
       messageBox('freqs should have at least 1 freq!!')
       return
    if period.value == '':
       messageBox('period is empty!!')
       return
    if deadline.value == '':
       messageBox('deadline is empty')
       return
    noChk = 0
    chs = []
    for i in range(8):
       if chk[i].value == True: 
          noChk += 1
          chs.append(i)
    if noChk == 0:
       messageBox('at least 1 checkbox should be checked!!')
       return

    fr = (freqs.value).split(',')
    frs=[]
    for i in fr: frs.append(int(i)*1000) #frequencies in KHz when debug
    info['isPaused']=False
    info['channels']=chs
    info['freqs']=frs
    info['period']=int(period.value)
    info['deadline']=int(deadline.value)
    conn.root.setup(info)

def onCheckBtnClicked(b):
    status=conn.root.getStatus()
    if status['isRecording']==True:
        messageBox('Please finish first!!')
        return
    checkBtn.disabled=True
    #measure all channel and if imp < 100k change led to blueLed
    #and the measured R, C is written to marea
    Z=conn.root.checkChip()
    mdatastr = 'ch \t R \t \t C \n' 
    for i in range(8):
       R=Z[i][0].real
       w=2*np.pi*4e3
       C=1/(w*Z[i][0].imag)*1e9
       if R < OPENRESISTANCE:
          led[i].value = blueLed
          chk[i].value = True
          Rs = '%.1f'%R
          Cs = '%.1f'%-C
       else:    
          led[i].value = redLed
          chk[i].value = False
          Rs = '-'
          Cs = '-'
       mdatastr += str(i+1) +':\t'+Rs+'\t'+Cs+ '\n' 
    marea.value=mdatastr
    checkBtn.disabled=False

checkBtn.on_click(onCheckBtnClicked)
setupBtn.on_click(onSetupBtnClicked)
      

# <control> Box
infoBtn = wg.Button(description = 'info', disabled=False, button_style='',width='50%')
recordingBtn = wg.Button(description = 'recording', disabled=False, button_style='',width='50%')
pauseBtn = wg.Button(description = 'pause', disabled=False, button_style='',width='50%')
finishBtn = wg.Button(description = 'finish', disabled=False, button_style='',width='50%')
statusLed = wg.Image(value=redLed,width=50,height=50)
elapse=wg.Text(value='',description='elapse:',width='100%')

controlBox = wg.Box([statusLed, infoBtn, recordingBtn, pauseBtn, finishBtn, elapse], layout=h_centering)
display(controlBox)
display(sline)

def btnsMode(mode):
    if mode == 'idle':
        checkBtn.disabled = False
        setupBtn.disabled = False
        recordingBtn.disabled = False
        pauseBtn.disabled = True
        finishBtn.disabled = True
    else:
        checkBtn.disabled = True
        setupBtn.disabled = True
        recordingBtn.disabled = True
        pauseBtn.disabled = False
        finishBtn.disabled = False
   

def onInfoBtnClicked(b):
    status = conn.root.getStatus()
    msgBox.value='%s\n'%status
    rinfo = info.copy()
    rinfo = conn.root.getRecordingInfo()
    msgBox.value += '%s\n'%rinfo
    if status['isRecording']==True: 
        statusLed.value=blueLed
        cur = datetime.now()
        tdelta =datetime.strptime(cur.strftime(timefmt),timefmt)-datetime.strptime(rinfo['begintime'], timefmt)
        rsnds = tdelta.seconds
        hrs = rsnds/3600
        rsnds = rsnds - hrs*3600
        mins = rsnds/60
        rsnds = rsnds-mins*60
        estr=''
        if tdelta.days > 0: estr = str(tdelta.days)+' d '
        if hrs > 0: estr += str(hrs)+' h '
        if mins > 0: estr += str(mins)+' m'
        estr += str(rsnds)+' s'
        elapse.value = estr
        btnsMode('run')
    else: 
        statusLed.value=redLed
        btnsMode('idle')
    if rinfo['isPaused']==True: statusLed.value=greenLed
    for i in rinfo['channels']:
       chk[i].value = True
    frstr =''
    for i in rinfo['freqs']:
        frstr += '%s,'%(i/1000) # freq's in kHz when debug
    freqs.value = frstr[0:-1]
    period.value = str(rinfo['period'])
    deadline.value = str(rinfo['deadline'])

def onRecordingBtnClicked(b):
    status = conn.root.getStatus()
    if status['isRecording']==True:
       messageBox('Please finish first!!')
       return
    #disable all btn's except 'pause' and 'finish'
    btnsMode('run')
    conn.root.recording()       
    statusLed.value = blueLed

def onPauseBtnClicked(b):
    status = conn.root.getStatus()
    if status['isRecording']==False:
       messageBox('Culture Server is not on recording!!')
       return
    rinfo = conn.root.getRecordingInfo()
    if rinfo['isPaused'] == False:
        pauseBtn.description = 'resume'
        conn.root.pause()
        statusLed.value = greenLed
    else:
        pauseBtn.description = 'pause'
        conn.root.resume()
        statusLed.value = blueLed

def onFinishBtnClicked(b):
    status = conn.root.getStatus()
    if status['isRecording']==False:
       messageBox('Culture Server is not on recording!!')
       return
    #disable finish, pause       
    conn.root.finish()
    statusLed.value=redLed
    btnsMode('idle')

infoBtn.on_click(onInfoBtnClicked)
recordingBtn.on_click(onRecordingBtnClicked)
pauseBtn.on_click(onPauseBtnClicked)
finishBtn.on_click(onFinishBtnClicked)

#<Message Box>
msgBox = wg.Textarea(value='',descrition='',disabled=False, width='100%')
display(msgBox)

#initize the control pannel
status=conn.root.getStatus()
rinfo= conn.root.getRecordingInfo()
if status['isRecording']==True:
    if rinfo['isPaused']==True: statusLed.value=greenLed
    else: statusLed.value=blueLed
    btnsMode('run')
else:
    statusLed.value=redLed
    btnsMode('idle')
