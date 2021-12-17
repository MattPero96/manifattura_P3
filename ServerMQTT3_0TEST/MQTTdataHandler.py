import gvServer
import struct, types
import threading, time, json
import paho.mqtt.client as paho

SPR = 0
P1 = 1
P2 = 2


BROKER_IP           = '10.5.6.178'#'10.8.9.1'#"localhost"#
FROM_PLANT_BLOCK    = "fromPlant/blockStation"

FROM_AGV_STATE      = "fromAGV/state/#"
LEN_STATE           = len(FROM_AGV_STATE)-1
FROM_AGV_STATION    = "fromAGV/dataStation/#"
LEN_STATION         = len(FROM_AGV_STATION)-1
FROM_AGV_ORDER      = "fromAGV/setOrder/#"
LEN_ORDER           = len(FROM_AGV_ORDER)-1

# TO_AGV_STATE        = "toAGV/state/"
SERVER_ON           = "serverSwitchOn"
DELETE_AGV          = "deleteAGV"

AGV_ID          = 0
AGV_LINE        = 1
AGV_IS_ON       = 2
AGV_STARTED     = 3
AGV_STATION     = 4
AGV_IN_STATION  = 5
AGV_CHARGING    = 8

stateLock = [None]*3
stationLock = [None]*3
for i in range(3):
    stationLock[i] = threading.Lock()
    stateLock[i] = threading.Lock()

### UTILITIES #######################################################################################
#####################################################################################################
def bittatrice(data,bitshift,mask):
	outBit = (data >> bitshift) & mask
	return outBit

def areEqual(arr1,arr2):
    if len(arr1) != len(arr2):
        return False
    for i in range(0,len(arr1)):
        if arr1[i] != arr2[i]:
            return False
    return True

def getLineNum(text):
    out = -1
    if text == "SPR":
        out = SPR
    elif text == "P1":
        out = P1
    elif text == "P2":
        out = P2
    return out

def getLineStr(num):
    out = -1
    if num == SPR:
        out = "SPR"
    elif num == P1:
        out = "P1"
    elif num == P2:
        out = "P2"
    return out

def findAGV(name,line):
    out = -1
    count = 0
    for el in gvServer.listaAGV[line]:
        if el["name"] == name:
            out = count
            break
        count = count + 1 
    return out

### GESTIONE MESSAGGI ###############################################################################
#####################################################################################################
def on_connect(client, userdata, flags, rc):
    global connected_flag
    if rc==0:
        connected_flag = True #set flag
        print("Connesso a " + BROKER_IP)
        client.subscribe(FROM_AGV_STATE,qos=2)
        client.subscribe(FROM_AGV_STATION,qos=2)
        client.subscribe(FROM_PLANT_BLOCK,qos=2)
        client.subscribe(FROM_AGV_ORDER,qos=2)
        client.subscribe(DELETE_AGV,qos=2)
    else:
        print("Bad connection Returned code=",rc)

def on_disconnect(client, userdata, rc):
    global connected_flag
    connected_flag = False
    print("Disconnesso da " + BROKER_IP)

def on_message(client, userdata, message):
    topic = message.topic
    data = str(message.payload.decode())
    # data = json.loads(str(message.payload.decode()))
    # print("Nuovo messaggio da: " + topic)
    th = None
    if topic[:LEN_STATE] == FROM_AGV_STATE[:LEN_STATE]:
        th = threading.Thread(target=agvStateManager,args=(client,data))
    elif topic[:LEN_STATION] == FROM_AGV_STATION[:LEN_STATION]:
        th = threading.Thread(target=stationManager,args=(data,))
    elif topic[:LEN_ORDER] == FROM_AGV_ORDER[:LEN_ORDER]:
        th = threading.Thread(target=setOrder,args=(data,))
    elif topic == FROM_PLANT_BLOCK:
        th = threading.Thread(target=blockStation,args=(client,data))
    elif topic == DELETE_AGV:
        th = threading.Thread(target=deleteAgv,args=(client,data))
    
    if th is not None:
        th.start()

### ELABORAZIONE DATI ###############################################################################
#####################################################################################################
def stationManager(message):
    global lineStationBlock, stationLock
    AGVdata = json.loads(message)
    
    agvId = AGVdata["name"]
    lineStr = AGVdata["line"]
    line = getLineNum(lineStr)
    inStation = AGVdata["inStation"]    
    nStation = AGVdata["station"]       

    # print("Lista stazioni " +data[AGV_LINE] + ": " + str(data))
    gvServer.num = (nStation<<1)+(inStation)      
    #print("STAZIONE-> "+str(nStation))
    stationLock[line].acquire()
    if nStation > 0 and nStation <= gvServer.nTotStazioni[line]:
        if inStation == 1:
            gvServer.listaStazioni[line][nStation] = False
        else:
            gvServer.listaStazioni[line][nStation] = True
    stationLock[line].release()
    for agv in gvServer.listaAGV[line]:
        if agv["name"] == agvId:
            stateLock[line].acquire()
            agv["station"] = nStation
            agv["inStation"] = inStation
            stateLock[line].release()
            break
    # print(lineStr + str(lineStationBlock)+str(gvServer.listaStazioni[SPR][LP_LOCKED_STATION]))
    if (lineStationBlock[line][nStation]) and (gvServer.listaStazioni[line][nStation]):
        stationLock[line].acquire()
        gvServer.listaStazioni[line][nStation] = False
        stationLock[line].release()
  
def agvStateManager(client,message):
    global stateLock,stationLock
    AGVdata = json.loads(message)
    print("===============================================================================")
    print("Ricevuto stato:" + str(AGVdata))
    name = AGVdata["name"]
    lineStr = AGVdata["line"]
    lineNum = getLineNum(lineStr)
    isOn = AGVdata["isOn"]
    station = AGVdata["station"]
    inStation = AGVdata["inStation"]
    # charging = AGVdata["charging"]

    if isOn:
        thereIs = findAGV(name,lineNum)
        # print("There is: "+str(thereIs))   
        if thereIs != -1:            
            print("** C'era gia' **")
            if not gvServer.listaAGV[lineNum][thereIs]["isOn"]:
                print("Accensione OK")
                AGVfound = gvServer.listaAGV[lineNum][thereIs]
                if AGVfound["station"] == station and AGVfound["inStation"] == inStation:
                    print("Check stazione OK")
                else:
                    print("Check stazione fail")
                    stationLock[lineNum].acquire()
                    gvServer.listaStazioni[lineNum][AGVfound["station"]] = True
                    stationLock[lineNum].release()

                stateLock[lineNum].acquire()
                gvServer.listaAGV[lineNum][thereIs].update(AGVdata)
                stateLock[lineNum].release()

        else:
            print("** Non c'era **")
            # newAGV = gvServer.AGV(name,lineStr)
            # newAGV.copyValues(data)
            # # newAGV.started = True
            stateLock[lineNum].acquire()
            gvServer.listaAGV[lineNum].append(AGVdata)
            stateLock[lineNum].release()
        
        topic = "toAGV/state/" + lineStr + "/" + name
        client.publish(topic = topic, payload = "",qos=2)
    else:
        agv = findAGV(name,lineNum)
        if agv != -1:
            print("** Spegnimento "+ name +" **")
            stateLock[lineNum].acquire()
            # gvServer.listaAGV[lineNum][agv].isOn = False
            # gvServer.listaAGV[lineNum][agv].charging = charging
            gvServer.listaAGV[lineNum][agv].update(AGVdata)
            stateLock[lineNum].release()
            # gvServer.listaAGV[lineNum][agv].started = False
        else:
            print("ERROR not isOn + Nessun AGV")
    print("\n **LINEA PORTE**")
    for el in gvServer.listaAGV[SPR]:
        print(""  + str(el))

    # print("\n **LINEA P1**")
    # for el in gvServer.listaAGV[P1]:
    #     print(""  + str(el.toString()))

    print("===============================================================================\n")

def deleteAgv(client,message):
    data = json.loads(message)
    name = data[0]
    lineStr = data[1]
    lineNum = getLineNum(lineStr)
    for i in range(len(gvServer.listaAGV[lineNum])):
        if gvServer.listaAGV[lineNum][i]["name"] == name:
            station = gvServer.listaAGV[lineNum][i]["station"]
            stationLock[lineNum].acquire()
            gvServer.listaStazioni[lineNum][station] = True
            stationLock[lineNum].release()
            gvServer.listaAGV[lineNum].pop(i)
            break
    # print("===============================================================================")
    # print("AGGIORNAMENTO LISTA AGV IN " + lineStr)
    # for el in gvServer.listaAGV[lineNum]:
    #     print(el.toString())
    # print("===============================================================================\n")

def blockStation(client,message):
    global lineStationBlock, stationLock
    data = json.loads(message)
    lineStr = data["line"]
    lineNum = getLineNum(lineStr)
    station = data["station"]
    command = data["command"]
    
    if command == "block":
        lineStationBlock[lineNum][station] = True
    elif command == "free":
        lineStationBlock[lineNum][station] = False
    else:
        print("Messaggio di blocco stazione errato")

    if lineStationBlock[lineNum][station]:
        gvServer.listaStazioni[lineNum][station] = False
    else:
        if not gvServer.listaStazioni[lineNum][station]:
            toWrite = True
            for agv in gvServer.listaAGV[lineNum]:
                if agv["station"] == station:
                    toWrite = False
                    break
            gvServer.listaStazioni[lineNum][station] = toWrite
    
def setOrder(message):
    global stateLock
    data = json.loads(message)
    name = data["name"]
    lineStr = data["line"]
    lineNum = getLineNum(lineStr)
    odpCode = data["orderNumber"]
    prodName = data["productCode"]

    numAgv = findAGV(name=name,line=lineNum)
    if numAgv != -1:
        stateLock[lineNum].acquire()
        gvServer.listaAGV[lineNum][numAgv]["orderNumber"] = odpCode
        gvServer.listaAGV[lineNum][numAgv]["productCode"] = prodName
        stateLock[lineNum].release()
    else:
        print("Errore aggiornamento ordine")
    # print("===============================================================================")
    # print("AGGIORNAMENTO CODICE CARICATO IN " + lineStr)
    # for el in gvServer.listaAGV[lineNum]:
    #     print(el.toString())
    # print("===============================================================================\n")


### MAIN THREAD #####################################################################################
#####################################################################################################
class threadServer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        #self.alive = True

    def run(self):
        global lineStationBlock, stationLock, connected_flag

        lineStationBlock = [None]*3
        for j in range(3):
            lockList = [False]*(gvServer.nTotStazioni[j]+1)
            lineStationBlock[j] = lockList
        print(str(lineStationBlock))
        connected_flag = False
        while gvServer.alive:
            try:
                client = paho.Client(client_id = "SERVER SMEMA AGV")
                client.on_connect = on_connect
                client.on_disconnect = on_disconnect
                client.on_message = on_message
                client.loop_start()
                # print("Loop started")
                client.connect(BROKER_IP)
            except:
                print("Errore connessione")
            finally:

                while (not connected_flag):
                    time.sleep(1)

                # if not connected_flag:
                #     print("CONNESSIONE FALLITA")
                # else:
                print("AVVIO")
                
                client.publish(topic=SERVER_ON,payload="",qos=2)
                print("Inviata richiesta")
                precStatList = [False]*3
                for j in range(3):
                    stazioneLibera = [None]*(gvServer.nTotStazioni[j]+1)
                    for i in range(0,(gvServer.nTotStazioni[j]+1)):
                        stazioneLibera[i]  = True
                    precStatList[j] = stazioneLibera
                resend = False
                # countResend = 0
                # (gvServer.nTotStazioni[SPR]+1)

                print("Lista di partenza: " + str(gvServer.listaStazioni[SPR]))
                while gvServer.alive:
                    if connected_flag:
                        for line in range(0, len(gvServer.listaStazioni)):
                            if not areEqual(gvServer.listaStazioni[line], precStatList[line]) or resend:
                                stationLock[line].acquire()
                                dataSend = json.dumps(gvServer.listaStazioni[line])
                                topic = "toAGV/stationList/"+getLineStr(line)
                                # topic = "toAGV/"+getLineStr(line)+"/stationList"
                                # print("invio a: "+topic)
                                client.publish(topic = topic, payload = dataSend,qos=2,retain=True)
                                stationLock[line].release()
                                # print("Stazioni -> " + str(gvServer.listaStazioni[line]))
                                for i in range(0,len(precStatList[line])):
                                    precStatList[line][i] = gvServer.listaStazioni[line][i]
                        if resend:
                            # countResend = countResend + 1
                            resend = False
                    else:
                        
                        for i in range(0,len(gvServer.listaStazioni)):
                            for j in range(0,len(gvServer.listaStazioni[i])):
                                gvServer.listaStazioni[i][j]  = True 
                        resend = True
                        # countResend = 0
                    # if not areEqual(gvServer.listaStazioni[SPR], precStatList):
                    #     dataSend = json.dumps(gvServer.listaStazioni[SPR])
                    #     client.publish(topic = 'toAGV/SPR/stationList', payload = dataSend)
                    #     # print("Nuova lista -> " + str(gvServer.listaStazioni[SPR]))
                    #     for i in range(0,len(precStatList)):
                    #         precStatList[i] = gvServer.listaStazioni[SPR][i]
                
                client.unsubscribe(FROM_AGV_STATION)

                for lista in gvServer.listaStazioni:
                    for i in range(0,len(lista)):
                        lista[i] = True
                        # gvServer.listaStazioni[SPR][i]  = True
                
                dataSend = json.dumps(gvServer.listaStazioni[SPR])
                client.publish(topic = 'toAGV/stationList/SPR', payload = dataSend,qos=2,retain=True)

                dataSend = json.dumps(gvServer.listaStazioni[P1])
                client.publish(topic = 'toAGV/stationList/P1', payload = dataSend,qos=2,retain=True)

            client.loop_stop()
            print('Ciao ciao thread MQTT server')

# th = threadServer()
# th.start()       












