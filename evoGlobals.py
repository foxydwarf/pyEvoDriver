from socket import gethostname
from socket import gethostbyname

outputPrefix = "./output"

ipModem = "192.168.0.188"
portModem = 9200
modemAddr = (ipModem, portModem)

nodeID = 1
startPowerLevel = 3
extendedNotif = 1
bufferSize = 1500
readInterval = 0.25

localAddr = gethostbyname(gethostname())
localAddr = "127.0.0.1"
controlPort = 19188
ctrlAddr = (localAddr,controlPort)

modemDebugLevel = 0
modemDebugLevelFile = 4

modemDebugFile = outputPrefix + "/" + "modemDebugOutput.txt"
modemInitDebugFile = outputPrefix + "/" + "modemInitDebugOutput.txt"

maxModemReadAttempts = 4

selectTimeout = 0.0625