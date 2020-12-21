# -*- coding: utf-8 -*-
"""
Sample periodic transmitter w/ EvoLogics driver

Created on Mon Oct 12 16:18:46 2020

@author: paolo
"""
import socket
from time import sleep
from datetime import datetime as dt


numTX = 10
txDelay = 2
dataToSend = "Automatic TX from modem no."

connCtrlModem = ("127.0.0.1",19188)

sockCtrlModem = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sockCtrlModem.connect(connCtrlModem)

sockCtrlModem.setblocking(False)

for i in range(numTX):
    now = dt.now()
    print("Time: {} TX #{}: ".format(now.strftime("%Y-%d-%m %H:%M:%S"),i+1), end="")
    sockCtrlModem.send("txData,1,{} {:03d}\n".format(dataToSend,i+1).encode("utf-8"))
    print("done.")
    sleep(txDelay)

sockCtrlModem.send("exit\n".encode())
sockCtrlModem.close()

