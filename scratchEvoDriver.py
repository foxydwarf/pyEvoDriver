# -*- coding: utf-8 -*-
"""
Scratch file for EvoLogics driver programming

Created on Wed Aug  5 10:26:57 2020

@author: Paolo Casari
@date: 12/10/2020
"""

import os
import sys
import socket
from time import sleep
from datetime import datetime as dt
from select import select
from collections import deque

import evoGlobals

# Socket to connect to modem
sockModem = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Buffer to store modem reports to be processed
modemReports = deque()

# Buffer to store commands from host
hostCommands = deque()

# Buffer to store received data packets for host
rxPackets = deque()



# State of the interpreter
stateINIT = -1
stateIDLE = 0
stateWAITFORRECVEND = 1
stateWAITFORRECVIM = 2
stateRECVIM = 3
stateRECVFAILED = 4
stateWAITFORSENDEND = 5

# Storage for all TRANSMITTED messages and status
txPacketData = list()

# Storage for all RECEIVED messages and status
rxPacketData = list()


def purgeSocket(sock):
    r, w, x = select([sock],[],[], evoGlobals.selectTimeout)
    while r != []:
        sock.recv(evoGlobals.bufferSize)
        r, w, x = select([sock],[],[], evoGlobals.selectTimeout)


def initModem():
    
    global sockModem
    global inState
    
    inState = stateINIT
    
    # Open debug file for modem init and write comments
    with open(evoGlobals.modemInitDebugFile, mode='w') as debugInitFile:
        now = dt.now()
        modemDebug("Connection to modem at {0}:{1} initiated at time {2} = {3}.\n".format(
            evoGlobals.ipModem, evoGlobals.portModem, dt.timestamp(now), now.strftime("%Y-%d-%m %H:%M:%S")),
            fh = debugInitFile, level = 0)
        
        # Open socket
        sockModem.connect(evoGlobals.modemAddr)
        sockModem.setblocking(False)
        
        # Purge socket receptions
        purgeSocket(sockModem)
        
        # TO MODEM: switch to command mode
        cmdModem = "+++ATC"
        sendCmdToModem(cmdModem, dbgFile=debugInitFile)
        sleep(0.75)
        if "OK" not in recvStrFromModem(dbgFile = debugInitFile):
            modemDebug("Modem did not accept command mode enabling command.\n", fh = debugInitFile, level = 0)
            sockModem.close()
            sys.exit()
        sleep(2)
        
        # Purge socket receptions
        purgeSocket(sockModem)

        # # TO MODEM: set power level
        # cmdModem = "AT!L" + str(evoGlobals.startPowerLevel)
        # sendCmdToModem(cmdModem, dbgFile = debugInitFile)
        # sleep(0.75)
        # if "OK" not in recvStrFromModem(dbgFile = debugInitFile):
        #     modemDebug("Modem did not accept power level setting command.\n", fh = debugInitFile, level = 0)
        #     sys.exit()
        # sleep(2)
    
        # Purge socket receptions
        purgeSocket(sockModem)

        # # TO MODEM: set node ID
        # cmdModem = "AT!AL" + str(evoGlobals.nodeID)
        # sendCmdToModem(cmdModem, dbgFile = debugInitFile)
        # sleep(0.75)
        # if "OK" not in recvStrFromModem(dbgFile = debugInitFile):
        #     modemDebug("Modem did not accept local address setting command.\n", fh = debugInitFile, level = 0)
        #     sys.exit()
        # sleep(2)
    
        # Purge socket receptions
        purgeSocket(sockModem)

        # TO MODEM: enable extended notifications
        cmdModem = "AT@ZX" + str(evoGlobals.extendedNotif)
        sendCmdToModem(cmdModem, dbgFile = debugInitFile)
        sleep(0.75)
        if "OK" not in recvStrFromModem(dbgFile = debugInitFile):
            modemDebug("Modem did not accept extended notification enabling command.\n", fh = debugInitFile, level = 0)
            sockModem.close()
            sys.exit()
        
        # Set driver state to idle
        inState = stateIDLE

def sendCmdToModem(cmdStr, dbgFile=None):
    global sockModem
    sockModem.send((cmdStr+"\n").encode("utf-8"))
    if dbgFile is not None:
        modemDebug("{0}::{1}::{2}\n".format(dt.timestamp(dt.now()), "TOMODEM", cmdStr), 
                   fh = dbgFile, level = 0)


def recvStrFromModem(dbgFile=None):
    global sockModem
    tryCount = 0
    strFromModem = None
    while tryCount < evoGlobals.maxModemReadAttempts:
        try:
            strFromModem = sockModem.recv(evoGlobals.bufferSize).decode("utf-8")
            # Purge "\r\n" and put "\n" instead
            if strFromModem.count("\r\n") != 0:
                strFromModem = strFromModem.replace("\r\n","\n")
            if dbgFile is not None:
                fullDbgStr = "{0}::{1}::".format(dt.timestamp(dt.now()), "FROMMODEM") + strFromModem.replace(
                    "\n","\n{0}::{1}::".format(dt.timestamp(dt.now()), "FROMMODEM"), strFromModem.count("\n")-1
                )
                modemDebug(fullDbgStr, fh = dbgFile, level = 0)
            return strFromModem
            break
        except BlockingIOError:
            # print("No data, retrying...")
            tryCount += 1
            sleep(0.25)
    if strFromModem is None:
        return ""


def prepareDebugFile():
    debugFile = open(evoGlobals.modemDebugFile, mode='w')
    now = dt.now()
    print("Connection to modem at {0}:{1} completed at time {2} = {3}.".format(
        evoGlobals.ipModem, evoGlobals.portModem, dt.timestamp(now), now.strftime("%Y-%d-%m %H:%M:%S") ),
        file = debugFile)
    return debugFile


def modemDebugToFile(strToPrint, fh, level=0):
    if evoGlobals.modemDebugLevelFile >= level:
        print(strToPrint, end="", file=fh)


def modemDebug(strToPrint, fh=None, level=0):
    global debugFile
    
    if evoGlobals.modemDebugLevel >= level:
        print(strToPrint,end="")
    modemDebugToFile(strToPrint, (fh if fh is not None else debugFile), level)
        

def ensureOutputPathExists():
    if not os.path.exists(evoGlobals.outputPrefix):
        os.mkdir(evoGlobals.outputPrefix)



def interpretModemReports():
    global modemReports
    global rxPackets
    global inState
    
    for iRep in range(len(modemReports)):
        currReport = modemReports.popleft().split(",");
        rep = currReport[0]
        
        if  rep == "OK":
            nextState = inState
        elif rep == "EXPIREDIMS":
            nextState = manageExpiredIms(currReport)
        elif rep == "SENDSTART":
            nextState = manageSendStart(currReport)
        elif rep == "SENDEND":
            nextState = manageSendEnd(currReport)
        elif rep == "RECVSTART":
            nextState = manageRecvStart(currReport)
        elif rep == "RECVEND":
            nextState = manageRecvEnd(currReport)
        elif rep == "RECVFAILED":
            nextState = manageRecvFailed(currReport)
        elif rep == "RECVIM":
            nextState = manageRecvIm(currReport)
        elif rep == "RECVIMS":
            nextState = manageRecvIms(currReport)
        elif rep == "CANCELEDIM":
            nextState = manageCanceledIm(currReport)
        else:
            nextState = inState
            # modemDebug("Undefined modem interpreter state\n", fh = debugFile, level = 0)
        inState = nextState
        
    else:
        modemReports.clear()


def manageCanceledIm(report):
    global inState
    nextState = inState
    return nextState

def manageCanceledIms(report):
    global inState
    strPkt = "{0}::{1}::{2}::{3}\n".format(dt.timestamp(dt.now()), "FROMMODEM", report[0], report[1])
    modemDebug(strPkt, level=0)
    nextState = inState
    return nextState

def manageExpiredIms(report):
    global inState
    strPkt = "{0}::{1}::{2}::{3}\n".format(dt.timestamp(dt.now()), "FROMMODEM", report[0], report[1])
    modemDebug(strPkt, level=0)
    nextState = inState
    return nextState

def manageRecvStart(report):
    global inState
    if inState == stateINIT:
        nextState = inState
    else:
        nextState = stateWAITFORRECVEND
    return nextState

def manageRecvEnd(report):
    # 1: timestamp;  2: duration;  3: RSSI;  4: integrity
    global inState
    if inState == stateINIT:
        nextState = inState
    elif inState == stateWAITFORRECVEND:
        nextState = stateWAITFORRECVIM
    return nextState

def manageRecvFailed(report):
    global inState
    if inState == stateINIT:
        nextState = inState
    elif inState == stateWAITFORRECVIM:
        nextState = stateIDLE
    else: #was: elif inState == stateWAITFORRECVEND:
        nextState = stateIDLE
    return nextState

def manageRecvIm(report):
    # 1: length;  2: fromID;  3: toID;  4: ack/noack;  5: duration;  
    # 6:RSSI;  7: integrity;  8: relative velocity;  9: payload
    global inState
    if inState == stateINIT:
        nextState = inState
    else: # was: elif inState == stateWAITFORRECVIM:
        nextState = stateIDLE
    recvdPktData = {
        "type":         "IM",
        "length":       report[1],
        "fromID":       report[2],
        "toID":         report[3],
        "ackFlag":      report[4],
        "duration":     report[5],
        "RSSI":         report[6],
        "integrity":    report[7],
        "relVelocity":  report[8],
        "payload":      report[9]
        }
    rxPacketData.append(recvdPktData)
    strPkt = "{0}::{1}::{2}::{3}::{4}::{5}::{6}::{7}::{8}::{9}::{10}::{11}\n".format(dt.timestamp(dt.now()),
        "FROMMODEM", report[0], report[1], report[2], report[3], report[4], report[5],
        report[6], report[7], report[8], report[9])
    modemDebug(strPkt, level=0)
    return nextState

def manageRecvIms(report):
    # 1: length;  2: fromID;  3: toID;  4: ack/noack;  5: duration;  
    # 6:RSSI;  7: integrity;  8: relative velocity;  9: payload
    global inState
    if inState == stateINIT:
        nextState = inState
    else: # was: elif inState == stateWAITFORRECVIM:
        nextState = stateIDLE
    recvdPktData = {
        "type":         "IMS",
        "length":       report[1],
        "fromID":       report[2],
        "toID":         report[3],
        "timestamp":    report[4],
        "duration":     report[5],
        "RSSI":         report[6],
        "integrity":    report[7],
        "relVelocity":  report[8],
        "payload":      report[9]
        }
    rxPacketData.append(recvdPktData)
    strPkt = "{0}::{1}::{2}::{3}::{4}::{5}::{6}::{7}::{8}::{9}::{10}::{11}\n".format(dt.timestamp(dt.now()),
        "FROMMODEM", report[0], report[1], report[2], report[3], report[4], report[5],
        report[6], report[7], report[8], report[9])
    modemDebug(strPkt, level=0)
    return nextState

def manageSendStart(report):
    global inState
    nextState = inState
    return nextState

def manageSendEnd(report):
    global inState
    nextState = inState
    return nextState



def interpretCommands():
    global inState
    global hostCommands
    global rxPackets
    global debugFile

    
    for iCmd in range(len(hostCommands)):
        currHostCmd = hostCommands.popleft().split(",")
        cmd = currHostCmd[0].lower()

        if cmd == "exit" or cmd == "quit":
            sockModem.send("ATO\n".encode("utf-8"))
            sockModem.close()
            sockCtrl.close()
            sCtrl.close()
            now = dt.now()
            modemDebug("Connections terminated, debug files closed at {0} = {1}.\n".format(
                dt.timestamp(now), now.strftime("%Y-%d-%m %H:%M:%S")),  level = 0)
            debugFile.close()
            sys.exit()

        elif cmd == "getclock":
            # Flush the reports from the modem
            r, w, x = select([sockModem],[],[], evoGlobals.selectTimeout)
            if r != []:
                strFromModem = recvStrFromModem(debugFile)
                strs = strFromModem.split("\n")
                # The below is probably unneeded
                if len(strs) == strFromModem.count("\r\n")+1:
                    strs = strFromModem.split("\r\n")
                # TODO::::Manage incomplete commands: check for last returned chunk '', store second to last chunk,
                # and merge with next command
                # AND CAREFUL in case the "\n" or "\r\n" should appear within an actual string to transmit!!!
                while strs.count('') != 0:
                    strs.remove('')
                modemReports.extend(strs)
            sockModem.send("AT?CLOCK\n".encode("utf-8"))
            sleep(0.05)
            currClockFromModem = recvStrFromModem(debugFile)
            currClock = currClockFromModem.split("\n")
            # The below is probably unneeded
            if len(currClock) == currClockFromModem.count("\r\n")+1:
                currClock = currClockFromModem.split("\r\n")
            currClock = currClock[0]
            sockCtrl.send((currClock+"\n").encode("utf-8"))
            if r != []:
                interpretModemReports()
            
        elif cmd == "getreceptions":
            # No parameters
            for i in range(len(rxPacketData)):
                rxType = rxPacketData[i]["type"]
                rxToSend = ("{}" + "".join([",{}" for i in range(9)])).format(
                    rxPacketData[i]["type"],
                    rxPacketData[i]["length"],
                    rxPacketData[i]["fromID"],
                    rxPacketData[i]["toID"],
                    (rxPacketData[i]["ackFlag"] if rxType=="IM" else rxPacketData[i]["timestamp"]),
                    rxPacketData[i]["duration"],
                    rxPacketData[i]["RSSI"],
                    rxPacketData[i]["integrity"],
                    rxPacketData[i]["relVelocity"],
                    rxPacketData[i]["payload"]
                )
                sockCtrl.send((rxToSend+"\n").encode("utf-8"))
            else:
                rxPacketData.clear()

        elif cmd == "txdata":
            # 1: recipient;  2: data bytes
            dataRecipient = currHostCmd[1]
            # Re-join strings that were separated due to commas in the text to send
            if len(currHostCmd) > 3:
                dataToSend = ','.join(currHostCmd[2:])
            else:
                dataToSend = currHostCmd[2]
            strToModem = "AT*SENDIM" + "," + str(len(dataToSend)) + "," + str(dataRecipient) + "," + "noack" + "," + dataToSend 
            sendCmdToModem(strToModem, dbgFile = debugFile)

        elif cmd == "txdataattime":
            # 1: timestamp;  2: recipient;  3: data bytes;
            timestampToSend = currHostCmd[1]
            dataRecipient = currHostCmd[2]
            if len(currHostCmd) > 4:
                dataToSend = ','.join(currHostCmd[3:])
            else:
                dataToSend = currHostCmd[3]
            strToModem = "AT*SENDIMS" + "," + str(len(dataToSend)) + "," + str(dataRecipient) + "," + str(timestampToSend) + "," + dataToSend 
            sendCmdToModem(strToModem, dbgFile = debugFile)

        else:
            pass
    else: 
        # At the end, clear the list
        hostCommands.clear()





#################################################
#        MAIN CYCLE OF THE DRIVER SCRIPT        #
#################################################

global debugFile

# Ensure output path exists
ensureOutputPathExists()

# Initialize modem according to parameters read from evoGlobals
initModem()

# Prepare debug file
debugFile = prepareDebugFile()

# Open control connection
sCtrl = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sCtrl.bind(evoGlobals.ctrlAddr)
sCtrl.listen(1)
sockCtrl, drvUser = sCtrl.accept()
now = dt.now()
modemDebug("Accepted connection to driver control from {0}:{1} at time {2} = {3}\n".format(
        *drvUser, dt.timestamp(now), now.strftime("%Y-%d-%m %H:%M:%S")))

# Set initial modem state
inState = stateIDLE

# Neverending socket reading loop
while True:

    # Check if something arrives from the modem
    r, w, x = select([sockModem],[],[], evoGlobals.selectTimeout)
    if r != []:
        strFromModem = recvStrFromModem(debugFile)
        strs = strFromModem.split("\n")
        if len(strs) == strFromModem.count("\r\n")+1:
            strs = strFromModem.split("\r\n")
        # TODO::::Manage incomplete commands: check for last returned chunk '', store second to last chunk,
        # and merge with next command
        # AND CAREFUL in case the "\n" or "\r\n" should appear within an actual string to transmit!!!
        while strs.count('') != 0:
            strs.remove('')
        modemReports.extend(strs)
        # Process according to state machine
        interpretModemReports()
        
    # Check if some command arrives from the device
    r, w, x = select([sockCtrl],[],[], evoGlobals.selectTimeout)
    if r != []:
        cmdFromHost = sockCtrl.recv(evoGlobals.bufferSize).decode("utf-8")
        cmds = cmdFromHost.split("\n")
        # TODO::::Manage incomplete commands: check for last returned chunk '', store second to last chunk,
        # and merge with next command
        # AND CAREFUL in case the "\n" or "\r\n" should appear within an actual string to transmit!!!
        while cmds.count('') != 0:
            cmds.remove('')
        hostCommands.extend(cmds)
        # Process according to state machine
        interpretCommands()
    
    # Insert some pause time here
    sleep(evoGlobals.readInterval)

    
# That's all folks
sockModem.send("ATO\n".encode("utf-8"))
sockModem.close()
sockCtrl.close()
sCtrl.close()
debugFile.close()

