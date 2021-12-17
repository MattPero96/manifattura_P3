
# Lista variabili globali 

import json

def globalInitialization():
    global alive, listaStazioni, nTotStazioni, listaAGV#, listaGui
    alive = True

    nTotStazioni = [8,3,2]
    listaStazioni = [None]*3
    for j in range(3):
        listaStazioni[j] = [True]*(nTotStazioni[j]+1)
        
        
    listaAGV = []
    nListe = 3
    for i in range(nListe):
        l = []
        listaAGV.append(l)

    
