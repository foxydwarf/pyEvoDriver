# -*- coding: utf-8 -*-
"""
Sample periodic transmitter w/ EvoLogics driver

Created on Mon Oct 12 16:18:46 2020

@author: paolo
"""
import socket
from time import sleep
from datetime import datetime as dt
from random import random as rand
from select import select

dataToSend = "This is your gateway, TX no."

expDuration = 58 # seconds

connCtrlModem = ("127.0.0.1",19188)

sockCtrlModem = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sockCtrlModem.connect(connCtrlModem)

sockCtrlModem.setblocking(False)

startTime = dt.now()
now = startTime

i=1

while (now - startTime).seconds < expDuration:
    sockCtrlModem.send("getreceptions\n".encode("utf-8"))
    r, w, x = select([sockCtrlModem],[],[], 0.0625)
    sleep(0.0625)
    if r != []:
        print( sockCtrlModem.recv(1500).decode("utf-8"), end="")
    sleep(0.5)
    if rand() > 0.75:
        print("Time: {} TX #{}: ".format(now.strftime("%Y-%d-%m %H:%M:%S"),i), end="")
        sockCtrlModem.send("txData,{},{} {:03d}\n".format((1 if rand()>0.5 else 4),dataToSend,i).encode("utf-8"))
        print("done.")
        i += 1
        sleep(1)
    now = dt.now()

sockCtrlModem.send("exit\n".encode("utf-8"))
sockCtrlModem.close()

