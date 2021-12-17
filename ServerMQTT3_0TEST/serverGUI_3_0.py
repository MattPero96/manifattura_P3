
"""
********************************** ServerMQTT3.0 ************************************
- Software di gestione linee AGV, da abbinare a AGV_GUI_5.2
- Gestione logica SMEMA fra le stazioni
- Gestione blocco stazioni desiderate da SW supervisione IT
"""

import gvServer, MQTTdataHandler
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox
from PIL import ImageTk, Image
import os, signal, sys, time

SPR = 0
P1 = 1

gvServer.globalInitialization()
print(str(gvServer.listaStazioni[SPR]))
print(str(gvServer.listaStazioni[P1]))

###########################################################################################################
def bittatrice(data,bitshift,mask):
	outBit = (data >> bitshift) & mask
	return outBit

def stazioneCommand(scelta):
    gvServer.listaStazioni[SPR][scelta] = not gvServer.listaStazioni[SPR][scelta]

    
def stazioneCommandR(scelta):
    gvServer.listaStazioni[P1][scelta] = not gvServer.listaStazioni[P1][scelta]
    
def on_closing():
	global afterID
	if messagebox.askokcancel("Quit", "Do you want to quit?"):
		gvServer.alive = False
		# root.after_cancel(afterID)		
		while th.is_alive():
			th.join()

		root.destroy()

def updateGUI():
    for i in range(1,gvServer.nTotStazioni[SPR]+1):    
        if gvServer.listaStazioni[SPR][i]:
            b_stazioneLibera[i].configure(text="STAZIONE "+ str(i) + " LIBERA", bg = defaultbg, activebackground = defaultbg)
        else:
            b_stazioneLibera[i].configure(text="STAZIONE "+ str(i) + " OCCUPATA", bg = 'red', activebackground = 'red')
            l_fill[i-1].configure(image = pixel, height = 50)
            if (i-1) == 0:
                l_fill[5].configure(image = pixel, height = 50)
    
    for agv in gvServer.listaAGV[SPR]:
            if agv["isOn"]:
                if agv["inStation"]:
                    l_fill[agv["station"]].configure(image = pixel, height = 50)
                else:
                    l_fill[agv["station"]].configure(image = freccia,height=50)
                    if agv["station"] == 5:
                        l_fill[0].configure(image = freccia,height=50)

    for i in range(1,gvServer.nTotStazioni[P1]+1):    
        if gvServer.listaStazioni[P1][i]:
            b_stazioneLiberaR[i].configure(text="STAZIONE "+ str(i) + " LIBERA", bg = defaultbg, activebackground = defaultbg)
        else:
            b_stazioneLiberaR[i].configure(text="STAZIONE "+ str(i) + " OCCUPATA", bg = 'red', activebackground = 'red')
            l_fillR[i-1].configure(image = pixel, height = 50)
            if (i-1) == 0:
                l_fillR[3].configure(image = pixel, height = 50)
    
    for agv in gvServer.listaAGV[P1]:
        if agv["isOn"]:
            if agv["inStation"]:
                l_fillR[agv["station"]].configure(image = pixel, height = 50)
            else:
                l_fillR[agv["station"]].configure(image = freccia,height=50)
                if agv["station"] == 3:
                        l_fillR[0].configure(image = freccia,height=50)

    
    if gvServer.alive:
        afterID = root.after(30, updateGUI) # run itself again after 30 ms	
###########################################################################################################

root = tk.Tk()
root.title("SERVER AGV")
root.geometry('700x550')
defaultbg = root.cget('bg')
#root.attributes("-fullscreen", True)
root.protocol('WM_DELETE_WINDOW',on_closing)

pixel = tk.PhotoImage(width=1, height=1)
freccia = Image.open("arrow.png")
freccia = ImageTk.PhotoImage(freccia.resize((50,50), Image.ANTIALIAS))

frameLeft = tk.Frame(master=root)
frameRight = tk.Frame(master=root)
frameLeft.pack(side = tk.LEFT,fill = tk.BOTH, expand = 1)
frameRight.pack(side = tk.LEFT,fill = tk.BOTH, expand = 1)

b_stazioneLibera = [None]*(gvServer.nTotStazioni[SPR]+1)
l_fill = [None]*(gvServer.nTotStazioni[SPR]+1)
l_fill[0] = tk.Label(frameLeft,image = pixel, height = 50)
l_fill[0].pack()

for i in range(1,gvServer.nTotStazioni[SPR]+1):
    # print('Pulsante '+str(i))
    b_stazioneLibera[i] = tk.Button(frameLeft,text="STAZIONE "+str(i)+" LIBERA", width = 20,command=lambda n=i: stazioneCommand(n))# *args: 
    b_stazioneLibera[i].pack()#side=tk.BOTTOM)
    l_fill[i] = tk.Label(frameLeft,image = pixel, height = 50)
    l_fill[i].pack()

b_stazioneLiberaR = [None]*(gvServer.nTotStazioni[P1]+1)
l_fillR = [None]*(gvServer.nTotStazioni[P1]+1)
l_fillR[0] = tk.Label(frameRight,image = pixel, height = 50)
l_fillR[0].pack()

for i in range(1,gvServer.nTotStazioni[P1]+1):
    # print('Pulsante '+str(i))
    b_stazioneLiberaR[i] = tk.Button(frameRight,text="STAZIONE "+str(i)+" LIBERA", width = 20,command=lambda n=i: stazioneCommandR(n))# *args: 
    b_stazioneLiberaR[i].pack()#side=tk.BOTTOM)
    l_fillR[i] = tk.Label(frameRight,image = pixel, height = 50)
    l_fillR[i].pack()

# print("QUI")

th = MQTTdataHandler.threadServer()
th.start()

root.after(200,updateGUI)
root.mainloop()
pid = os.getpid()
os.kill(pid,signal.SIGTERM)
