#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys
import os
os.chdir('/home/blue/model11')
os.environ["QT_QUICK_CONTROLS_STYLE"] = "Material"
os.environ["QT_IM_MODULE"] = "qtvirtualkeyboard"
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtQml import QQmlApplicationEngine
from PyQt5.QtCore import QThread, pyqtSignal, QObject, pyqtSlot, pyqtProperty, QPointF, QTimer
from PyQt5.QtChart import QXYSeries
import serial
import serial.tools.list_ports
import pandas as pd
import numpy as np
import time


#Golbal variables
#comment if emulator
number_of_channels = 8
#un comment if emulator with zapOF.csv
#number_of_channels = 2

#comment if emulator
number_of_channels_received = 8
#uncomment if emulator with zapOF.csv
#number_of_channels_received = 2

number_of_bytes = 18 + number_of_channels_received * 2
#number_of_samples = 2  #for baseline calculation of model9
number_of_samples = 429 #for baseline calculation of model 10
#model9 1/1000, model10 1/1000000
arrmultip = np.array([1,
                      1/1000000,
                      1/16,
                      0.1875*16.218/1000,
                      0.1875*-3.2353/1000,
                      0.1875*4.2353/1000,
                      0.1875/1000] + [-24/65535] * number_of_channels_received)

arrsum = np.array([0,0,0,0.1028,0,0,0]+[12]*number_of_channels_received)

globalda = b''

toffset = 0.15


#Classes

class RegulatingThread(QThread):
    voltagechanged = pyqtSignal(int, arguments=['voltagenow'])
    regulatefinished = pyqtSignal()

    def __init__(self):
        QThread.__init__(self)
        self._setvoltage = 40
        self._voltagenow = 4000

    @pyqtSlot(float)
    def setvoltage(self, value):
        print (value)
        self._setvoltage = value

    @pyqtSlot(float)
    def startregulating(self, value):
        print ('Start Regulating at %s' %value)
        self._setvoltage = value
        self.start()

    def __del__(self):
        self.wait()

    def run(self):
        self.stop = False
        print('Regulating')
        voltage = self._setvoltage
        print(voltage)
        print(type(voltage))
        device = list(serial.tools.list_ports.grep('ItsyBitsy M4'))[0].device
        ser = serial.Serial (device, 115200, timeout=1)
        texttosend = 'r%s,' %voltage
        ser.write(texttosend.encode())
        while True:
            try:
                lista2 = ser.readline().decode().strip().split(',')
                if len(lista2) == 6:
                    voltage1 = float(lista2[-1])
                    print ('lista2', lista2)
                    print ('voltage1', voltage1)
                    break
                else:
                    pass
            except:
                print ('listaerror')

        print (lista2)
        while not(self.stop):
            if ser.in_waiting:
                try:
                    lista = ser.readline().decode().strip().split(',')
                    if len(lista) == 6:
                        valuenow = float(lista[-1])
                        self.voltagechanged.emit(int(valuenow * 100))
                        print (lista)
                    else:
                        break
                except:
                    break

        print ('regulate finished')
        self.regulatefinished.emit()
        ser.write('n'.encode())
        ser.close()

    @pyqtSlot()
    def stopping(self):
        self.stop = True
        self.wait()
        self.quit()
        #print('measure stopoped')



class ReadingThread(QThread):

    def __init__(self):
        QThread.__init__(self)

    def __del__(self):
        self.wait()

    def run(self):
        global globalda
        self.stop = False

        #Prepare the file to store all data
        #Check if the file already exist, to prevent overwritting
        filenow = '%s.csv' %mysettingsw._filename
        filesindisk = os.listdir('rawdata')
        #is the file in the disk and it is not default.csv?
        if (filenow in filesindisk and filenow != 'default.csv'):
            n = 2
            pos = filenow.find('-')
            if pos != -1:
                originalname = filenow[:pos]
            else:
                originalname = mysettingsw._filename
            while filenow in filesindisk:
                filenow = '%s-%s.csv' %(originalname, n)
                n = n + 1
        #print ('file to store data will be: %s' %filenow)

        device = list(serial.tools.list_ports.grep('ItsyBitsy M4'))[0].device
        self.ser = serial.Serial (device, 115200, timeout=1)

        globalda = b''

        self.ser.write(b't')

        while not(self.stop):

            try:
                if self.ser.in_waiting:
                    inbytes = self.ser.read(self.ser.in_waiting)
                    globalda += inbytes
                    #print (globalda)

            except serial.serialutil.SerialException:
                 pass
            except OSError:
                pass

        #After stopping
        aa = np.ndarray((len(globalda)//number_of_bytes,number_of_bytes), np.uint8, globalda)
        ac = np.column_stack((aa[:,[0,4]] * 2**24 + aa[:,[1,5]] * 2**16 + aa[:,[2,6]] * 2**8 + aa[:,[3,7]],
                              2**8 + aa[:,9],
                              aa[:,10::2] * 2**8 + aa[:,11::2]))
        av1 = ac * arrmultip + arrsum
        av = av1[:,:7+number_of_channels]
        #remove first line bogus
        while av[0,0] > 10:
            av = av[1:,:]
        #av = av[2:,:]
        np.savetxt('rawdata/%s' %filenow, av, delimiter=',')


        #save datetime at the begining of the file
        with open('rawdata/%s' %filenow, 'r') as f:
            contents = f.readlines()
        contents.insert(0, 'date time: %s\n' %time.strftime('%d %b %Y %H:%M:%S'))
        #and the notes too
        contents.insert(1, 'Notes: %s\n' %mysettingsw._notes)

        #save rank at the begining of the file
        rankin = mysettingsw.readrank()
        contents.insert(2, 'Rank: %s\n' %rankin)

        #save number of sensors at begining of the file
        contents.insert(3, 'Number of sensors: %s\n' %number_of_channels)

        #save cartridge in option at beginign of file
        contents.insert(4, 'cartridge in: %s\n' %mysettingsw.cartridgeinlist[mycartridgew.allmemoryint[5]])

        #save functions of each channel at top of file
        contents.insert(5, 'ch0 function: %s\n' %myseries.functionsavailable[mycartridgew.allmemoryint[6]])
        contents.insert(6, 'ch1 function: %s\n' %myseries.functionsavailable[mycartridgew.allmemoryint[7]])
        contents.insert(7, 'ch2 function: %s\n' %myseries.functionsavailable[mycartridgew.allmemoryint[8]])
        contents.insert(8, 'ch3 function: %s\n' %myseries.functionsavailable[mycartridgew.allmemoryint[9]])
        contents.insert(9, 'ch4 function: %s\n' %myseries.functionsavailable[mycartridgew.allmemoryint[10]])
        contents.insert(10, 'ch5 function: %s\n' %myseries.functionsavailable[mycartridgew.allmemoryint[11]])
        contents.insert(11, 'ch6 function: %s\n' %myseries.functionsavailable[mycartridgew.allmemoryint[12]])
        contents.insert(12, 'ch7 function: %s\n' %myseries.functionsavailable[mycartridgew.allmemoryint[13]])


        #insert column names on top of the file
        lineofchannels = ','.join(['ch%s' %i for i in range(number_of_channels)])
        contents.insert(13, 'number,time,temp,PS0,-15V,15V,5V,%s\n' %lineofchannels)
        with open('rawdata/%s' %filenow, 'w') as f:
            contents = ''.join(contents)
            f.write(contents)


        #Find measurements lost
        measlost = (av[1:,0] - av[:-1,0] -1).sum()
        print ('Measurements lost: ', measlost)
        #Find monitor channel
        mchh = np.argmax(av[:,7:].max(axis=0))
        mch = 'ch%s' % mchh
        print ('Monitor channel: ', mch)


        #New way to calculate integrals
        #comment if emulator
        myseries.analyzemeasurements(av, rankin)


    def stopping(self):
        self.stop = True
        self.ser.close()
        self.wait()
        self.quit()
        #print('measure stopoped')


class DarkCurrentThread(QThread):

    ch0dcchanged = pyqtSignal(float, arguments=['ch0dcvalue'])
    ch1dcchanged = pyqtSignal(float, arguments=['ch1dcvalue'])
    ch2dcchanged = pyqtSignal(float, arguments=['ch2dcvalue'])
    ch3dcchanged = pyqtSignal(float, arguments=['ch3dcvalue'])
    ch4dcchanged = pyqtSignal(float, arguments=['ch4dcvalue'])
    ch5dcchanged = pyqtSignal(float, arguments=['ch5dcvalue'])
    ch6dcchanged = pyqtSignal(float, arguments=['ch6dcvalue'])
    ch7dcchanged = pyqtSignal(float, arguments=['ch7dcvalue'])
    darkcurrentend = pyqtSignal()

    def __init__(self):
        QObject.__init__(self)

    def __del__(self):
        self.wait()

    @pyqtSlot()
    def startdarkcurrent(self):
        self.start()


    def run(self):
        print("starting dark current subtraction")
        device = list(serial.tools.list_ports.grep('ItsyBitsy M4'))[0].device
        self.ser = serial.Serial (device, 115200, timeout=1)
        self.ser.write('s'.encode())
        for _ in range(3):
            line = self.ser.readline()
        self.stop = False
        listline = self.ser.readline().decode().strip().split(',')
        while not self.stop:
            try:
                listline = self.ser.readline().decode().strip().split(',')
            except (UnicodeDecodeError, TypeError):
                break
            print (listline)
            if listline[0] == '0':
                self.ch0dcchanged.emit(float(listline[-1]))
            elif listline[0] == '1':
                self.ch1dcchanged.emit(float(listline[-1]))
            elif listline[0] == '2':
                self.ch2dcchanged.emit(float(listline[-1]))
            elif listline[0] == '3':
                self.ch3dcchanged.emit(float(listline[-1]))
            elif listline[0] == '4':
                self.ch4dcchanged.emit(float(listline[-1]))
            elif listline[0] == '5':
                self.ch5dcchanged.emit(float(listline[-1]))
            elif listline[0] == '6':
                self.ch6dcchanged.emit(float(listline[-1]))
            elif listline[0] == '7':
                self.ch7dcchanged.emit(float(listline[-1]))

        self.darkcurrentend.emit()

    @pyqtSlot()
    def stopping(self):
       #self.stop = True
       self.ser.write('n'.encode())
       #self.ser.close()
       #self.wait()
       #self.quit()
       #print('terminado')



class UltraFastCommissioning(QObject):

    signalreadytoplot = pyqtSignal(list, arguments=['limits'])
    signallimits = pyqtSignal(list, list, arguments=['starttimes', 'finishtimes'])
    signalfullintegrals = pyqtSignal(list, arguments=['fullintegrals'])
    signalpartialintegrals = pyqtSignal(list, list, list, arguments=['sortedstarttimes', 'sortedfinishtimes','partialintegrals'])
    signalshowdialogerror = pyqtSignal(str, arguments=['textdialog'])
    signaltonotes = pyqtSignal(str, arguments=['notesfromfile'])
    signalpddfinished = pyqtSignal(list, arguments=['pddlimits'])

    def __init__(self):
        QObject.__init__(self)
        self._cerenkovch = 1
        self._sensorch = 0
        self._acr0 = 1
        self._calib0 = 1

    @pyqtSlot(int)
    def cerenkovchchange(self, chnumber):
        #print ('new Cerenkov channel is: ', chnumber)
        self._cerenkovch = chnumber
        if chnumber == 0:
            self._sensorch = 1
        else:
            self._sensorch = 0


    @pyqtSlot(int)
    def acr0change(self, newacr0):
        #print ('Then new ACR for pair 0 is: %.7f' %(newacr0/10000000))
        self._acr0 = newacr0/10000000

    @pyqtSlot(int)
    def calib0change(self, newcalib0):
        #print ('The new calib for pair 0 is: %.7f cGy/nC' %(newcalib0/10000000))
        self._calib0 = newcalib0/10000000

    @pyqtSlot(str)
    def openfile(self, filename):
        nrawdata = filename.find('rawdata')
        goodfilename = filename[nrawdata:]
        #check self.capacitor
        file = open(goodfilename)
        lines = file.readlines()[:20]
        file.close()
        #find lines to skip
        for n, line in enumerate(lines):
            if line.startswith('number,time'):
                lines_to_skip = n
        
        linerank = lines[2]
        rank = linerank[6]
        if rank == '0':
            self.capacitor = 30/1000
        elif rank == '1':
            self.capacitor = 60/1000

        #Check notes and send to GUI
        linenotes = lines[1]
        cleanlinenotes = linenotes[7:].replace(',','').replace('\n','')
        #self.signaltonotes.emit(cleanlinenotes)

        #Check integration time
        intline = lines[3]
        inttnow = int(intline[18:].strip())

        #Analyze data with Pandas
        df = pd.read_csv(goodfilename, skiprows=lines_to_skip)
        self.chmax = df.loc[:,'ch0':].max().idxmax()
        self.chmaxz = '%sz' %self.chmax
        #print ('ch max is: ', self.chmaxz)

        last_time = df.iloc[-1,1]
        zeros = df.loc[(df.time < 1)|(df.time > last_time - 1), 'ch0':].mean()
        dfchz = df.loc[:, 'ch0':] - zeros
        dfchz.columns = ['ch%sz' %i for i in range(number_of_channels)]
        dfz = pd.concat([df, dfchz], axis=1)

        maxvaluech = dfz.loc[(df.time < 2)|(df.time > last_time - 2), self.chmaxz].max()
        print ('max value of ', self.chmaxz, 'is ', maxvaluech)
        dfz['pulse'] = dfz[self.chmaxz] > maxvaluech * 1.05
        dfz.loc[dfz.pulse, 'pulsenum'] = 1
        dfz.fillna({'pulsenum':0}, inplace=True)
        dfz['pulsecoincide'] = dfz.loc[dfz.pulse, 'number'].diff() == 1
        dfz.fillna({'pulsecoincide':False}, inplace=True)

        dfz['chunk'] = dfz.number // int(300000/inttnow)
        dfz['chargesensor'] = dfz['ch%sz' %self._sensorch] * self.capacitor
        dfz['chargecerenkov'] = dfz['ch%sz' %self._cerenkovch] * self.capacitor
        dfz['chargedose'] = (dfz['ch%sz' %self._sensorch] - dfz['ch%sz' %self._cerenkovch] * self._acr0) * self.capacitor
        dfz['dosecgy'] = dfz.chargedose * self._calib0
        dfz['dosegy'] = dfz.dosecgy / 100
        dfz['singlepulse'] = dfz.pulse & ~dfz.pulsecoincide
        dfz['pulsetoplot'] = dfz.singlepulse * 0.10

        group = dfz.groupby('chunk')

        dfg = group.agg({'time':np.median,
                         'temp':np.mean, '5V':np.mean, 'PS':np.mean, '-15V':np.mean, '15V':np.mean,
                         'ch0z': np.sum,
                         'ch1z': np.sum,
                         'chargesensor':np.sum,
                         'chargecerenkov':np.sum})
        dfg['time_min'] = group['time'].min()
        dfg['time_max'] = group['time'].max()
        self.dfg = dfg
        self.dfz = dfz

        limits = [float(dfg.iloc[-1,0]),
                   float((dfg.loc[:,['chargesensor', 'chargecerenkov']]).max().max()),
                   float((dfz.loc[:,['chargesensor', 'chargecerenkov']]).max().max()),
                   float(dfg.temp.min()),
                   float(dfg.temp.max()),
                   float(dfg['5V'].min()),
                   float(dfg['5V'].max()),
                   float(dfg.PS.min()),
                   float(dfg.PS.max()),
                   float(dfg['-15V'].min()),
                   float(dfg['-15V'].max())]

        self.signalreadytoplot.emit(limits)

        listfullintegrals = dfz.loc[:,'chargesensor':'singlepulse'].sum().round(2).tolist()
        listfullintegralstosend = [float(i) for i in listfullintegrals]
        self.signalfullintegrals.emit(listfullintegralstosend)


    @pyqtSlot(QXYSeries, str, bool)
    def updateserie(self, serie, name, pulsestrue):
        if pulsestrue:
            dftoplot = self.dfz
        else:
            dftoplot = self.dfg
        pointstoreplace = [QPointF(x,y) for x, y in dftoplot.loc[:,['time',name]].values]
        serie.replace(pointstoreplace)

    @pyqtSlot(list, list, str, str)
    def calcpdd(self, starttimes, finishtimes, depth, dmax):
        try:
            sts = [i for i in starttimes if i != -1]
            fts = [j for j in finishtimes if j != -1]
            sts.sort()
            fts.sort()
            if len(sts) != 2 or len(fts) != 2:
                raise ValueError
            print ('First zero: ', sts[0])
            print ('secnod zero: ', fts[1])
            print ('PDD starts at: ', sts[1])
            print ('PDD ends at: ', fts[0])
            print ('PDD depth: ', depth)
            print ('dmax: ', dmax)
            t1z = sts[0]
            t2z = fts[1]
            st = sts[1]
            fn = fts[0]
            intdepth = int(depth)
            intdmax = int(dmax)
            vel = intdepth/(fn - st)
            print ('Estimated speed: %s mm/s' %vel)
            meanzeros = self.dfz.loc[(self.dfz.time < t1z)|(self.dfz.time > t2z), ['ch0', 'ch1']].mean()
            self.dfz.loc[:, ['ch0z', 'ch1z']] = (self.dfz.loc[:,['ch0', 'ch1']] - meanzeros).values
            maxvaluech = self.dfz.loc[(self.dfz.time < t1z )|(self.dfz.time > t2z), self.chmaxz].max()
            print ('max value of ', self.chmaxz, 'is ', maxvaluech)
            self.dfz['pulse'] = self.dfz[self.chmaxz] > maxvaluech * 1.5
            self.dfz.loc[self.dfz.pulse, 'pulsenum'] = 1
            self.dfz.fillna({'pulsenum':0}, inplace=True)
            self.dfz['pulsecoincide'] = self.dfz.loc[self.dfz.pulse, 'number'].diff() == 1
            self.dfz.fillna({'pulsecoincide':False}, inplace=True)
            self.dfz['chargesensor'] = self.dfz['ch%sz' %self._sensorch] * self.capacitor
            self.dfz['chargecerenkov'] = self.dfz['ch%sz' %self._cerenkovch] * self.capacitor
            self.dfz['chargedose'] = (self.dfz['ch%sz' %self._sensorch] - self.dfz['ch%sz' %self._cerenkovch] * self._acr0) * self.capacitor
            self.dfz['dosecgy'] = self.dfz.chargedose * self._calib0
            self.dfz['dosegy'] = self.dfz.dosecgy / 100
            self.dfz['singlepulse'] = self.dfz.pulse & ~self.dfz.pulsecoincide
            self.dfz['pulsetoplot'] = self.dfz.singlepulse * 0.10

            self.dfz['timediff'] = self.dfz.time.diff()
            self.dfz['distance'] = self.dfz.timediff * vel
            self.dfz['pos1'] = self.dfz.distance.cumsum()

            self.dfn = self.dfz.loc[(self.dfz.time > st) & (self.dfz.time < fn), :].copy()
            self.dfn['pos'] = -self.dfn.pos1 + intdepth

            samplespermm = int(1/(self.dfn.timediff.mean() * vel))
            print ('samples per mm: ', samplespermm)
            self.dfn['chunk'] = self.dfn.number // samplespermm
            self.dfg = self.dfn.groupby('chunk').agg({'time':np.median, 'pos':np.median, 'chargedose':np.sum}).reset_index()
            self.dfg = self.dfg.iloc[1:-1]
            posmaxnow = self.dfg.loc[self.dfg.chargedose == self.dfg.chargedose.max(), 'pos'].item()
            print ('Dmax now: ', posmaxnow)
            diffmax = intdmax - posmaxnow
            self.dfn['posg'] = self.dfn.pos + diffmax
            self.dfg['posg'] = self.dfg.pos + diffmax
            self.dfg['dosenorm'] = self.dfg.chargedose / self.dfg.chargedose.max() * 100
            self.dfg['dosesoft'] = self.dfg.chargedose.rolling(window=4, center=True).sum() #this is the rolling average
            self.dfg['dosesoftnorm'] = self.dfg.dosesoft / self.dfg.dosesoft.max() * 100
            print (self.dfg.head())
            pddlimits = [float(self.dfn.posg.min()),
                         float(self.dfn.posg.max()),
                         float(self.dfn.chargedose.min()),
                         float(self.dfg.dosesoftnorm.min()),
                         float(self.dfn.chargedose.max())]
            self.signalpddfinished.emit(pddlimits)



        except ValueError:
            self.signalshowdialogerror.emit('Not the right startimes finishtimes')


    @pyqtSlot(QXYSeries, bool)
    def updatepdd(self, serie, pulsestrue):
        if pulsestrue:
            pointstoreplace = [QPointF(x,y) for x, y in self.dfn.loc[:,['posg','chargedose']].values]
        else:
            pointstoreplace = [QPointF(x,y) for x, y in self.dfg.loc[:,['posg','dosesoftnorm']].values]
        serie.replace(pointstoreplace)

class AnalyzeWindow(QObject):

    signalreadytoplot = pyqtSignal(list, arguments=['limits'])
    signallimits = pyqtSignal(list, list, arguments=['starttimes', 'finishtimes'])
    signalfullintegrals = pyqtSignal(list, arguments=['fullintegrals'])
    signalpartialintegrals = pyqtSignal(list, list, list, arguments=['sortedstarttimes', 'sortedfinishtimes','partialintegrals'])
    signalshowdialogerror = pyqtSignal(str, arguments=['texterror'])
    signalnumberofchannelsfromfile = pyqtSignal(int, arguments=['numberofchannels'])
    signalcartridgeinselected = pyqtSignal(int, arguments=['cartridgeinselected'])

    def __init__(self):
        QObject.__init__(self)
        self.pulseschecked = True
        self.chargechecked = True
        self.chargedosechecked = False
        self.dosechecked = False
        self.grayschecked = False
        self.centygrayschecked = True
        self._cutoff = 20
        self.sensors = ['ch%s' %i for i in range(0,number_of_channels,2)]
        self.sensorsi = [i for i in range(0, number_of_channels, 2)]
        self.cerenkovs = ['ch%s' %i for i in range(1, number_of_channels,2)]
        self.cerenkovsi = [i for i in range(1, number_of_channels,2)]
        self.acrs = [1 for i in range(int(number_of_channels/2))]
        self.capacitor = 1.8
        self.calibs = [0.5 for i in range(int(number_of_channels/2))]

        #functions available must be equal to list of functions in qml
        self.functionsavailable = ['N/A', 'sensor0', 'cerenkov0', 'sensor1', 'cerenkov1', 'sensor2', 'cerenkov2', 'sensor3',
                                  'cerenkov3', 'sensor4', 'sensor5', 'sensor6', 'sensor7']
        self.listfunctions = ['N/A'] * 8

    @pyqtSlot(int)
    def cutoffchange(self, currentindex):
        cutoffvalues = [0.5, 10, 20, 40, 100, 150]
        self._cutoff = cutoffvalues[currentindex]
        print ('cutoff now is: %s' %self._cutoff)

    @pyqtSlot(int)
    def sensor0change(self, chnumber):
        self.sensorsi[0] = chnumber
        self.sensors[0] = 'ch%s' %chnumber
        print ('Sensor 0 channel is now: ', 'ch%s' %chnumber)

    @pyqtSlot(int)
    def sensor1change(self, chnumber):
        self.sensorsi[1] = chnumber
        self.sensors[1] = 'ch%s' %chnumber

    @pyqtSlot(int)
    def sensor2change(self, chnumber):
        self.sensorsi[2] = chnumber
        self.sensors[2] = 'ch%s' %chnumber

    @pyqtSlot(int)
    def sensor3change(self, chnumber):
        self.sensorsi[3] = chnumber
        self.sensors[3] = 'ch%s' %chnumber

    @pyqtSlot(int)
    def cerenkov0change(self, chnumber):
        self.cerenkovsi[0] = chnumber
        self.cerenkovs[0] = 'ch%s' %chnumber

    @pyqtSlot(int)
    def cerenkov1change(self, chnumber):
        self.cerenkovsi[1] = chnumber
        self.cerenkovs[1] = 'ch%s' %chnumber

    @pyqtSlot(int)
    def cerenkov2change(self, chnumber):
        self.cerenkovsi[2] = chnumber
        self.cerenkovs[2] = 'ch%s' %chnumber

    @pyqtSlot(int)
    def cerenkov3change(self, chnumber):
        self.cerenkovsi[3] = chnumber
        self.cerenkovs[3] = 'ch%s' %chnumber


    @pyqtSlot(int)
    def acr0change(self, newacr):
        self.acrs[0] = newacr/10000000

    @pyqtSlot(int)
    def acr1change(self, newacr):
        self.acrs[1] = newacr/10000000

    @pyqtSlot(int)
    def acr2change(self, newacr):
        self.acrs[2] = newacr/10000000

    @pyqtSlot(int)
    def acr3change(self, newacr):
        self.acrs[3] = newacr/10000000

    @pyqtSlot(int)
    def calib0change(self, newcalib):
        self.calibs[0] = newcalib/10000000

    @pyqtSlot(int)
    def calib1change(self, newcalib):
        self.calibs[1] = newcalib/10000000

    @pyqtSlot(int)
    def calib2change(self, newcalib):
        self.calibs[2] = newcalib/10000000

    @pyqtSlot(int)
    def calib3change(self, newcalib):
        self.calibs[3] = newcalib/10000000

    @pyqtSlot(bool)
    def pulsescheck(self, checked):
        self.pulseschecked = checked
        print ('pulses button is now: ', checked)

    @pyqtSlot(bool)
    def chargecheck(self, checked):
        self.chargechecked = True
        self.chargedosechecked = False
        self.dosechecked = False
        print ('chargedose button is now: ', checked)

    @pyqtSlot(bool)
    def chargedosecheck(self, checked):
        self.chargechecked = False
        self.chargedosechecked = True

        self.dosechecked = False
        print ('chargedose button is now: ', checked)

    @pyqtSlot(bool)
    def dosecheck(self, checked):
        self.chargechecked = False
        self.chargedosechecked = False
        self.dosechecked = True
        print ('dose button is now: ', checked)

    @pyqtSlot(bool)
    def grayscheck(self, checked):
        self.grayschecked = checked
        self.centygrayschecked = not(checked)
        print ('grays button is now: ', checked)

    @pyqtSlot(bool)
    def centygrayscheck(self, checked):
        self.centygrayschecked = checked
        self.grayschecked = not(checked)
        print ('centygrays button is now: ', checked)

    @pyqtSlot()
    def renewvalues(self):
        if (self.chargechecked and not(self.pulseschecked)):
            listtosend = self.fullintcharge
            listtosend.append(self.totalpulses)
            self.signalfullintegrals.emit(listtosend)
            self.signalpartialintegrals.emit(self.listpartialintegralscharge)

        elif (self.chargedosechecked and not(self.pulseschecked)):
            listtosend = []
            for a in self.fullintchargedose:
                listtosend.append(a)
                listtosend.append('--')
            listtosend.append(self.totalpulses)
            self.signalfullintegrals.emit(listtosend)
            partialstosend = self.listpartialintegralschargedose
            for i in range(len(partialstosend)):
                for j in range(1,8,2):
                    partialstosend[i].insert(j, '--')
            self.signalpartialintegrals.emit(partialstosend)


        elif (self.dosechecked and not(self.pulseschecked)) and self.centygrayschecked:
            listtosend = []
            for a in self.fullintdosecentygrays:
                listtosend.append(a)
                listtosend.append('--')
            listtosend.append(self.totalpulses)
            self.signalfullintegrals.emit(listtosend)
            partialstosend = self.listpartialintegralsdosecentigrays
            for i in range(len(partialstosend)):
                for j in range(1,8,2):
                    partialstosend[i].insert(j, '--')
            self.signalpartialintegrals.emit(partialstosend)

        elif (self.dosechecked and not(self.pulseschecked)) and self.grayschecked:
            listtosend = []
            for a in self.fullintdosegrays:
                listtosend.append(a)
                listtosend.append('--')
            listtosend.append(self.totalpulses)
            self.signalfullintegrals.emit(listtosend)
            partialstosend = self.listpartialintegralsdosecentigrays
            for i in range(len(partialstosend)):
                for j in range(1,8,2):
                    partialstosend[i].insert(j, '--')
            self.signalpartialintegrals.emit(partialstosend)

        elif (self.chargechecked and (self.pulseschecked)):
            listtosend = self.fullintchargep
            listtosend.append(self.totalpulses)
            #print ('list to send', listtosend)
            self.signalfullintegrals.emit(listtosend)
            self.signalpartialintegrals.emit(self.listpartialintegralschargep)

        elif (self.chargedosechecked and (self.pulseschecked)):
            listtosend = []
            for a in self.fullintchargedosep:
                listtosend.append(a)
                listtosend.append('--')
            listtosend.append(self.totalpulses)
            self.signalfullintegrals.emit(listtosend)
            partialstosend = self.listpartialintegralschargedosep
            for i in range(len(partialstosend)):
                for j in range(1,8,2):
                    partialstosend[i].insert(j, '--')
            self.signalpartialintegrals.emit(partialstosend)

        elif (self.dosechecked and (self.pulseschecked)) and self.centygrayschecked:
            listtosend = []
            for a in self.fullintdosecentygraysp:
                listtosend.append(a)
                listtosend.append('--')
            listtosend.append(self.totalpulses)
            self.signalfullintegrals.emit(listtosend)
            partialstosend = self.listpartialintegralsdosecentigraysp
            for i in range(len(partialstosend)):
                for j in range(1,8,2):
                    partialstosend[i].insert(j, '--')
            self.signalpartialintegrals.emit(partialstosend)

        elif (self.dosechecked and (self.pulseschecked)) and self.grayschecked:
            listtosend = []
            for a in self.fullintdosegraysp:
                listtosend.append(a)
                listtosend.append('--')
            listtosend.append(self.totalpulses)
            self.signalfullintegrals.emit(listtosend)
            partialstosend = self.listpartialintegralsdosegraysp
            for i in range(len(partialstosend)):
                for j in range(1,8,2):
                    partialstosend[i].insert(j, '--')
            self.signalpartialintegrals.emit(partialstosend)


    @pyqtSlot(str)
    def openfile(self, filename):
        nrawdata = filename.find('rawdata')
        goodfilename = filename[nrawdata:]
        #check self.capacitor
        file = open(goodfilename)
        lines = file.readlines()[:20]
        file.close()
        #check lines to skip
        for n, line in enumerate(lines):
            if line.startswith('number,time'):
                lines_to_skip = n

        rank = lines[2][6]
        print ('rank: ', rank)
        print ('rank type: ', type(rank))
        if rank == '0':
            self.capacitor = 30/1000
        elif rank == '1':
            self.capacitor = 60/1000
        print('capacitor: ', self.capacitor)

        #cartridgeinselected in header of the file
        if lines_to_skip != 4:
            cartridgeinselectedtext = lines[4][14:].strip()
        else:
            cartridgeinselectedtext = '1 sensor'
        self.cartridgeinselected = mysettingsw.cartridgeinlist.index(cartridgeinselectedtext)
        self.signalcartridgeinselected.emit(self.cartridgeinselected)
        print ('cartridgein seleted from file: ', self.cartridgeinselected)

        #generate listfunctions from header of file
        if lines_to_skip != 4:
            self.listfunctions = [i[14:].strip() for i in lines[5:13]]
        else:
            self.listfunctions = ['sensor0', 'cerenkov0', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']
        print ('func#tion list from file: ', self.listfunctions)

        #Get the number of channels from the header of the file
        if lines_to_skip !=4:
            self.number_of_channels = int(lines[3][19:].strip())
        else:
            self.number_of_channels = 2
        print ('number of channesls from file: ', self.number_of_channels)
        self.signalnumberofchannelsfromfile.emit(self.number_of_channels)
     

        df = pd.read_csv(goodfilename, skiprows=lines_to_skip)
        #print (df.head())
        for _ in range(10):
            if df.iloc[0, 0] > 10:
                df.drop(0, inplace=True)
                df.reset_index(inplace=True, drop=True)


        try:
            last_time = df.iloc[-1,1]
            zeros = df.loc[(df.time < 1)|(df.time > last_time - 1), 'ch0':].mean()
            dfchz = df.loc[:, 'ch0':] - zeros
            dfchz.columns = ['ch%sz' %i for i in range(self.number_of_channels)]
            dfz = pd.concat([df, dfchz], axis=1)
            self.chmaxz = dfz.loc[:,'ch0z':].max().idxmax()

            #calculate coulombs
            dfzc = dfz.loc[:,'ch0z':] * self.capacitor
            listachculombs = ['ch%sc' %i for i in range(self.number_of_channels)]
            dfzc.columns = listachculombs
            dfz = pd.concat([dfz, dfzc], axis=1)

            self.chmaxc = dfz.loc[:,'ch0c':].max().idxmax()
            print ('ch max is: ', self.chmaxc)

            maxvaluech = dfz.loc[(df.time < 2)|(df.time > last_time - 2), self.chmaxc].max()
            print ('max value of ', self.chmaxc, 'is ', maxvaluech)
            dfz['pulse'] = dfz[self.chmaxc] > maxvaluech
            dfz.loc[dfz.pulse, 'pulsenum'] = 1
            dfz.fillna({'pulsenum':0}, inplace=True)
            dfz['pulsecoincide'] = dfz.loc[dfz.pulse, 'number'].diff() == 1
            dfz.fillna({'pulsecoincide':False}, inplace=True)


            dfz['pulseafter'] = dfz.pulse.shift()
            dfz['pulseaa'] = dfz.pulse | dfz.pulseafter
            dfz['singlepulse'] = dfz.pulse & ~dfz.pulsecoincide
            dfz['pulsetoplot'] = dfz.singlepulse * 0.10


            dfz[['ch%sj' %i for i in range(self.number_of_channels)]] = dfz[['ch%sz' %i for i in range(self.number_of_channels)]]

            dfz.loc[~dfz.pulseaa, ['ch%sj' %i for i in range(self.number_of_channels)]] = 0

            dfz['chunk'] = dfz.number // int(300000/700)
            #print (dfz.loc[:,listachculombs + ['pulsetoplot']].head())
            # Calculate doses based in functionality in settings for any number of channels
            #in case of 1 single sensor or 4 single sensors
            print('before calculating dose, cartridgein selected index: ', self.cartridgeinselected)
            print ('before calculating dose, number of channels: ', self.number_of_channels)
            if self.cartridgeinselected in [0, 1]:
                #Find functionality of channels
                listasensorchannels = ['ch%sc' %self.listfunctions.index('sensor%s' %i) for i in range(self.number_of_channels//2)]
                print ('list sensor channels: ')
                print (listasensorchannels)
                listacerenkovchannels = ['ch%sc' %self.listfunctions.index('cerenkov%s' %i) for i in range(self.number_of_channels//2)]
                print ('list cerenkov channels: ')
                print (listacerenkovchannels)
                print ('list acrs')
                print (self.acrs)
                print ('list functions')
                print (self.listfunctions)
                acrssort = [self.acrs[listacerenkovchannels.index('cerenkov%s' %i)] for i in range(self.number_of_channels//2)]
                print ('ACRs sorted')
                print (acrssort)
                calibsort = [self.calibs[listsensorchannels.index('sensor%s' %i)] for i in range(self.number_of_channels//2)]
                print ('Calibration Factors Sorted: ')
                print (calibsort)
                #calculate charge dose for all channels
                listachargedose = ['chargedose%s' %i for i in range(self.number_of_channels//2)]
                print ('list charge dose: ')
                print (listachargedose)
                dfz.loc[:, listachargedose] = dfz.loc[:, listasensorchannels].values - (dfz.loc[:, listacerenkovchannels] * acrssort).values
                print (dfz.head())

                #calculate dose in cGy
                listadosecgy = ['dose%scgy' %i for i in range(self.number_of_channels//2)]
                dfz.loc[:, listadosecgy] = (dfz.loc[:, listachargedose] * calibsort).values

                #calculate dose in Gy
                listadosegy = ['dose%sgy' %i for i in range(self.number_of_channels//2)]
                dfz.loc[:, listadosegy] = (dfz.loc[:, listadosecgy] / 100).values
                
            #if RTSafe cartridge is selected Mercurius
            elif self.cartridgeinselected == 2:
            
                #calculate the charge proportional to dose for each channel
                sensor0now = 'ch%sc' %self.listfunctions.index('sensor0')
                cerenkov0now = 'ch%sc' %self.listfunctions.index('cerenkov0')
                acr0now = self.acrs[self.listfunctions.index('cerenkov0')]
                dfz['chargedose0'] = dfz[sensor0now] - dfz[cerenkov0now] * acr0now 
                listaschargedose = ['chargedose%s' %i for i in range(1,7)]
                listaschannels = ['ch%sc' %self.listfunctions.index('sensor%s' %i) for i in range(1,7)]

                dfz.loc[:, listaschargedose] = dfz.loc[:, listaschannels].values

                listachargedose = ['chargedose0'] + listaschargedose

                #calculate dose in cGy
                listadosecgy = ['dose%scgy' %i for i in range(7)]
                calibsort = [self.calibs[self.listfunctions.index('sensor%s' %i)] for i in range(7)]
                print ('calibsort is: ', calibsort)
                dfz.loc[:, listadosecgy] = dfz.loc[:, listachargedose].values * calibsort

                #calculate dose in Gy
                listadosegy = ['dose%sgy' %i for i in range(7)]
                dfz.loc[:, listadosegy] = dfz.loc[:, listadosecgy].values / 100
                
            group = dfz.groupby('chunk')

            dictime = {'time':np.median}
            dicvoltages = {'temp':np.mean, 'PS0':np.mean, '-15V':np.mean, '15V':np.mean, '5V':np.mean, 'singlepulse':np.sum}
            dicchannelsc = {'ch%sc' %i:np.sum for i in range(self.number_of_channels)}
            dicchannelsz = {'ch%sz' %i:np.sum for i in range(self.number_of_channels)}
            dicchargedose = {ch:np.sum for ch in listachargedose}
            dicdosecgy = {ch:np.sum for ch in listadosecgy}
            dicdosegy = {ch:np.sum for ch in listadosegy}
            #dicchargesensors = {'chargesensor%s' %i:np.sum for i in range(self.number_of_channels//2)}
            #dicchargecerenkovs = {'chargecerenkov%s' %i:np.sum for i in range(self.number_of_channels//2)}

            #dfg = group.agg({**dictime, **dicvoltages, **dicchannels, **dicchargesensors, **dicchargecerenkovs})
            dfg = group.agg({**dictime, **dicvoltages, **dicchannelsc, **dicchannelsz, **dicchargedose, **dicdosecgy, **dicdosegy})
            dfg['time_min'] = group['time'].min()
            dfg['time_max'] = group['time'].max()
            #dfz.to_csv('rawdata/testdfz.csv')
            self.dfg = dfg
            self.dfz = dfz
            self.df = df

            #print ('dfg head :')
            #print (self.dfg.head())

            limits = [float(dfg.iloc[-1,0]),
                       float((dfz.loc[:, listachculombs]).max().max()),
                       float((dfg.loc[:, listachculombs]).max().max()),
                       float(dfg.temp.min()),
                       float(dfg.temp.max()),
                       float(dfg.PS0.min()),
                       float(dfg.PS0.max()),
                       float(dfg['-15V'].min()),
                       float(dfg['-15V'].max()),
                       float(dfg['15V'].min()),
                       float(dfg['15V'].max()),
                       float(dfg['5V'].min()),
                       float(dfg['5V'].max())]

            self.signalreadytoplot.emit(limits)
            #print ('limits: ', limits)
            listofinterest = listachculombs + listachargedose + listadosecgy + listadosegy + ['singlepulse']
            #print (dfz.loc[:, listofinterest].sum().round(2))
            
            dflistfullintegrals = dfz.loc[:, listofinterest].sum().round(2).tolist()
            listfullintegralstosend = [float(i) for i in dflistfullintegrals]
            self.signalfullintegrals.emit(listfullintegralstosend)
            print ('lista full integrals: ', listfullintegralstosend)

        except IndexError:
            self.signalshowdialogerror.emit('IndexError, try it again')
            print ('Partial shot try again')

        except UnboundLocalError:
            self.signalshowdialogerror.emit('UnboundLocalError, try it again')
            print ('Un bound local error, try it again')

        except TypeError:
            self.signalshowdialogerror.emit('TypeError, try it again')

    @pyqtSlot()
    def autodetect(self):
        n = self._cutoff
        print ('n: ', n)
        print ('toffset: ', toffset)
        self.dfg['chdiff'] = self.dfg[self.chmaxz].diff()
        starttimes = self.dfg.loc[self.dfg.chdiff > n, 'time']
        print ('original starttimes: ', starttimes)
        finishtimes = self.dfg.loc[self.dfg.chdiff < -n, 'time']
        print ('original finishtimes: ', finishtimes)
        try:
            stss = [starttimes.iloc[0]] + list(starttimes[starttimes.diff()>2])
            sts = [t - toffset - 0.6 for t in stss]
            ftss = [finishtimes.iloc[0]] + list(finishtimes[finishtimes.diff()>2])
            fts = [t + toffset + 0.4 for t in ftss]
            print ('start times: ', sts)
            print ('finish times: ', fts)
            ststoplot = [float(i) for i in sts]
            ftstoplot = [float(i) for i in fts]
            self.signallimits.emit(ststoplot, ftstoplot)
        except IndexError:
            self.signalshowdialogerror.emit('Try a different cut off')



    @pyqtSlot(list, list)
    def calcshots (self, starttimes, finishtimes):
        sts = [i for i in starttimes if i != -1]
        fts = [j for j in finishtimes if j != -1]
        sts.sort()
        fts.sort()
        ststosend = [float(i) for i in sts]
        ftstosend = [float(j) for j in fts]
        
        listachannels = ['ch%s' %i for i in range(self.number_of_channels)]


        try:

            for j in range(len(sts)-1):
                if sts[j] > fts[j] or sts[j+1] < fts[j]:
                    raise ValueError

            for i in range(len(sts)):
                self.df.loc[(self.df.time > sts[i]) & (self.df.time < fts[i]), 'shot'] = i

            self.df.fillna(-1, inplace=True)

            #find better zeros
            listachannelsz = ['ch%sz' %i for i in range(self.number_of_channels)]
            newzeros = self.df.loc[(self.df.time < sts[0] -1)|(self.df.time > fts[-1] + 1), listachannels].mean()
            #print ('new zeros')
            #print (newzeros)
            dfzz = self.df.loc[:, listachannels] - newzeros
            dfzz.columns = listachannelsz
            self.dfz = pd.concat([self.df, dfzz], axis=1)
            #print ((self.dfz.loc[:,['ch0', 'ch1']] - newzeros).head())
            self.chmaxz = self.dfz.loc[:,listachannelsz].max().idxmax()

            #calculate coulombs
            dfzc = self.dfz.loc[:, listachannelsz] * self.capacitor
            listachculombs = ['ch%sc' %i for i in range(self.number_of_channels)]
            dfzc.columns = listachculombs
            self.dfz = pd.concat([self.dfz, dfzc], axis=1)

            self.chmaxc = self.dfz.loc[:, listachculombs].max().idxmax()
            print ('ch max is: ', self.chmaxc)

            maxvaluech = self.dfz.loc[(self.dfz.time < sts[0] - 1)|(self.dfz.time > fts[-1] + 1), self.chmaxc].max()
            print ('max value of ', self.chmaxc, 'with better pulses clean is: ', maxvaluech, type(maxvaluech))
            self.dfz['pulse'] = self.dfz[self.chmaxc] > maxvaluech
            self.dfz.loc[self.dfz.pulse, 'pulsenum'] = 1
            self.dfz.fillna({'pulsenum':0}, inplace=True)
            self.dfz['pulsecoincide'] = self.dfz.loc[self.dfz.pulse, 'number'].diff() == 1
            self.dfz.fillna({'pulsecoincide':False}, inplace=True)


            self.dfz['pulseafter'] = self.dfz.pulse.shift()
            self.dfz['pulseaa'] = self.dfz.pulse | self.dfz.pulseafter
            self.dfz['singlepulse'] = self.dfz.pulse & ~self.dfz.pulsecoincide
            self.dfz['pulsetoplot'] = self.dfz.singlepulse * 0.10


            self.dfz[['ch%sj' %i for i in range(self.number_of_channels)]] = self.dfz[['ch%sz' %i for i in range(self.number_of_channels)]]

            self.dfz.loc[~self.dfz.pulseaa, ['ch%sj' %i for i in range(self.number_of_channels)]] = 0

            self.dfz['chunk'] = self.dfz.number // int(300000/700)

            #Calculating doses with listfunctions
            print ('list of functions after shot calculations: ', self.listfunctions)
            if self.cartridgeinselected in [0,1]:
                #Find functionality of channels
                listasensorchannels = ['ch%sc' %self.listfunctions.index('sensor%s' %i) for i in range(self.number_of_channels//2)]
                listacerenkovchannels = ['ch%sc' %self.listfunctions.index('cerenkov%s' %i) for i in range(self.number_of_channels//2)]
                acrssort = [self.acrs[self.listfunctions.index('cerenkov%s' %i)] for i in range(self.number_of_channels//2)]
                calibsort = [self.calibs[self.listfunctions.index('sensor%s' %i)] for i in range(self.number_of_channels//2)]

                #calculate charge dose for all channels
                listachargedose = ['chargedose%s' %i for i in range(self.number_of_channels//2)]
                self.dfz.loc[:, listachargedose] = self.dfz.loc[:, listasensorchannels].values - (self.dfz.loc[:, listacerenkovchannels] * acrssort).values

                #calculate dose in cGy
                listadosecgy = ['dose%scgy' %i for i in range(self.number_of_channels//2)]
                self.dfz.loc[:, listadosecgy] = (self.dfz.loc[:, listachargedose] * calibsort).values

                #calculate dose in Gy
                listadosegy = ['dose%sgy' %i for i in range(self.number_of_channels//2)]
                self.dfz.loc[:, listadosegy] = (self.dfz.loc[:, listadosecgy] / 100).values
            #if 7 sensors RTSafe is selected
            elif self.cartridgeinselected == 2:
                #calculate the charge proportional to dose for each channel
                sensor0now = 'ch%sc' %self.listfunctions.index('sensor0')
                cerenkov0now = 'ch%sc' %self.listfunctions.index('cerenkov0')
                acr0now = self.acrs[self.listfunctions.index('cerenkov0')]
                self.dfz['chargedose0'] = self.dfz[sensor0now] - self.dfz[cerenkov0now] * acr0now 
                listaschargedose = ['chargedose%s' %i for i in range(1,7)]
                listaschannels = ['ch%sc' %self.listfunctions.index('sensor%s' %i) for i in range(1,7)]

                self.dfz.loc[:, listaschargedose] = self.dfz.loc[:, listaschannels].values

                listachargedose = ['chargedose0'] + listaschargedose

                #calculate dose in cGy
                listadosecgy = ['dose%scgy' %i for i in range(7)]
                calibsort = [self.calibs[self.listfunctions.index('sensor%s' %i)] for i in range(7)]
                print ('calibsort is: ', calibsort)
                self.dfz.loc[:, listadosecgy] = self.dfz.loc[:, listachargedose].values * calibsort

                #calculate dose in Gy
                listadosegy = ['dose%sgy' %i for i in range(7)]
                self.dfz.loc[:, listadosegy] = self.dfz.loc[:, listadosecgy].values / 100


            self.dfi = self.dfz.groupby('shot').sum()
            listofinterest = listachculombs + listachargedose + listadosecgy + listadosegy + ['singlepulse']
            #listanames = ['ch%sc' %i for i in range(self.number_of_channels)] + ['singlepulse']
            locintegralstosend = self.dfi.loc[0:, listofinterest].values.round(2).tolist()
            self.signalpartialintegrals.emit(ststosend, ftstosend, locintegralstosend)
            print ('lista shots')
            print (self.dfi.loc[0:, listofinterest].round(2))

            dflistfullintegrals = self.dfi.loc[0:, listofinterest].sum().round(2).tolist()
            listfullintegralstosend = [float(i) for i in dflistfullintegrals]
            self.signalfullintegrals.emit(listfullintegralstosend)


        except IndexError:
            self.signalshowdialogerror.emit('Different length start times and finish times')


        except ValueError as e:
            print (e)
            self.signalshowdialogerror.emit('Start and Finish times not in the right order')


    @pyqtSlot(QXYSeries, str, bool)
    def updateserieanalyze(self, serie, column, pulsestrue):
        if pulsestrue:
            dftoplot = self.dfz
        else:
            dftoplot = self.dfg
        pointstoreplace = [QPointF(x,y) for x, y in dftoplot.loc[:,['time', column]].values]
        serie.replace(pointstoreplace)


class SettingsWindow(QObject):

    signalrankread = pyqtSignal(str, arguments=['rankchip'])
    signalsendPS0 = pyqtSignal(str, arguments=['PS0value'])
    signalshowdialogerror = pyqtSignal(str, arguments=['textmessage'])

    def __init__(self):
        QObject.__init__(self)
        self._filename = 'default'
        self._notes = 'notes'
        self.cartridgeinlist = ['1 sensor', '4 sensors', '7 sen. RTSafe']
        self.cartridgeinselected = 2

    @pyqtSlot(int)
    def cartridgeinboxchange(self, index):
        print ('cartridgein selected: ', self.cartridgeinlist[index])
        self.cartridgeinselected = index

    @pyqtSlot()
    def checkPS0(self):
        try:
            device = list(serial.tools.list_ports.grep('ItsyBitsy M4'))[0].device
            ser = serial.Serial (device, 115200, timeout=1)
            ser.write('a'.encode())
            time.sleep(1)
            psnowraw = ser.readline()
            ser.close()
            pos = psnowraw.find(b'PS')
            psnow = psnowraw[pos:].strip().decode()
            psonly = psnow[12:]
            print ('PS0 value now is: ', psonly)
            if psonly == '1.10':
                self.signalshowdialogerror.emit('Acquisition Unit is turned off')
            self.signalsendPS0.emit(psonly)
        except IndexError:
            self.signalshowdialogerror.emit('Acquisition Unit not connected')

    @pyqtSlot(int)
    def sendtocontroller(self, value):
        device = list(serial.tools.list_ports.grep('ItsyBitsy M4'))[0].device
        serc = serial.Serial(device, 115200, timeout=1)
        texttosend = 'i%s,' %(value)
        serc.write(texttosend.encode())
        serc.close()
        print ('Sent to controller %s' %texttosend)


    @pyqtSlot(int)
    def rankselection(self, value):
        device = list(serial.tools.list_ports.grep('ItsyBitsy M4'))[0].device
        ser = serial.Serial (device, 115200, timeout=1)
        if value == 0:
            valuesend = 'l'
        else:
            valuesend = 'h'
        texttosend = 'c%s' %valuesend
        ser.write(texttosend.encode())
        print('I have sent rank: ', texttosend)
        ser.close()


    @pyqtSlot()
    def readrank(self):
        try:
            device = list(serial.tools.list_ports.grep('ItsyBitsy M4'))[0].device
            ser = serial.Serial (device, 115200, timeout=1)
            ser.write('f'.encode())
            time.sleep(0.5)
            #rankin = ser.readline().strip()[-20:].decode()[-1]
            rankin = ser.readline().strip()[-20:].decode()[-1]
            ser.close()
            print ('Reading rank from box: ', rankin, type(rankin))
            self.signalrankread.emit(rankin)
            return rankin
        except IndexError:
            self.signalshowdialogerror.emit('Acquisition Unit not connected')


    @pyqtSlot(str)
    def filenamein(self, textin):
        self._filename = textin


    @pyqtSlot(str)
    def notesin(self, textin):
        cleantext = textin.replace(',', '').replace('\n','')
        self._notes = cleantext
        #print (cleantext)


class Cartridgewindow (QObject):

    signaldisplaymemorydata = pyqtSignal(list, arguments=['listdatamemory'])

    def __init__(self):
        QObject.__init__(self)

    @pyqtSlot()
    def readallmemory(self):
        global number_of_channels
        device = list(serial.tools.list_ports.grep('ItsyBitsy M4'))[0].device
        ser = serial.Serial (device, 115200, timeout=1)
        ser.write('ma0,'.encode())
        memorynow = []
        firstline = ser.readline().strip()[-3:].decode()
        #print ('first line: ', firstline)
        for _ in range(32766):
            try:
                linenow = ser.readline().decode().strip()
                memorynow.append(linenow)
            except UnicodeDecodeError:
                break
        ser.close()

        allmemory = [firstline] + memorynow

        # remove values at the end of the file if they are not 222
        allmemory = allmemory[:allmemory.index('222') + 1]
        print ('all memory no int: ', allmemory)

        allmemoryint = [int(i) for i in allmemory]

        #Check if memory cartridge is connected
        if allmemoryint[0] == 255:
            #print ('length of memory when not connected: ', len(allmemory))
            print ('Cartridge not connected')
            allmemory = ['255']
            connected = False
        else:
            connected = True


        #check integrity of memory
        # is the begining and the end correct?
        begining = allmemoryint[0] == 111
        ending = allmemoryint[-1] == 222
        length = allmemoryint[-2] == len(allmemoryint)
        checksum = (allmemoryint[-4] << 8 | allmemoryint[-3]) == sum(allmemoryint[:55]) 
        filter = begining and ending and length and checksum
        print ('filter: ', filter)
        if filter:
            integrity = True
            print ('memory integrity OK')
            #Now that it is integrity we can display the information
            #First calculate the PS0
            PS0tosend = allmemoryint[3] + allmemoryint[4]/100
            print ('PS0 to send: ', PS0tosend)
            print ('number of channels in this cartridge: ', allmemoryint[2])
            number_of_channels = allmemoryint[2]
            self.signaldisplaymemorydata.emit(allmemoryint)
            self.allmemoryint = allmemoryint
        else:
            integrity = False
            print ('memory integrity issue')
        
        return connected, integrity




class Series (QObject):

    signalreadytoplot = pyqtSignal(list, arguments=['limits'])
    mysignal = pyqtSignal(list, arguments=['measnow'])
    mysignalfirstaxis = pyqtSignal(list, arguments=["lfirstaxis"])
    mysignalpulses = pyqtSignal(float, float, float, float, float, float, arguments=["tnowpulses", "meantemp", "meanPS0", "meanminus15V", "mean15V","mean5V"])
    signallimits = pyqtSignal(list, list, arguments=['starttimes', 'finishtimes'])
    signalfullintegrals = pyqtSignal(list, arguments=['fullintegrals'])
    signalpartialintegrals = pyqtSignal(list, list, list, arguments=['sortedstarttimes', 'sortedfinishtimes','partialintegrals'])
    signalshowdialogerror = pyqtSignal(str, arguments=['textmessage'])

    def __init__(self):
        QObject.__init__(self)
        self.reset()
        self.chargechecked = True
        self.chargedosechecked = False
        self.dosechecked = False
        self.grayschecked = False
        self.centygrayschecked = True
        self._cutoff = 40
        self.sensors = ['ch%sz' %i for i in range(0,number_of_channels,2)]
        #self.sensorsj = ['ch%sj' %i for i in range(0, number_of_channels,2)]
        #self.sensorsi = [i for i in range(0, number_of_channels, 2)]
        #self.cerenkovs = ['ch%sz' %i for i in range(1, number_of_channels,2)]
        #self.cerenkovsj = ['ch%sj' %i for i in range(1, number_of_channels,2)]
        #self.cerenkovsi = [i for i in range(1, number_of_channels,2)]
        self.acrs = [1 for i in range(number_of_channels)]
        self.capacitor = 10/1000
        self.calibs = [1 for i in range(number_of_channels)]
        self.pulseschecked = False
        #functions available must be equal to list of functions in qml
        self.functionsavailable = ['N/A', 'sensor0', 'cerenkov0', 'sensor1', 'cerenkov1', 'sensor2', 'cerenkov2', 'sensor3',
                                  'cerenkov3', 'sensor4', 'sensor5', 'sensor6', 'sensor7']
        self.listfunctions = ['N/A'] * 8

        #uncomment if emulator
        #self.avemulator = np.loadtxt('rawdata/zapOF.csv', delimiter=',', skiprows=5)

    #Function to check Acquisition Unity and Cartridge at the begining
    @pyqtSlot()
    def checkacqucartridge(self):
        #First check connection to PS ACD1115 chip
        try:
            device = list(serial.tools.list_ports.grep('ItsyBitsy M4'))[0].device
            ser = serial.Serial (device, 115200, timeout=1)
            ser.write('a'.encode())
            time.sleep(1)
            psnowraw = ser.readline()
            ser.close()
            pos = psnowraw.find(b'PS')
            psnow = psnowraw[pos:].strip().decode()
            psonly = psnow[12:]
            print ('Check status of Acquisition Unit: ', psonly, type(psonly))
            if psonly == '1.10':
                print ('Acquisition Unit is turned off')
                self.signalshowdialogerror.emit('Acquisition Unit is turned off')
            elif psonly == '99.4253' or psonly == '82.2632':
                self.signalshowdialogerror.emit('Reset Acquisition Unit')
            else:
                #print ('Check cartridge is work in progress')
                # Acquisition unit is OK but let's check the cartridge now
                cartridge_connected, integrity = mycartridgew.readallmemory()
                if cartridge_connected:
                    if integrity:
                        self.signalshowdialogerror.emit('Acquisition Unit and\nCartridge connected\nand memory integrity OK')
                    else:
                        self.signalshowdialogerror.emit('Acquisition Unit and\nCartridge are connected\nbut memory integrity NOT OK')
                else:
                    self.signalshowdialogerror.emit('Acquisition Unit is OK\nbut Cartridge is disconnected')
        except IndexError:
            self.signalshowdialogerror.emit('Acquisition Unit not connected')


    @pyqtSlot(bool)
    def pulsescheck(self, checked):
        self.pulseschecked = checked


    @pyqtSlot(int)
    def sendtocontroller(self, value):
        device = list(serial.tools.list_ports.grep('ItsyBitsy M4'))[0].device
        serc = serial.Serial(device, 115200, timeout=1)
        texttosend = 'i%s,' %(value)
        serc.write(texttosend.encode())
        serc.close()
        print ('Sent to controller %s' %texttosend)

    @pyqtSlot(int)
    def cutoffchange(self, currentindex):
        cutoffvalues = [0.5, 10, 20, 40, 100, 150]
        self._cutoff = cutoffvalues[currentindex]
        print ('cutoff now is: %s' %self._cutoff)

    @pyqtSlot(int)
    def functionch0change(self, index):
        #self.sensorsi[0] = chnumber
        #self.sensors[0] = 'ch%sz' %chnumber
        #self.sensorsj[0] = 'ch%sj' %chnumber
        self.listfunctions[0] = self.functionsavailable[index]
        print ('Function of ch0 is now: %s' %self.functionsavailable[index])
        print ('list functions is now: %s' %self.listfunctions)

    @pyqtSlot(int)
    def functionch1change(self, index):
        #self.sensorsi[1] = chnumber
        #self.sensors[1] = 'ch%sz' %chnumber
        #self.sensorsj[1] = 'ch%sj' %chnumber
        self.listfunctions[1] = self.functionsavailable[index]
        print ('list functions is now: %s' %self.listfunctions)

    @pyqtSlot(int)
    def functionch2change(self, index):
        #self.sensorsi[2] = chnumber
        #self.sensors[2] = 'ch%sz' %chnumber
        #self.sensorsj[2] = 'ch%sj' %chnumber
        self.listfunctions[2] = self.functionsavailable[index]
        print ('list ch2  functions is now: %s' %self.listfunctions, self.functionsavailable[index], index)
        
        

    @pyqtSlot(int)
    def functionch3change(self, index):
        #self.sensorsi[3] = chnumber
        #self.sensors[3] = 'ch%sz' %chnumber
        #self.sensorsj[3] = 'ch%sj' %chnumber
        self.listfunctions[3] = self.functionsavailable[index]
        print ('list functions is now: %s' %self.listfunctions)

    @pyqtSlot(int)
    def functionch4change(self, index):
        #self.cerenkovsi[0] = chnumber
        #self.cerenkovs[0] = 'ch%sz' %chnumber
        #self.cerenkovsj[0] = 'ch%sj' %chnumber
        self.listfunctions[4] = self.functionsavailable[index]
        print ('ch4 change list functions is now: %s' %self.listfunctions)
        

    @pyqtSlot(int)
    def functionch5change(self, index):
        #self.cerenkovsi[1] = chnumber
        #self.cerenkovs[1] = 'ch%sz' %chnumber
        #self.cerenkovsj[1] = 'ch%sj' %chnumber
        self.listfunctions[5] = self.functionsavailable[index]
        print ('list functions is now: %s' %self.listfunctions)

    @pyqtSlot(int)
    def functionch6change(self, index):
        #self.cerenkovsi[2] = chnumber
        #self.cerenkovs[2] = 'ch%sz' %chnumber
        #self.cerenkovsj[2] = 'ch%sj' %chnumber
        self.listfunctions[6] = self.functionsavailable[index]
        print ('list functions is now: %s' %self.listfunctions)

    @pyqtSlot(int)
    def functionch7change(self, index):
        #self.cerenkovsi[3] = chnumber
        #self.cerenkovs[3] = 'ch%sz' %chnumber
        #self.cerenkovsj[3] = 'ch%sj' %chnumber
        self.listfunctions[7] = self.functionsavailable[index]
        print ('list functions is now: %s' %self.listfunctions)


    @pyqtSlot(int)
    def acr0change(self, newacr):
        self.acrs[0] = newacr/10000000

    @pyqtSlot(int)
    def acr1change(self, newacr):
        self.acrs[1] = newacr/10000000

    @pyqtSlot(int)
    def acr2change(self, newacr):
        self.acrs[2] = newacr/10000000

    @pyqtSlot(int)
    def acr3change(self, newacr):
        self.acrs[3] = newacr/10000000


    @pyqtSlot(int)
    def acr4change(self, newacr):
        self.acrs[4] = newacr/10000000

    @pyqtSlot(int)
    def acr5change(self, newacr):
        self.acrs[5] = newacr/10000000

    @pyqtSlot(int)
    def acr6change(self, newacr):
        self.acrs[6] = newacr/10000000

    @pyqtSlot(int)
    def acr7change(self, newacr):
        self.acrs[7] = newacr/10000000


    @pyqtSlot(int)
    def calib0change(self, newcalib):
        self.calibs[0] = newcalib/10000000

    @pyqtSlot(int)
    def calib1change(self, newcalib):
        self.calibs[1] = newcalib/10000000

    @pyqtSlot(int)
    def calib2change(self, newcalib):
        self.calibs[2] = newcalib/10000000

    @pyqtSlot(int)
    def calib3change(self, newcalib):
        self.calibs[3] = newcalib/10000000


    @pyqtSlot(int)
    def calib4change(self, newcalib):
        self.calibs[4] = newcalib/10000000


    @pyqtSlot(int)
    def calib5change(self, newcalib):
        self.calibs[5] = newcalib/10000000


    @pyqtSlot(int)
    def calib6change(self, newcalib):
        self.calibs[6] = newcalib/10000000


    @pyqtSlot(int)
    def calib7change(self, newcalib):
        self.calibs[7] = newcalib/10000000
        print (self.calibs)

    @pyqtSlot(bool)
    def chargecheck(self, checked):
        self.chargechecked = True
        self.chargedosechecked = False
        self.dosechecked = False
        print ('chargedose button is now: ', checked)

    @pyqtSlot(bool)
    def chargedosecheck(self, checked):
        self.chargechecked = False
        self.chargedosechecked = True
        self.dosechecked = False
        print ('chargedose button is now: ', checked)

    @pyqtSlot(bool)
    def dosecheck(self, checked):
        self.chargechecked = False
        self.chargedosechecked = False
        self.dosechecked = True
        print ('dose button is now: ', checked)

    @pyqtSlot(bool)
    def grayscheck(self, checked):
        self.grayschecked = checked
        self.centygrayschecked = not(checked)
        print ('grays button is now: ', checked)

    @pyqtSlot(bool)
    def centygrayscheck(self, checked):
        self.centygrayschecked = checked
        self.grayschecked = not(checked)
        print ('centygrays button is now: ', checked)

    def checkbaseline(self):

        #comment if emulator
        aa = np.ndarray((number_of_samples,number_of_bytes), np.uint8, globalda[-(number_of_samples*number_of_bytes):])
        ac = np.column_stack((aa[:,[0,4]] * 2**24 + aa[:,[1,5]] * 2**16 + aa[:,[2,6]] * 2**8 + aa[:,[3,7]],
                              2**8 + aa[:,9],
                              aa[:,10::2] * 2**8 + aa[:,11::2]))
        av1 = ac * arrmultip + arrsum
        av = av1[:,:7+number_of_channels]

        #uncomment if emulator
        #av = self.avemulator[:number_of_samples]


        print ('First temp min', av[:,2].min())
        tempmean = float(av[:,2].mean())
        psmean = float(av[:,3].mean())
        vminus15mean = float(av[:,4].mean())
        v15mean = float(av[:,5].mean())
        v5mean = float(av[:,6].mean())
        self.chmeans = av[:,7:].mean(axis=0)
        self.chzeromax = av[:,7:].max()
        print ('zero channels', self.chmeans)
        self.mysignalfirstaxis.emit([tempmean, psmean, vminus15mean, v15mean, v5mean])


    def reset(self):
        dicvoltages = {'temp':[], 'PS0':[], '-15V':[], '15V':[], '5V':[]}
        #dicsensors = {'s%s' %i:[] for i in range(number_of_channels//2)}
        #diccerenkovs = {'c%s' %i:[] for i in range(number_of_channels//2)}
        dicchannels = {'ch%s' %i:[] for i in range(number_of_channels)}
        dicchargedose0 = {'chargedose0':[]}
        #self.dicpointspulsesrealtime = {**dicvoltages, **dicsensors, **diccerenkovs}
        #self.dicpointsrealtime = {**dicvoltages, **dicsensors, **diccerenkovs}
        self.dicpointspulsesrealtime = {**dicvoltages, **dicchannels, **dicchargedose0}
        self.dicpointsrealtime = {**dicvoltages, **dicchannels, **dicchargedose0}

        #uncomment if emulator
        #self.emulatorcounter = 0


    def updatepoints(self):

        #comment if emulator
        aa = np.ndarray((number_of_samples,number_of_bytes), np.uint8, globalda[-(number_of_samples * number_of_bytes):])
        ac = np.column_stack((aa[:,[0,4]] * 2**24 + aa[:,[1,5]] * 2**16 + aa[:,[2,6]] * 2**8 + aa[:,[3,7]],
                              2**8 + aa[:,9],
                              aa[:,10::2] * 2**8 + aa[:,11::2]))
        avp1 = ac * arrmultip + arrsum
        avp = avp1[:,:7+number_of_channels]

        #uncomment if emulator
        #avp = self.avemulator[number_of_samples * self.emulatorcounter: number_of_samples * (self.emulatorcounter + 1)]
        #self.emulatorcounter = self.emulatorcounter + 1

        avz = avp - np.hstack((np.zeros(7), self.chmeans))
        ameans = avz.sum(axis=0) / np.array([number_of_samples]*7 + [1]*number_of_channels)
        #print ('ameans: ', ameans)
        tnow = ameans[1]
        chsmax = ameans[7:].max()
        listato = avp[-1].tolist()

        #print (['%.2f' %i for i in listato])

        if self.pulseschecked:
            self.dicpointspulsesrealtime['temp'] = [QPointF(x,y) for x,y in avp[:,[1,2]]]
            self.dicpointspulsesrealtime['PS0'] = [QPointF(x,y) for x,y in avp[:,[1,3]]]
            self.dicpointspulsesrealtime['-15V'] = [QPointF(x,y) for x,y in avp[:,[1,4]]]
            self.dicpointspulsesrealtime['15V'] = [QPointF(x,y) for x,y in avp[:,[1,5]]]
            self.dicpointspulsesrealtime['5V'] = [QPointF(x,y) for x,y in avp[:,[1,6]]]
            for i in range(number_of_channels):
                #print ('time now: ' ,avp[-1,1])
                self.dicpointspulsesrealtime['ch%s' %i] = [QPointF(x,y) for x,y in avp[:,[1, 7 + i]]]
            '''for i in range(number_of_channels//2):
                self.dicpointspulsesrealtime['s%s' %i] = [QPointF(x,y) for x,y in avp[:,[1,7 + self.sensorsi[i]]]]
                self.dicpointspulsesrealtime['c%s' %i] = [QPointF(x,y) for x,y in avp[:,[1, 7 + self.cerenkovsi[i]]]]'''

            self.mysignalpulses.emit(float(avp[-1,1]), float(avp[:,2].mean()), float(avp[:,3].mean()), float(avp[:,4].mean()), float(avp[:,5].mean()), float(avp[:,6].mean()))
        else:
            self.dicpointsrealtime['temp'].append(QPointF(tnow, ameans[2]))
            self.dicpointsrealtime['PS0'].append(QPointF(tnow, ameans[3]))
            self.dicpointsrealtime['-15V'].append(QPointF(tnow, ameans[4]))
            self.dicpointsrealtime['15V'].append(QPointF(tnow, ameans[5]))
            self.dicpointsrealtime['5V'].append(QPointF(tnow, ameans[6]))
            for i in range(number_of_channels):
                self.dicpointsrealtime['ch%s' %i].append(QPointF(tnow, ameans[7 +i]))
            '''for i in range(number_of_channels//2):
                self.dicpointsrealtime['s%s' %i].append(QPointF(tnow, ameans[7 + self.sensorsi[i]]))
                self.dicpointsrealtime['c%s' %i].append(QPointF(tnow, ameans[7 + self.cerenkovsi[i]]))'''
            
            self.dicpointsrealtime['chargedose0'].append(QPointF(tnow, (ameans[7+0] - ameans[7+1]*self.acrs[0])))
            self.mysignal.emit([float(tnow), float(chsmax), float(ameans[2]), float(ameans[3]), float(ameans[4]), float(ameans[5]), float(ameans[6])])


    #def stopping(self):
        #function to do things after stopping
        #added here now to work with emulator
        #self.analyzemeasurements(self.avemulator, '1')

    def analyzemeasurements(self, aa, rank):
        print ('rank: ', rank)
        print ('rank type: ', type(rank))
        if rank == '0':
            self.capacitor = 30/1000
        elif rank == '1':
            self.capacitor = 60/1000
        print('capacitor: ', self.capacitor)


        try:
            df = pd.DataFrame(aa, columns = ['number','time','temp','PS0','-15V','15V','5V'] + ['ch%s' %i for i in range(number_of_channels)])
            #remove dummy lines
            for _ in range(10):
                if df.iloc[0, 0] > 10:
                    df.drop(0, inplace=True)
                    df.reset_index(inplace=True, drop=True)


            last_time = df.iloc[-1,1]
            zeros = df.loc[(df.time < 1)|(df.time > last_time - 1), 'ch0':].mean()
            dfchz = df.loc[:, 'ch0':] - zeros
            dfchz.columns = ['ch%sz' %i for i in range(number_of_channels)]
            dfz = pd.concat([df, dfchz], axis=1)
            self.chmaxz = dfz.loc[:,'ch0z':].max().idxmax()

            #calculate coulombs
            dfzc = dfz.loc[:,'ch0z':] * self.capacitor
            listachculombs = ['ch%sc' %i for i in range(number_of_channels)]
            dfzc.columns = listachculombs
            dfz = pd.concat([dfz, dfzc], axis=1)

            self.chmaxc = dfz.loc[:,'ch0c':].max().idxmax()
            print ('ch max is: ', self.chmaxc)

            maxvaluech = dfz.loc[(df.time < 2)|(df.time > last_time - 2), self.chmaxc].max()
            print ('max value of ', self.chmaxc, 'is ', maxvaluech)
            dfz['pulse'] = dfz[self.chmaxc] > maxvaluech
            dfz.loc[dfz.pulse, 'pulsenum'] = 1
            dfz.fillna({'pulsenum':0}, inplace=True)
            dfz['pulsecoincide'] = dfz.loc[dfz.pulse, 'number'].diff() == 1
            dfz.fillna({'pulsecoincide':False}, inplace=True)


            dfz['pulseafter'] = dfz.pulse.shift()
            dfz['pulseaa'] = dfz.pulse | dfz.pulseafter
            dfz['singlepulse'] = dfz.pulse & ~dfz.pulsecoincide
            dfz['pulsetoplot'] = dfz.singlepulse * 0.10


            dfz[['ch%sj' %i for i in range(number_of_channels)]] = dfz[['ch%sz' %i for i in range(number_of_channels)]]

            dfz.loc[~dfz.pulseaa, ['ch%sj' %i for i in range(number_of_channels)]] = 0

            dfz['chunk'] = dfz.number // int(300000/700)

            # Calculate doses based in functionality in settings for any number of channels
            #in case of 1 single sensor or 4 single sensors
            print('before calculating dose, cartridgein selected index: ', mysettingsw.cartridgeinselected)
            print ('before calculating dose, number of channels: ', number_of_channels)
            if mysettingsw.cartridgeinselected in [0, 1]:
                #Find functionality of channels
                listasensorchannels = ['ch%sc' %self.listfunctions.index('sensor%s' %i) for i in range(number_of_channels//2)]
                listacerenkovchannels = ['ch%sc' %self.listfunctions.index('cerenkov%s' %i) for i in range(number_of_channels//2)]
                acrssort = [self.acrs[self.listfunctions.index('cerenkov%s' %i)] for i in range(number_of_channels//2)]
                calibsort = [self.calibs[self.listfunctions.index('sensor%s' %i)] for i in range(number_of_channels//2)]

                #calculate charge dose for all channels
                listachargedose = ['chargedose%s' %i for i in range(number_of_channels//2)]
                dfz.loc[:, listachargedose] = dfz.loc[:, listasensorchannels].values - (dfz.loc[:, listacerenkovchannels] * acrssort).values

                #calculate dose in cGy
                listadosecgy = ['dose%scgy' %i for i in range(number_of_channels//2)]
                dfz.loc[:, listadosecgy] = (dfz.loc[:, listachargedose] * calibsort).values

                #calculate dose in Gy
                listadosegy = ['dose%sgy' %i for i in range(number_of_channels//2)]
                dfz.loc[:, listadosegy] = (dfz.loc[:, listadosecgy] / 100).values
                
            #if RTSafe cartridge is selected Mercurius
            elif mysettingsw.cartridgeinselected == 2:
            
                #calculate the charge proportional to dose for each channel
                sensor0now = 'ch%sc' %self.listfunctions.index('sensor0')
                cerenkov0now = 'ch%sc' %self.listfunctions.index('cerenkov0')
                acr0now = self.acrs[self.listfunctions.index('cerenkov0')]
                dfz['chargedose0'] = dfz[sensor0now] - dfz[cerenkov0now] * acr0now 
                listaschargedose = ['chargedose%s' %i for i in range(1,7)]
                listaschannels = ['ch%sc' %self.listfunctions.index('sensor%s' %i) for i in range(1,7)]

                dfz.loc[:, listaschargedose] = dfz.loc[:, listaschannels].values

                listachargedose = ['chargedose0'] + listaschargedose

                #calculate dose in cGy
                listadosecgy = ['dose%scgy' %i for i in range(7)]
                calibsort = [self.calibs[self.listfunctions.index('sensor%s' %i)] for i in range(7)]
                print ('calibsort is: ', calibsort)
                dfz.loc[:, listadosecgy] = dfz.loc[:, listachargedose].values * calibsort

                #calculate dose in Gy
                listadosegy = ['dose%sgy' %i for i in range(7)]
                dfz.loc[:, listadosegy] = dfz.loc[:, listadosecgy].values / 100

            group = dfz.groupby('chunk')

            dictime = {'time':np.median}
            dicvoltages = {'temp':np.mean, 'PS0':np.mean, '-15V':np.mean, '15V':np.mean, '5V':np.mean, 'singlepulse':np.sum}
            dicchannelsc = {'ch%sc' %i:np.sum for i in range(number_of_channels)}
            dicchannelsz = {'ch%sz' %i:np.sum for i in range(number_of_channels)}
            dicchargedose = {ch:np.sum for ch in listachargedose}
            dicdosecgy = {ch:np.sum for ch in listadosecgy}
            dicdosegy = {ch:np.sum for ch in listadosegy}
            #dicchargesensors = {'chargesensor%s' %i:np.sum for i in range(number_of_channels//2)}
            #dicchargecerenkovs = {'chargecerenkov%s' %i:np.sum for i in range(number_of_channels//2)}

            #dfg = group.agg({**dictime, **dicvoltages, **dicchannels, **dicchargesensors, **dicchargecerenkovs})
            dfg = group.agg({**dictime, **dicvoltages, **dicchannelsc, **dicchannelsz, **dicchargedose, **dicdosecgy, **dicdosegy})
            dfg['time_min'] = group['time'].min()
            dfg['time_max'] = group['time'].max()
            #dfz.to_csv('rawdata/testdfz.csv')
            self.dfg = dfg
            self.dfz = dfz
            self.df = df

            #print ('dfg head :')
            #print (self.dfg.head())

            limits = [float(dfg.iloc[-1,0]),
                       float((dfz.loc[:, listachculombs]).max().max()),
                       float((dfg.loc[:, listachculombs]).max().max()),
                       float(dfg.temp.min()),
                       float(dfg.temp.max()),
                       float(dfg.PS0.min()),
                       float(dfg.PS0.max()),
                       float(dfg['-15V'].min()),
                       float(dfg['-15V'].max()),
                       float(dfg['15V'].min()),
                       float(dfg['15V'].max()),
                       float(dfg['5V'].min()),
                       float(dfg['5V'].max())]

            self.signalreadytoplot.emit(limits)
            #print ('limits: ', limits)
            listofinterest = listachculombs + listachargedose + listadosecgy + listadosegy + ['singlepulse']
            #print (dfz.loc[:, listofinterest].sum().round(2))
            
            dflistfullintegrals = dfz.loc[:, listofinterest].sum().round(2).tolist()
            listfullintegralstosend = [float(i) for i in dflistfullintegrals]
            self.signalfullintegrals.emit(listfullintegralstosend)
            print ('lista full integrals: ', listfullintegralstosend)

        except IndexError:
            self.signalshowdialogerror.emit('IndexError, try it again')
            print ('Partial shot try again')

        except UnboundLocalError:
            self.signalshowdialogerror.emit('UnboundLocalError, try it again')
            print ('Un bound local error, try it again')

        except TypeError:
            self.signalshowdialogerror.emit('TypeError, try it again')


    @pyqtSlot()
    def autodetect(self):
        n = self._cutoff
        print ('n: ', n)
        print ('toffset: ', toffset)
        self.dfg['chdiff'] = self.dfg[self.chmaxz].diff()
        starttimes = self.dfg.loc[self.dfg.chdiff > n, 'time']
        print ('original starttimes: ', starttimes)
        finishtimes = self.dfg.loc[self.dfg.chdiff < -n, 'time']
        print ('original finishtimes: ', finishtimes)
        try:
            stss = [starttimes.iloc[0]] + list(starttimes[starttimes.diff()>2])
            sts = [t - toffset - 0.6 for t in stss]
            ftss = [finishtimes.iloc[0]] + list(finishtimes[finishtimes.diff()>2])
            fts = [t + toffset + 0.4 for t in ftss]
            print ('start times: ', sts)
            print ('finish times: ', fts)
            ststoplot = [float(i) for i in sts]
            ftstoplot = [float(i) for i in fts]
            self.signallimits.emit(ststoplot, ftstoplot)
        except IndexError:
            self.signalshowdialogerror.emit('Try a different cut off')


    @pyqtSlot(list, list)
    def calcshots (self, starttimes, finishtimes):
        sts = [i for i in starttimes if i != -1]
        fts = [j for j in finishtimes if j != -1]
        sts.sort()
        fts.sort()
        ststosend = [float(i) for i in sts]
        ftstosend = [float(j) for j in fts]
        
        listachannels = ['ch%s' %i for i in range(number_of_channels)]


        try:

            for j in range(len(sts)-1):
                if sts[j] > fts[j] or sts[j+1] < fts[j]:
                    raise ValueError

            for i in range(len(sts)):
                self.df.loc[(self.df.time > sts[i]) & (self.df.time < fts[i]), 'shot'] = i

            self.df.fillna(-1, inplace=True)

            #find better zeros
            listachannelsz = ['ch%sz' %i for i in range(number_of_channels)]
            newzeros = self.df.loc[(self.df.time < sts[0] -1)|(self.df.time > fts[-1] + 1), listachannels].mean()
            #print ('new zeros')
            #print (newzeros)
            dfzz = self.df.loc[:, listachannels] - newzeros
            dfzz.columns = listachannelsz
            self.dfz = pd.concat([self.df, dfzz], axis=1)
            #print ((self.dfz.loc[:,['ch0', 'ch1']] - newzeros).head())
            self.chmaxz = self.dfz.loc[:,listachannelsz].max().idxmax()

            #calculate coulombs
            dfzc = self.dfz.loc[:, listachannelsz] * self.capacitor
            listachculombs = ['ch%sc' %i for i in range(number_of_channels)]
            dfzc.columns = listachculombs
            self.dfz = pd.concat([self.dfz, dfzc], axis=1)

            self.chmaxc = self.dfz.loc[:, listachculombs].max().idxmax()
            print ('ch max is: ', self.chmaxc)

            maxvaluech = self.dfz.loc[(self.dfz.time < sts[0] - 1)|(self.dfz.time > fts[-1] + 1), self.chmaxc].max()
            print ('max value of ', self.chmaxc, 'with better pulses clean is: ', maxvaluech, type(maxvaluech))
            self.dfz['pulse'] = self.dfz[self.chmaxc] > maxvaluech
            self.dfz.loc[self.dfz.pulse, 'pulsenum'] = 1
            self.dfz.fillna({'pulsenum':0}, inplace=True)
            self.dfz['pulsecoincide'] = self.dfz.loc[self.dfz.pulse, 'number'].diff() == 1
            self.dfz.fillna({'pulsecoincide':False}, inplace=True)


            self.dfz['pulseafter'] = self.dfz.pulse.shift()
            self.dfz['pulseaa'] = self.dfz.pulse | self.dfz.pulseafter
            self.dfz['singlepulse'] = self.dfz.pulse & ~self.dfz.pulsecoincide
            self.dfz['pulsetoplot'] = self.dfz.singlepulse * 0.10


            self.dfz[['ch%sj' %i for i in range(number_of_channels)]] = self.dfz[['ch%sz' %i for i in range(number_of_channels)]]

            self.dfz.loc[~self.dfz.pulseaa, ['ch%sj' %i for i in range(number_of_channels)]] = 0

            self.dfz['chunk'] = self.dfz.number // int(300000/700)

            #Calculating doses with listfunctions
            print ('list of functions after shot calculations: ', self.listfunctions)
            if mysettingsw.cartridgeinselected in [0,1]:
                #Find functionality of channels
                listasensorchannels = ['ch%sc' %self.listfunctions.index('sensor%s' %i) for i in range(number_of_channels//2)]
                listacerenkovchannels = ['ch%sc' %self.listfunctions.index('cerenkov%s' %i) for i in range(number_of_channels//2)]
                acrssort = [self.acrs[self.listfunctions.index('cerenkov%s' %i)] for i in range(number_of_channels//2)]
                calibsort = [self.calibs[self.listfunctions.index('sensor%s' %i)] for i in range(number_of_channels//2)]

                #calculate charge dose for all channels
                listachargedose = ['chargedose%s' %i for i in range(number_of_channels//2)]
                self.dfz.loc[:, listachargedose] = self.dfz.loc[:, listasensorchannels].values - (self.dfz.loc[:, listacerenkovchannels] * acrssort).values

                #calculate dose in cGy
                listadosecgy = ['dose%scgy' %i for i in range(number_of_channels//2)]
                self.dfz.loc[:, listadosecgy] = (self.dfz.loc[:, listachargedose] * calibsort).values

                #calculate dose in Gy
                listadosegy = ['dose%sgy' %i for i in range(number_of_channels//2)]
                self.dfz.loc[:, listadosegy] = (self.dfz.loc[:, listadosecgy] / 100).values
            #if 7 sensors RTSafe is selected
            elif mysettingsw.cartridgeinselected == 2:
                #calculate the charge proportional to dose for each channel
                sensor0now = 'ch%sc' %self.listfunctions.index('sensor0')
                cerenkov0now = 'ch%sc' %self.listfunctions.index('cerenkov0')
                acr0now = self.acrs[self.listfunctions.index('cerenkov0')]
                self.dfz['chargedose0'] = self.dfz[sensor0now] - self.dfz[cerenkov0now] * acr0now 
                listaschargedose = ['chargedose%s' %i for i in range(1,7)]
                listaschannels = ['ch%sc' %self.listfunctions.index('sensor%s' %i) for i in range(1,7)]

                self.dfz.loc[:, listaschargedose] = self.dfz.loc[:, listaschannels].values

                listachargedose = ['chargedose0'] + listaschargedose

                #calculate dose in cGy
                listadosecgy = ['dose%scgy' %i for i in range(7)]
                calibsort = [self.calibs[self.listfunctions.index('sensor%s' %i)] for i in range(7)]
                print ('calibsort is: ', calibsort)
                self.dfz.loc[:, listadosecgy] = self.dfz.loc[:, listachargedose].values * calibsort

                #calculate dose in Gy
                listadosegy = ['dose%sgy' %i for i in range(7)]
                self.dfz.loc[:, listadosegy] = self.dfz.loc[:, listadosecgy].values / 100


            self.dfi = self.dfz.groupby('shot').sum()
            listofinterest = listachculombs + listachargedose + listadosecgy + listadosegy + ['singlepulse']
            #listanames = ['ch%sc' %i for i in range(number_of_channels)] + ['singlepulse']
            locintegralstosend = self.dfi.loc[0:, listofinterest].values.round(2).tolist()
            self.signalpartialintegrals.emit(ststosend, ftstosend, locintegralstosend)
            print ('lista shots')
            print (self.dfi.loc[0:, listofinterest].round(2))

            dflistfullintegrals = self.dfi.loc[0:, listofinterest].sum().round(2).tolist()
            listfullintegralstosend = [float(i) for i in dflistfullintegrals]
            self.signalfullintegrals.emit(listfullintegralstosend)


        except IndexError:
            self.signalshowdialogerror.emit('Different length start times and finish times')


        except ValueError:
            self.signalshowdialogerror.emit('Start and Finish times not in the right order')



    @pyqtSlot(QXYSeries, str, bool)
    def updateserieanalyze(self, serie, column, pulsestrue):
        if pulsestrue:
            dftoplot = self.dfz
        else:
            dftoplot = self.dfg
        pointstoreplace = [QPointF(x,y) for x, y in dftoplot.loc[:,['time', column]].values]
        serie.replace(pointstoreplace)

    @pyqtSlot(QXYSeries, str)
    def updateseriepulsesrealtime(self, serie, n):
        pointstoreplace = self.dicpointspulsesrealtime[n]
        serie.replace(pointstoreplace)

    @pyqtSlot(QXYSeries, str)
    def updateserierealtime(self, serie, n):
        pointstoreplace = self.dicpointsrealtime[n]
        serie.replace(pointstoreplace)



#Create objects and threads
readingthread = ReadingThread()
regulatethread = RegulatingThread()
timer = QTimer()
myseries = Series()
mydarkcurrentthread = DarkCurrentThread()
mysettingsw = SettingsWindow()
myanalyzew = AnalyzeWindow()
mycartridgew = Cartridgewindow()
myultrafast = UltraFastCommissioning()



#Functions


def startreading():

    #comment if emulator
    readingthread.start()

    myseries.reset()
    time.sleep(1)
    myseries.checkbaseline()
    timer.start(300)

def stopreading():

    #comment if emulator
    readingthread.stopping()

    timer.stop()

    #only if emulator
    #myseries.stopping()


#Create the main app
app = QApplication(sys.argv)
app.setWindowIcon(QIcon("icons/logoonlyspheretransparent.png"))
app.setOrganizationName('BluePhysics')


#create the qml engine
engine = QQmlApplicationEngine()

#create objects in Python and pushthem to qml
#QXYSeries
context = engine.rootContext()
context.setContextProperty("myseries", myseries)
context.setContextProperty("mydarkcurrentthread", mydarkcurrentthread)
context.setContextProperty("mysettingsw", mysettingsw)
context.setContextProperty("regulatethread", regulatethread)
context.setContextProperty("myanalyzew", myanalyzew)
context.setContextProperty("mycartridgew", mycartridgew)
context.setContextProperty("myultrafast", myultrafast)

#Load the qmlfile
engine.load('main.qml')

#get objects from qml engine
startb = engine.rootObjects()[0].findChild(QObject, 'startbutton')
stopb = engine.rootObjects()[0].findChild(QObject, 'stopbutton')



#Signals
startb.clicked.connect(startreading)
stopb.clicked.connect(stopreading)
timer.timeout.connect(myseries.updatepoints)


#Close qml engine if the app is closed
engine.quit.connect(app.quit)
sys.exit(app.exec_())
