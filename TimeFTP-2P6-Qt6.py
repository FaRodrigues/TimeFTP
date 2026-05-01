 # -*- coding: utf-8 -*-
# TimeFTP version 2.6 (2025)
# Autor: Fernando Rodrigues (Inmetro)

import base64
import logging
import os
from pathlib import Path
import shutil
import sys
import subprocess
import threading
from queue import Queue
import time
import xml.etree.ElementTree as ET
from collections import deque
from datetime import datetime as dtime, datetime, timedelta
from threading import Thread, Event
from typing import Union

import numpy as np
import schedule
import winsound

tokenQt = 6
formlayout_width = 800
formlayout_height = 800
formlayout_vertical_spacing = 10
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import QFile, QRect, QPoint, QSize, Qt, QCoreApplication, QObject, QTime
from PySide6.QtGui import QFont
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QFormLayout, QLabel, \
    QHBoxLayout, QLineEdit, QComboBox, QCheckBox, QTimeEdit, QToolButton, QLCDNumber, QDialogButtonBox, \
    QVBoxLayout, QDialog, QFileDialog

from astropy.time import Time
import ConverterClass as Conv
import FileUtilitiesClass as Futil
import TransferFiles as TF
from Calendars import RapidYear
from Global import GlobalVars as Globvar


def getDateTimeFromMJD(mjd_param):
    tmjd = Time(mjd_param, format='mjd')
    stringdate = Time(tmjd.to_value('iso'), out_subfmt='date_hms').iso
    return datetime.fromisoformat(stringdate)

class TaskClass(QObject):
    def __init__(self, dtts, tipo, tmjd, taskmode, parent=None):
        super().__init__(parent)
        self.dtts = dtts
        self.tipo = tipo
        self.tmjd = tmjd
        self.taskmode = taskmode

    def setTaskMode(self, tm):
        self.taskmode = tm

    def getTaskMode(self):
        return self.taskmode

    def setTargetMJD(self, tmjd):
        self.tmjd = tmjd

    def getTargetMJD(self):
        return self.tmjd

    def setTipo(self, tipo):
        self.tipo = tipo

    def getTipo(self):
        return self.tipo

    def setDatetimeTosend(self, dtts):
        self.dtts = dtts

    def getDatetimeTosend(self):
        return self.dtts


class CheckPathDialog(QDialog):
    def __init__(self, mensagem=None):
        super().__init__()
        app_icon_dialog = QtGui.QIcon()
        app_icon_dialog.addFile(os.path.join("gui", "icons", "sad_icon.ico"), QtCore.QSize(256, 256))
        self.setWindowIcon(app_icon_dialog)
        self.setWindowTitle("ERRO!")
        QBtn = QDialogButtonBox.StandardButton.Close
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout = QVBoxLayout()
        messsage = QLabel(mensagem)
        layout.addWidget(messsage)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)


class PreferenceDialog(QDialog):
    def __init__(self, parent=None, caminho=None):
        super().__init__(parent)
        self.setWindowTitle("Definição de preferências!")
        QBtn = QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout = QVBoxLayout()
        self.setStyleSheet("QDialog {background-color: #deebee; color: brown;}")
        message = QLabel("Deseja tornar padrão o diretório: {} ?".format(caminho))
        self.layout.addWidget(message)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)


class CreateDirDialog(QDialog):
    def __init__(self, parent=None, message=None, caminho=None):
        super().__init__(parent)
        app_icon_dialog = QtGui.QIcon()
        app_icon_dialog.addFile(os.path.join("gui", "icons", "smile-icon.ico"), QtCore.QSize(256, 256))
        self.setWindowIcon(app_icon_dialog)
        self.setWindowTitle("ATENÇÃO: Verifique o caminho de log SBF")
        QBtn = QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout = QVBoxLayout()
        self.setStyleSheet("QDialog {background-color: #f0f0f0; color: blue;}")
        self.layout.addWidget(message)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)


def getCirctMJDList(localdatetime):
    refyear = localdatetime.year
    mesref = localdatetime.month
    rapidyear = RapidYear(refyear)
    lista_dias_circT = rapidyear.getCirctMonthList()
    listaplana = deque()
    listaplana.extend(lista_dias_circT)
    numerodias = 7
    listforCircT = []
    for mes in range(1, 13):
        mjdlist = list(listaplana)[0:numerodias]
        if mes == mesref:
            listforCircT = mjdlist
        listaplana.rotate(-(numerodias - 1))
    return listforCircT

def getFramedMessage(midmsg):
    linetext = "*" * (len(midmsg) + 4)
    intermessage = f"\n{linetext}\n{midmsg}\n{linetext}\n"
    return intermessage

def getValueFromChave(root, chavestr):
    elementoxml = root.findall(f"entry[@chave='{chavestr}']")
    return str(elementoxml[0].text)


class MainWindow(QMainWindow, threading.Thread):
    formvalueschecked: bool
    def __init__(self, event, parent=None):
        super().__init__(parent)
        Thread.__init__(self)
        self.configpath = None
        self.lab_id = None
        self.xmllabproproot = None
        self.rx_id = None
        self.gwnr_dict_prop = {}
        self.epoch_index = 0
        self.appversion = None
        self.formvalueschecked = False
        self.layoutminimized = False
        self.xrootgui = None
        self.xtreegui = None
        self.currentyear = None

        self.approccesspath = os.path.join(os.path.expanduser("~"), ".timeftp")
        lab_properties_dir = os.path.join(self.approccesspath, "properties")

        if not os.path.exists(self.approccesspath):
            os.makedirs(self.approccesspath)
        if not os.path.exists(lab_properties_dir):
            os.makedirs(lab_properties_dir)
            Futil.copyXmlPropertyFiles(os.path.join(".", "properties"), lab_properties_dir)
            Globvar.setLabPropertiesDIR(lab_properties_dir)

        if os.path.exists(self.approccesspath):
            Globvar.setAppProcesspath(self.approccesspath)
        else:
            return

        if os.path.exists(lab_properties_dir):
            Globvar.setAppProcesspath(self.approccesspath)

            treeprefs = ET.parse(os.path.join(lab_properties_dir, 'labproperties.xml'))
            ''' verificar salvamento do nó xmllabproproot '''
            self.xmllabproproot = treeprefs.getroot()
            labpropertiesnode = self.xmllabproproot.find("./")
            Globvar.setLabPropertiesNode(self.xmllabproproot)

            self.rx_id = self.xmllabproproot.attrib.get("mainRxID")
            self.lab_id = labpropertiesnode.attrib.get("bipmLabShortPrefix")
            Globvar.setRxID(self.rx_id)
            Globvar.setLabID(self.lab_id)
            # print('self.rx_id = ', self.rx_id)
            receiver_config_dir = os.path.join(Globvar.getAppProcesspath(), self.rx_id, "configuration")
            self.configpath = os.path.join(receiver_config_dir, "configui.xml")
            # self.loadLabProperties(lab_properties_dir)
        else:
            return

        self.context_dict_prop = None
        self.contextlogpath = None
        self.currenttaskclass = None
        self.subprodir = None
        self.stopped = event
        self._stop_event = threading.Event()
        self.rescheduledmjd = {0: False}
        self.dailytaskscheduled = None
        self.dailytasktime = datetime.strptime("00:00:00", '%H:%M:%S').time()
        self.datetimetosend = None
        self.dailytaskstate = None
        self.userhomepath = None
        self.logfilepathname = None
        self.logger = None
        self.dict_prop = {}
        self.rinToCGGproccessDIR = None
        self.trycount = 0
        self.tokensended = {0: False}
        # self.lab_prefix = " "
        self.countup = 0
        self.configtoken = False
        self.startedApp = False
        self.leftwidgetnt = None
        self.processofset = 1
        self.changedformtoken = False
        self.active = False
        self.diaryTaskTime = None
        self.xtree = None
        self.xroot = None
        # self.rxid = None
        self.rootpath = None
        self.labname = None
        self.logpath = None
        self.mjd = 0
        self.doy = 0
        self.shortyear = 0
        self.dataatual = 0
        self.datetimenow = datetime.now()
        self.horarioatual = None
        self.intersend = None
        self.rawScheduledTaskClasses = deque([])
        self.status = None
        self.encodedpass = None
        self.labcode = 0
        self.clockcode = 0
        self.timezonediff = 0
        #
        guipath = os.path.abspath(os.path.join(".", "gui", "ui", "formTime.ui"))
        file = QFile(guipath)
        file.open(QFile.OpenModeFlag.ReadOnly)
        loader = QUiLoader()
        self.ui = loader.load(file, self.window())
        file.close()
        #
        self.statusbar = self.statusBar()
        self.statusbar.setFont(QtGui.QFont('Verdana', 10, QFont.Weight.DemiBold))
        self.statusbar.setSizeGripEnabled(False)
        #
        ## dictGenerateCGGTTS é configurado no carregamento do XML configui.xml
        self.dictGenerateCGGTTS = {
            "G": False,
            "R": False,
            "E": False,
            "C": False
        }

        ################################################################################################################
        '''  Vide RxTools Manual - sbf2rin params | Usado na conversão SBF -> RINEX e RINEX => CGGTTS  '''
        ################################################################################################################

        # self.constraintFileParams = {
        #     "O": ["O", "gps", " "],
        #     "N": ["N", "gps", "ERC"],
        #     "G": ["G", "glo", "GEC"],
        #     "L": ["E", "gal", "GRC"],
        #     "I": ["I", "bds", "GRE"]
        #     }

        # self.constraintFileParams = {
        #     "O": ["O", "gps", " "],
        #     "N": ["N", "gps", " "],
        #     "G": ["G", "glo", " "],
        #     "L": ["E", "gal", " "],
        #     "I": ["I", "bds", " "]
        # }

        self.constraintFileParams = {
            "O": ["O", "gps", " "],
            "N": ["N", "gps", " "],
            "G": ["G", "glo", " "]
        }

        Globvar.setConstraintFileParams(self.constraintFileParams)

        self.btn_state_color = {
            'ready': ['rgb(190, 190, 190)', 'rgb(240,240,240)', 'black', 'bold', False,
                      {'pushButton_1': 'Ativar', 'pushButton_2': 'Configurações', 'pushButton_3': 'Salvar'}],
            "retorna": ['rgb(228,228,228)', 'rgb(240,240,240)', 'black', 'bold', False,
                        {'pushButton_1': 'Ativar', 'pushButton_2': 'Configurações', 'pushButton_3': 'Voltar'}],
            "disabled": ['rgb(228,228,228)', 'rgb(240,240,240)', 'gray', 'bold', True,
                         {'pushButton_1': 'Ativar', 'pushButton_2': 'Configurações', 'pushButton_3': 'Salvar'}],
            "active": ['rgb(190,190,190)', 'rgb(255,255,255)', 'rgb(0,0,156)', 'bold', False,
                       {'pushButton_1': 'Ativar', 'pushButton_2': 'Configurações', 'pushButton_3': 'Salvar'}],
        }
        #
        # self.setWindowTitle("TimeSCP versão 1.6 (2024) | Dmtic | Laboratório de Tempo e Frequência")
        # Busca na UserInterface o objeto referente ao splitter container
        self.btnativa = self.getChildrenObjectUI(QPushButton, 'pushButton_1')
        self.btnconfig = self.getChildrenObjectUI(QPushButton, 'pushButton_2')
        self.btnsalva = self.getChildrenObjectUI(QPushButton, 'pushButton_3')

        self.setBtnState(self.btnativa, 'ready', '')
        self.setBtnState(self.btnconfig, 'ready', '')
        self.setBtnState(self.btnsalva, 'disabled', '')

        self.btnativa.clicked.connect(self.startApp)
        self.btnconfig.clicked.connect(self.configuraApp)
        self.btnsalva.clicked.connect(self.retornaMenu)

        self.lcdNumber_1 = self.getChildrenObjectUI(QLCDNumber, 'lcdNumber_1')
        self.lcdNumber_2 = self.getChildrenObjectUI(QLCDNumber, 'lcdNumber_2')
        self.lcdNumber_3 = self.getChildrenObjectUI(QLCDNumber, 'lcdNumber_3')

        self.styleQLCD = "font-size: 12pt; background-color: rgb(0,0,0); color: {}"

        self.dictQLD = {
            1: ["00:00:00", "gray"],
            2: ["--:--:--", "gray"],
            3: ["00:00", "gray"],
        }

        self.atualizaLCDNumber()
        #
        self.formlayout = self.getChildrenObjectUI(QFormLayout, 'formLayout')
        self.formlayout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.formlayout.setVerticalSpacing(formlayout_vertical_spacing)

        receiver_dir_path = os.path.join(str(self.approccesspath), str(self.rx_id))
        Globvar.setReceiverDIR(receiver_dir_path)

        applogpath = os.path.join(str(receiver_dir_path), "logfiles")

        # Seta a variável global que aponta para applogpath
        self.setAppUserHomePath(os.path.join(applogpath))

        rec_configuration_dir = os.path.join(str(receiver_dir_path), "configuration")
        Globvar.setAppConfigDIR(rec_configuration_dir)

        lab_properties_dir = os.path.join(self.approccesspath, 'properties')
        # print(f"lab_properties_dir = {lab_properties_dir}")
        Globvar.setLabPropertiesDIR(lab_properties_dir)

        # Cria o diretório applogpath caso não exista
        for one_path in [applogpath, rec_configuration_dir, lab_properties_dir]:
            absolute_path = os.path.abspath(one_path)
            if not os.path.exists(absolute_path):
                os.makedirs(absolute_path)

        tokentransfere = False  # token booleano para transferência de arquivos XML para configuration

        # Caso o caminho appxmlproppath não exista, cria o caminho e copia os arquivos xml
        # **************************************************************************************************************
        # ****************************************   Atenção  **********************************************************
        # Os arquivos XML são copiados na ausência de appxmlproppath ao iniciar
        # ou quando o número de arquivos XML em configuration é menor que 3
        # **************************************************************************************************************
        # **************************************************************************************************************

        xmlguipath = os.path.join(rec_configuration_dir, 'configui.xml')
        client_profile_path = os.path.join(rec_configuration_dir, 'clientprofiles.xml')

        for path_item in [xmlguipath, client_profile_path]:
            if not os.path.exists(path_item):
                print(f"Erro: O arquivo {path_item} não foi encontrado!")
                time.sleep(0.2)
                origem = os.path.abspath(os.path.join(".", "configuration", Path(path_item).name))
                destino = os.path.join(rec_configuration_dir, Path(path_item).name)
                print(f"Copiando o arquivo {origem} para {destino}!")
                shutil.copy(origem, destino)

        # serializa o arquivo XML contendo os perfis
        clientprofilepath = os.path.join(Globvar.getAppConfigDIR(), "clientprofiles.xml")

        tokenconfigprofile = False

        if os.path.exists(clientprofilepath):
            clientprofiles = ET.parse(clientprofilepath)
            self.xmlprofilesroot = clientprofiles.getroot()
            Globvar.setClientProfileNode(self.xmlprofilesroot)
            tokenconfigprofile = True

        if tokenconfigprofile:

            self.dailytaskstatedict = {
                0: [0, "Não Agendado"],
                1: [1, "Agendado"],
                2: [2, "ReAgendado"],
                3: [3, "Tentativa de envio diário sem sucesso"],
                4: [4, "Tentativa de envio diário com sucesso"]
            }

            self.dictTaskClasses = {
                0: "PARTIAL",
                1: "FULL",
            }

            Globvar.setDictTaskClasses(self.dictTaskClasses)

            #############################################################################################################
            #############################################################################################################
            ''' Em caso de GPS Week Number Rollover, setGwnrFactor define o intervalo de dias entre GNSS time e Local '''
            Globvar.setGwnrFactor(0)
            #############################################################################################################
            #############################################################################################################

            self.setDailyTaskState(0)
            self.serializeXML(False)

            # Carrega os valores dos nós XML que compõem o caminho de LOG SBF e atualiza na memória
            self.updateAppLogDirFromXML(True)

            # Define o nome dos subprogramas do RxTools em função do sistema operacional

            if "win" in sys.platform:
                sbf2rinprogparam = [True, 'sbf2rin.exe']
                sbf2cggttsprogparam = [True, 'sbf2cggtts.exe']
                rin2cggexeprogparam = [True, 'R2CGGTTSV8P3.exe']
            else:
                sbf2rinprogparam = [False, 'sbf2rin']
                sbf2cggttsprogparam = [False, 'sbf2cggtts']
                rin2cggexeprogparam = [False, 'R2CGGTTSV8P3']

            Globvar.setSbf2RinProgParam(sbf2rinprogparam)
            Globvar.setSbf2CggttsProgParam(sbf2cggttsprogparam)
            Globvar.setRin2CggexePathParam(rin2cggexeprogparam)
        else:
            message = f"Erro: Arquivos de configuração não encontrados em {clientprofilepath}!"
            self.atualizaStatusBar(message, 'red', 'bold')
            self.disableAppMenu()
            self.closeEvent(False)

        # epochlag is the time the software to process data after the estimated CGGTTS epoch
        epochlag = 60 # em segundos
        Globvar.setEpochAdjust(epochlag)

    #################################################################################################################

    def loadLabProperties(self, path):
        # print('loadLabProperties path = ', path)
        if path is None or Globvar.getAppProcesspath() is None:
            # Define as propriedades do lab GNSS
            treeprefs = ET.parse(os.path.join(".", "properties", "labproperties.xml"))
        else:
            Globvar.setLabPropertiesDIR(path)
            treeprefs = ET.parse(os.path.join(path, 'labproperties.xml'))

        ''' verificar salvamento do nó xmllabproproot '''
        self.xmllabproproot = treeprefs.getroot()
        labpropertiesnode = self.xmllabproproot.find("./")
        Globvar.setLabPropertiesNode(self.xmllabproproot)

        self.rx_id = self.xmllabproproot.attrib.get("mainRxID")
        self.lab_id = labpropertiesnode.attrib.get("bipmLabShortPrefix")
        Globvar.setRxID(self.rx_id)
        Globvar.setLabID(self.lab_id)
        # print('self.rx_id = ', self.rx_id)
        receiver_config_dir = os.path.join(Globvar.getAppProcesspath(), self.rx_id, "configuration")
        self.configpath = os.path.join(receiver_config_dir, "configui.xml")

    def setDailytasktime(self, dtt):
        self.dailytasktime = dtt

    def getDailytasktime(self):
        return self.dailytasktime

    def disableAppMenu(self):
        self.setWindowTitle("TimeFTP | TimeSCP")
        self.setBtnState(self.btnativa, 'disabled', '')
        self.setBtnState(self.btnconfig, 'disabled', '')

    def configuraApp(self):
        self.serializeXML(True)
        self.setBtnState(self.btnativa, 'ready', '')
        self.setBtnState(self.btnconfig, 'disabled', '')
        self.setBtnState(self.btnsalva, 'ready', 'Voltar')

    def setBtnState(self, obj, btn_state, state_text):
        btn_style = self.btn_state_color[btn_state]
        obj.setStyleSheet(
            pusbutton_style.format(bkcor=btn_style[0], border_color=btn_style[1], cor=btn_style[2], peso=btn_style[3]))
        obj.setDisabled(btn_style[4])
        if len(state_text) < 1:
            obj.setText(btn_style[5][obj.objectName()])
        else:
            obj.setText(state_text)

    def setLayoutMinimized(self, se):
        self.layoutminimized = se

    def isLayoutMinimized(self):
        return self.layoutminimized

    def getChildrenObjectUI(self, objtype, chave):
        return list(self.ui.findChildren(objtype, chave))[0]

    def run(self):
        try:
            while not self.stopped.wait(0.125):
                self.updateTimeProperties()
        except KeyboardInterrupt as e:
            self.setLogInfo(f"Aplicação encerrada!\n{e}")

    def setScheduling(self, scc):
        self.rawScheduledTaskClasses = scc

    def getScheduling(self):
        return self.rawScheduledTaskClasses

    def setDailyDatetimeToSend(self, ddtts, schedule_state):
        self.datetimetosend = ddtts
        self.setDailyTaskState(schedule_state)

    def getDailyDatetimeToSend(self):
        return self.datetimetosend

    def setDailyTaskState(self, dts):
        # Seta a variável self.dailytaskstate com uma chave e um valor do dict self.dailytaskstatedict
        self.dailytaskstate = self.dailytaskstatedict[dts]
        # definidos  1: [1, "Agendado"], 2: [2, "ReAgendado"] em self.dailytaskstatedict
        if dts in [1, 2]:
            self.setDailyTaskScheduled(True)

    def getDailyTaskState(self):
        return self.dailytaskstate[0]

    def reScheduleDailyTasks(self, mjd, dttime):
        print("reScheduleDailyTasks")
        agoraUTC = self.datetimenow
        # if agoraUTC > self.getDailyDatetimeToSend():
        #     plusdays_for_schedule = 1
        # else:
        plusdays_for_schedule = 0

        datetimepostponed = agoraUTC + timedelta(days=plusdays_for_schedule)
        newdatetimetosend = datetimepostponed.replace(hour=dttime.hour, minute=dttime.minute)

        print(f"newdatetimetosend = {newdatetimetosend}")

        taskstate = 2  # definido [ReAgendado] em self.dailytaskstatedict
        self.setDailyDatetimeToSend(newdatetimetosend, taskstate)
        self.rescheduledmjd[mjd] = True
        ######################################################################################################
        Globvar.resetCountError()
        ######################################################################################################
        message = f"O envio diário de arquivos para o BIPM [ MJD = {mjd} ] foi reagendado para {newdatetimetosend}"
        print(getFramedMessage(message))
        self.setLogWarning(message)
        # Retorna o OFFSET ao valor 1
        self.setProccessOfset(0)
        ######################################################################################################
        Globvar.setEpochAdjusted(False)  # Allow the function getFirstSttimeFromCggtts in checkIntraDayTasks
        Globvar.setEpochAdjust(60)
        ######################################################################################################
        self.generateSchedule(True, False, 0, True)

    def getRescheduledMJD(self, mjd):
        if mjd in self.rescheduledmjd.keys():
            resp = self.rescheduledmjd[mjd]
        else:
            resp = False
        return resp

    def openfiledialog(self):
        savetoxml = False
        # Seleciona o disco com base no diretório raiz
        try:
            approotdir = os.path.dirname(self.getRootPath())
        except ValueError as ve:
            approotdir = "C:\\"
            self.setLogWarning(str(ve))

        filedialog = QFileDialog.getExistingDirectory(self, "Selecione o diretório raiz", approotdir,
                                                      QFileDialog.Option.ShowDirsOnly)
        try:
            sfd = str(filedialog)
            if len(filedialog) < 2:
                pass
            else:
                # Verifica se a seleção atual é diferente do atual approotdir
                if sfd != self.getRootPath():
                    directory = os.path.abspath(sfd)
                    prefdiag = PreferenceDialog(self, caminho=sfd)
                    msgBoxResult = prefdiag.exec()
                    if msgBoxResult == 0:
                        savetoxml = True
                    elif msgBoxResult == 1:
                        savetoxml = True
                    # Carrega o valor do diretório e atualiza interface gráfica
                    self.setRootPath('{}'.format(os.path.abspath(directory)))
                    self.atualizaStatusBar('Atualizando a propriedade approotdir = {}'.format(directory),
                                           "rgb(128, 128, 128)", "normal")
                    self.saveXMLNode('root_disk', directory, savetoxml)
                    toolButtonForROOT = self.getChildrenObjectUI(QToolButton, 'root_disk')
                    toolButtonForROOT.setText('{}'.format(directory))
                    self.formlayout.update()
                    QtCore.QCoreApplication.processEvents()
        except ValueError as ve:
            self.atualizaStatusBar(f'Erro ao definir o diretório raiz!\n{ve}', "rgb(128, 128, 128)", "bold")

    def setCurrentYEAR(self, cy):
        self.currentyear = cy

    def getCurrentYEAR(self):
        return self.currentyear

    def setShortYEAR(self, shortyear):
        self.shortyear = shortyear

    def getShortYEAR(self):
        return self.shortyear

    def setCurrentMJD(self, mjd):
        self.mjd = mjd

    def getCurrentMJD(self):
        return self.mjd

    def setCurrentDOY(self, doy):
        self.doy = doy

    def getCurrentDOY(self):
        return self.doy

    def setLabCode(self, labcode):
        self.labcode = labcode

    def getLabCode(self):
        return self.labcode

    def setClockCode(self, clkcode):
        self.clockcode = clkcode

    def getClockCode(self):
        return self.clockcode

    def setTokenSended(self, chave, valor):
        self.tokensended[chave] = valor

    def getTokenSended(self, chave):
        if chave in self.tokensended.keys():
            resp = self.tokensended[chave]
        else:
            resp = False
        return resp

    def updatelogFromResp(self, lista):
        resptokenList = []
        if lista is not None:
            fila = deque()
            fila.extend(lista)
            while len(fila) > 0:
                respin = fila.popleft()
                selista = type(respin).__name__ == "list"
                if selista:
                    tamlista = len(respin)

                    if tamlista == 2:
                        token = respin[0]
                        if token:
                            self.setLogInfo("{}".format(respin[1]))
                        else:
                            self.setLogError("{}".format(respin[1]))
                    else:
                        token = self.updatelogFromResp(respin)
                    resptokenList.append(token)
        else:
            resptokenList = [False]

        return all(res is True for res in resptokenList)

    def updateTimeProperties(self):
        global strei, context_task, contexttaskclass, nextdatetime, contexttaskmode
        appstate = self.getStartingAppState()
        dttime = self.getDailytasktime()
        dtstate = self.getDailyTaskState()
        scheduling = self.getScheduling()
        self.countup += 1
        # Define the local time
        tzd = self.getTimeZoneDiff()
        self.datetimenow = dtime.now() + timedelta(hours=tzd)
        self.horarioatual = self.datetimenow.time()
        self.dictQLD[1] = [self.horarioatual, ""]
        self.atualizaLCDNumber()
        QtCore.QCoreApplication.processEvents()

        if dtstate in [0, 2]:
            self.dictQLD[3] = [dttime, "gray"]
        if self.isDailyTaskScheduled():
            self.dictQLD[3] = [dttime, "rgb(228,228,228)"]

        self.atualizaLCDNumber()

        self.dataatual = self.datetimenow.date()
        currentyear = self.dataatual.year
        self.setCurrentYEAR(currentyear)
        shortyear = currentyear - 2000
        self.setShortYEAR(shortyear)
        doy = self.datetimenow.timetuple().tm_yday
        self.setCurrentDOY(doy)
        # print(f"horário = {self.horarioatual} | data = {self.dataatual} | shortyear = {shortyear} | doy = {doy} ")
        data1 = Time(str(self.datetimenow))
        mjd = int(data1.to_value('mjd'))
        self.setCurrentMJD(mjd)
        Globvar.setCurrentMJD(mjd)
        appmode = Globvar.getAppMode()
        context_message = Globvar.getContextMessage()

        # print(f"appstate = {appstate} | self.countup = {self.countup}")

        task_num_remains = scheduling.__len__()

        if appstate and self.countup > 2 and task_num_remains > 0:
            # Define a diferença entre a data GWNR e a data atual
            gwnrfactor = Globvar.getGwnrFactor()
            # Define o proccess_offset do contador
            proccess_offset = self.getProccessOfset()

            if proccess_offset > 0 and not Globvar.isProcessOffsetMode():
                tokenPO = self.scheduleProcessOfsetTask(proccess_offset, mjd, gwnrfactor)
                if tokenPO: Globvar.setProcessOffsetMode(True)

                if not self.isDailyTaskScheduled():
                    candidateDailydatetime = self.datetimenow.replace(hour=dttime.hour, minute=dttime.minute, second=dttime.second)
                    self.setDailyDatetimeToSend(candidateDailydatetime, 1)

            context_task = scheduling[0]
            nextdatetime = context_task.getDatetimeTosend()
            nexttime = nextdatetime.time()
            # print(f"nexttime = {nexttime}")
            contexttaskclass = context_task.getTipo()
            contexttaskmode = context_task.getTaskMode()
            self.setCurrentTaskClass(contexttaskclass)
            # print(f"contexttaskmode = {contexttaskmode} | len(scheduling)  = {len(scheduling)} | contexttaskclass = {contexttaskclass} | nexttime = {nexttime}")
            # Considerando que a data de envio ocorre no mjd seguinte o alvo da transmissão Full é o mjd anterior
            target_mjd = context_task.getTargetMJD()
            num_try = 1

            # print(f"task_num_remains = {task_num_remains} | self.countup = {self.countup}")

            if self.countup == 2 or self.countup % 12 == 0:

                # Define the index of the CGGTTS epoch
                if self.getEpochIndex() == 0:
                    strei = "FIRST"
                elif self.getEpochIndex() == -1:
                    strei = "LAST"

                # Verifica se a tarefa é do tipo "Full" e realiza tarefas diárias
                if contexttaskclass == self.dictTaskClasses[1]:
                    # token_for_rescheduling = False
                    daily_target_mjd = target_mjd - 1

                    cor = "rgb(228,228,228)"
                    self.dictQLD[2] = [nexttime, cor]

                    message = f"Operando com tarefas diárias " \
                              f"programadas para {nexttime} UTC | GWNR = {gwnrfactor} | {strei} EPOCH = {Globvar.getEpochAdjust()} s "

                    Globvar.setContextMessage([message, 'rgb(48,232,232)', 'bold'])

                    if self.datetimenow >= nextdatetime or (proccess_offset > 0):

                        for self.trycount in range(num_try):
                            self.trycount += 1

                            if contexttaskmode == "OFFSET":
                                # daily_target_mjd = target_mjd
                                gwnr_mjd = daily_target_mjd - Globvar.getGwnrFactor()
                                message = f"Iniciando o processamento com OFFSET = {proccess_offset} para o MJD {gwnr_mjd} => {daily_target_mjd}"
                                self.dictQLD[2] = ["PO:{:02d}".format(proccess_offset), "rgb(255, 192, 48)"]
                                self.atualizaLCDNumber()
                                tokenOFFSET = True
                            else:
                                Globvar.setProcessOffsetMode(False)
                                gwnr_mjd = daily_target_mjd - Globvar.getGwnrFactor() # FULL task for the day before
                                cor = "blue"
                                self.dictQLD[2] = [nexttime, cor]
                                message = f"Iniciando a tentativa {self.trycount} para realização de tarefas diárias | MJD = [ {daily_target_mjd} ]"
                                tokenOFFSET = False

                            self.atualizaStatusBar(message, "rgb(48, 228, 228)", "bold")
                            print(getFramedMessage(message))
                            self.setLogInfo(message)
                            # Creates a queue to store the result
                            result_queue = Queue()
                            thread = Thread(target=self.checkThreadDailyTimerTasks, args=(self.trycount, daily_target_mjd, result_queue))
                            thread.start()
                            thread.join()
                            # Get the result from Thread
                            resposta = result_queue.get()
                            tokensuccess = self.updatelogFromResp(resposta)
                            # print(f"tokensuccess = {tokensuccess}")
                            # tokensuccess = False

                            if tokensuccess:
                                self.setDailyTaskState(4)
                                message = f"O processamento com OFFSET = {proccess_offset} de arquivos foi concluído com SUCESSO para o MJD {gwnr_mjd} => {daily_target_mjd}"
                                self.setLogInfo(message)
                                Globvar.setContextMessage([message, 'white', 'normal'])
                            else:
                                self.setDailyTaskState(3)
                                message = f"Não foi possível realizar o processamento com [ OFFSET = {proccess_offset} ] para o MJD {gwnr_mjd} => {daily_target_mjd}"
                                self.setLogError(message)
                                Globvar.setContextMessage([message, 'red', 'normal'])
                                # token_for_rescheduling = True

                            print(getFramedMessage(message))

                            self.dictQLD[1] = [self.horarioatual, "white"]
                            self.atualizaLCDNumber()

                            message = f"Realizando a tarefa com OFFSET = {proccess_offset} e GWNR = {gwnrfactor} para o MJD {gwnr_mjd} => {daily_target_mjd}"
                            self.setLogInfo(message)
                            Globvar.setContextMessage([message, 'white', 'normal'])
                            self.atualizaStatusBar(message, "rgb(48, 228, 228)", "bold")

                            # print(f"self.trycount = {self.trycount} | dttime = {dttime} | {self.getRescheduledMJD(daily_target_mjd)}")

                            if tokenOFFSET:
                                self.dictQLD[2] = ["PO:{:02d}".format(proccess_offset), "rgb(255, 192, 48)"]
                                # self.rawScheduledTaskClasses.popleft()
                                if proccess_offset > 0:
                                    proccess_offset = proccess_offset - 1
                                    self.saveXMLNode("process_offset", proccess_offset, True)
                                    self.setProccessOfset(proccess_offset)
                                # else:
                                #     self.saveXMLNode("process_offset", proccess_offset, True)

                            # number_thread.join()

                            self.rawScheduledTaskClasses.popleft()

                        # if token_for_rescheduling:
                        #     self.reScheduleDailyTasks(mjd, dttime)

                # Verifica se a tarefa é do tipo "Partial" e realiza tarefas intermediária
                elif contexttaskclass == self.dictTaskClasses[0]:

                    daily_target_mjd = target_mjd
                    gwnr_mjd = daily_target_mjd - Globvar.getGwnrFactor()

                    cor = "rgb(192,192,192)"
                    self.dictQLD[2] = [nexttime, cor]

                    part_difftime = (nextdatetime - self.datetimenow).seconds
                    base_interval = 86400 / self.getIntersend()

                    if part_difftime < 0:
                        print(f"part_difftime = {part_difftime} | base_interval = {base_interval} | Removing old task programed to {nextdatetime}")
                        self.rawScheduledTaskClasses.popleft()
                        winsound.Beep(1500, 1000)
                        # time.sleep(10)

                    message = f"O Time{appmode} está operando com {task_num_remains} tarefas intermediárias " \
                              f"pendentes! | GWNR = {gwnrfactor} | {strei} EPOCH = {Globvar.getEpochAdjust()} s "

                    Globvar.setContextMessage([message, 'rgb(48,232,232)', 'bold'])

                    tasknumberdone = self.getIntersend() - task_num_remains

                    '''
                    lastCountForPartial define o número mínimo de tarefas em self.rawScheduledTaskClasses
                    para o qual o tratamento de uma tarefa 'Partial' é considerado - dessa forma sempre sobrará uma 
                    tarefa não 'Partial', ou seja, uma tarefa 'Full'
                    '''

                    lastCountForPartial = 0

                    tasknumbertodo = task_num_remains + lastCountForPartial
                    # print(f"tasknumbertodo = {tasknumbertodo}")

                    if tasknumbertodo >= lastCountForPartial:
                        # print(f"task_num_remains = {task_num_remains}")
                        cor = "gray"
                        self.dictQLD[2] = [nexttime, cor]
                        self.atualizaLCDNumber()

                        if self.active and self.datetimenow >= nextdatetime:
                            cor = "green"
                            self.dictQLD[2] = [nexttime, cor]
                            message = f"Iniciando a realização da tarefa parcial {tasknumbertodo} para o MJD [ {mjd} ]"
                            self.setLogInfo(message)
                            Globvar.setContextMessage([message, 'white', 'normal'])
                            # print(message)
                            resposta = self.checkIntraDayTasks()
                            # print(f"resposta checkIntraDayTasks = {resposta}")
                            tokensuccess = self.updatelogFromResp(resposta)
                            # print(f"tokensuccess = {tokensuccess}")

                            if tokensuccess:
                                pass
                                # self.setTokenSended(mjd, True)
                                Globvar.setTokenError(False)
                            else:
                                message = f"A tarefa parcial {tasknumberdone} não foi realizada para o MJD {gwnr_mjd} => {daily_target_mjd}!"
                                Globvar.setContextMessage([message, 'red', 'normal'])
                                self.setLogError("{}".format(message))
                                Globvar.setTokenError(True)
                                # print(f"{message}\n{resposta}")

                            self.countup = 0

                    elif proccess_offset < 1:
                        self.setProccessOfset(0)

                    if self.countup > 30:
                        self.atualizaStatusBar(self.getAppStatus(), "rgb(228, 228, 228)", "normal")
                        self.countup = 0

            self.atualizaLCDNumber()
            # schedule.run_pending()
            # if self.countup % 20 == 0:
            #     # print(self.horarioatual)
            #     hora1 = datetime.strptime(f"{dttime}", "%H:%M:%S")
            #     hora2 = datetime.strptime(f"{self.horarioatual.isoformat(timespec='seconds')}", "%H:%M:%S")
            #     print(f"diferedttime = {(hora1 - hora2).total_seconds()/60}")
            #     # print(f"schedule.run_pending() {schedule.get_jobs()}")

        else:
            if self.countup % 20 == 0:
                # print(self.horarioatual)
                message = f"Aguardando intervalo para agendamento!"
                self.dictQLD[2] = ["--:--:--", "gray"]
                Globvar.setContextMessage([message, 'red', 'normal'])
                hora1 = datetime.strptime(f"{dttime}", "%H:%M:%S")
                hora2 = datetime.strptime(f"{self.horarioatual.isoformat(timespec='seconds')}", "%H:%M:%S")
                diferedttime = (hora1 - hora2).total_seconds() / 60
                # print(f"diferedttime = {diferedttime} | mjd = {mjd}")
                # print(f"schedule.run_pending() {schedule.get_jobs()}")
                # print(f"self.getRescheduledMJD(mjd) = {self.getRescheduledMJD(mjd)}")
                if 0 < diferedttime < 20 and self.getRescheduledMJD(mjd) == False:
                    self.reScheduleDailyTasks(mjd, dttime)
            #############################################################################

        if self.countup % 8 == 0:
            if not appstate:
                Globvar.setContextMessage(['Em espera', 'rgb(48,200,200)', 'bold'])
            else:
                self.atualizaStatusBar(context_message[0], context_message[1], "normal")

        dictup = {'datetimeagora': self.datetimenow, "data": self.dataatual, "shortyear": shortyear, "doy": doy,
                  "mjd": mjd}
        return dictup

    ####################################################################################################################

    def scheduleProcessOfsetTask(self, proccess_offset, mjd, gwnrfactor):
        mjdrange = range(mjd, (mjd - proccess_offset), -1) # Reverse range to append left
        '''
        Criar uma lista de caminhos válidos usando MJD para calcular year e doy.
        Guardar os indices dos caminhos válidos junto com o MJD
        Exemplo: deque([60236: 90, 60240: 86])
        Usar o índice válido (val_index) para setar setProccessOfset(val_index)
        '''
        for po_mjd in mjdrange:
            dtttosend = getDateTimeFromMJD(po_mjd)
            taskFullPO = TaskClass(dtts=dtttosend, tipo=self.dictTaskClasses[1], tmjd=po_mjd, taskmode='OFFSET')
            self.rawScheduledTaskClasses.appendleft(taskFullPO)
        return True

    ####################################################################################################################

    def setIntersend(self, num):
        self.intersend = num

    def setActiveState(self, se):
        self.active = se

    def getActiveState(self):
        return self.active

    def getIntersend(self):
        return self.intersend

    def getIntValueFromString(self, txt):
        valor = 1
        try:
            valor = int(txt)
            self.setFormValuesChecked(True)
        except ValueError as e:
            message = f"Valor {txt} está em desacordo com o formulário!\n{e}"
            # self.stopApp(False)
            self.setFormValuesChecked(False)
            self.atualizaStatusBar(message, 'red', 'normal')
        return valor

    def serializeXML(self, mostra):
        # print("serializeXML:", self.objectName(), mostra)
        properties_path = os.path.join(Globvar.getAppProcesspath(), 'properties', 'labproperties.xml')
        properties_xml = ET.parse(properties_path)
        # properties_root = properties_xml.getroot()
        # print(properties_root.get("mainRxID"))

        leftwidget = None
        if self.formlayout.rowCount() <= 1:
            try:
                self.configpath = os.path.join(Globvar.getAppConfigDIR(), "configui.xml")
                # print(f"configpath = {self.configpath}")
                self.xtree = ET.parse(self.configpath)
                self.xroot = self.xtree.getroot()
                self.appversion = " "
                try:
                    self.appversion = self.xroot.attrib["version"]
                except BaseException as error:
                    print(f"ERRO = {error}")
                    pass

                for nodexml in self.xroot.findall('entry'):
                    tokenabled = True
                    attr = nodexml.attrib
                    desc = attr.get('desc')
                    chave = attr.get('chave').strip()
                    render = attr.get('render').strip()

                    if nodexml.text is not None:
                        txt = nodexml.text.strip()
                    else:
                        txt = " "

                    if type(desc).__name__ == "str":
                        btn = QLabel(f"{desc}")
                        if render == "QComboBox":
                            leftwidget = QComboBox()
                            if chave == "tx_modo":
                                listoption = ['FTP', 'SCP']
                                leftwidget.addItems(listoption)
                                currentindex = listoption.index(f"{txt}")
                                leftwidget.setCurrentIndex(currentindex)
                                leftwidget.setProperty("datamodel", listoption)
                                leftwidget.currentIndexChanged.connect(self.changedForm)
                                currenttext = leftwidget.currentText()
                                Globvar.setAppMode(currenttext)
                            elif chave == "epoch_id":
                                listoption = {'Primeiro': '0', 'Último': '-1'}
                                currentKeysTextList = list(listoption.keys())
                                currentEpocIndexList = list(listoption.values())
                                leftwidget.addItems(currentKeysTextList)
                                currentQCindex = currentKeysTextList.index(f"{txt}")
                                leftwidget.setCurrentIndex(currentQCindex)
                                leftwidget.setProperty("datamodel", listoption)
                                leftwidget.currentIndexChanged.connect(self.changedForm)
                                currentSTTIMEIndex = currentEpocIndexList[currentQCindex]
                                valor = self.getIntValueFromString(currentSTTIMEIndex)
                                self.setEpochIndex(valor)
                        if render == "QToolButton":
                            leftwidget = QToolButton()
                            leftwidget.setText(f"{txt}")
                            leftwidget.pressed.connect(self.changedForm)
                            if chave == "root_disk":
                                rootpath = os.path.abspath(txt)
                                self.setRootPath(rootpath)
                                leftwidget.clicked.connect(self.openfiledialog)
                                Globvar.setRootPath(rootpath)
                        elif render == "QPushButton":
                            leftwidget = QPushButton(f"{txt}")
                            leftwidget.clicked.connect(self.changedForm)
                        elif render == "QCheckBox":
                            leftwidget = QCheckBox()
                            transmitparam = False
                            if txt.lower() == "true":
                                transmitparam = True
                                leftwidget.setChecked(transmitparam)
                                Globvar.setRinexZipped(transmitparam)
                            leftwidget.clicked.connect(self.changedForm)
                            if chave in self.dictGenerateCGGTTS.keys():
                                self.dictGenerateCGGTTS[chave] = transmitparam
                                Globvar.setDictGenerateCGGTTS(self.dictGenerateCGGTTS)
                        elif render == "QTimeEdit":
                            pass
                            leftwidget = QTimeEdit()
                            dailytt = datetime.strptime(txt, '%H:%M:%S').time()
                            self.setDailytasktime(dailytt)
                            newqtime = QTime(dailytt.hour, dailytt.minute)
                            self.dictQLD[3] = [dailytt, ""]
                            leftwidget.setDisplayFormat("HH:mm:ss")
                            leftwidget.setTime(newqtime)
                            # # Carrega a hora atual
                            # currenttime = self.datetimenow.time()
                            # # Carrega a data atual
                            # newdatetosend = self.datetimenow.date()
                            # # Se a hora atual for maior que a hora de envio adiciona 1 dia à newdatetosend
                            # if currenttime > dailytt:
                            #     newdatetosend += timedelta(days=1)
                            # # Define a variável newdatetimetosend
                            # newdatetimetosend = datetime.combine(newdatetosend, dailytt)
                            #
                            # taskstate = 0  # definido em self.dailytaskstatedict
                            # self.setDailyDatetimeToSend(newdatetimetosend, taskstate)
                            leftwidget.timeChanged.connect(self.changedForm)
                        elif render == "QLineEdit":
                            leftwidget = QLineEdit(f"{txt}")
                            if chave in ["appPassword", "pass_inm"]:
                                leftwidget.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
                            if chave == "lab_name":
                                self.setLabName(txt)
                                Globvar.setLabName(txt)
                            elif chave == "lab_id":
                                self.setLabID(txt)
                                Globvar.setLabID(txt)
                            elif chave == "rx_id":
                                self.setRxID(txt)
                                Globvar.setRxID(txt)
                                # Define o receptor atual como principal
                                self.xmllabproproot = Globvar.getLabPropertiesNode()
                                self.xmllabproproot.set("mainRxID", txt)
                                # print(txt)
                                # self.saveLabPropXML()
                            elif chave == "rin2cgg_dir":
                                self.setRinToCGGproccessDIR(txt)
                            elif chave == "subprog_dir":
                                Globvar.setSubProgDIR(txt)
                            elif chave == "local_sbf_to_inm":
                                Globvar.setSBFLogDIR(txt)
                            elif chave == "local_cggtts_to_inm":
                                Globvar.setCGGTTSLogDIR(txt)
                            elif chave == "local_rinex_to_inm":
                                Globvar.setRinexLogDIR(txt)
                            elif chave == "store_rinex_to_inm":
                                Globvar.setRinexLinksDIR(txt)
                            elif chave == "store_cggtts_to_inm":
                                Globvar.setCggttsLinksDIR(txt)
                            elif chave == "store_clockdata_to_inm":
                                Globvar.setClockLinksDIR(txt)
                            elif chave == "num_tasks":
                                valor = self.getIntValueFromString(txt)
                                self.setIntersend(valor)
                            elif chave == "process_offset":
                                valor = self.getIntValueFromString(txt)
                                self.setProccessOfset(valor)
                            elif chave == "gwnr_polarx":
                                valor = self.getIntValueFromString(txt)
                                Globvar.setGwnrFactor(valor)
                            elif chave == "lab_code":
                                self.setLabCode(txt)
                                Globvar.setLabCode(txt)
                                tokenabled = False
                            elif chave == "clock_code":
                                self.setClockCode(txt)
                                Globvar.setClockCode(txt)
                                tokenabled = False

                            # Define o signal associado ao widget
                            leftwidget.textChanged.connect(self.changedForm)
                            leftwidget.setEnabled(tokenabled)
                        #
                        rectbtn = QRect(0, 0, 220, 22)
                        vbox = QHBoxLayout()
                        vbox.addWidget(btn)
                        leftwidget.setObjectName(chave)
                        leftwidget.setProperty("chave", chave)
                        vbox.addWidget(leftwidget)
                        vbox.setGeometry(rectbtn)
                    if mostra:
                        self.formlayout.addRow(f"{desc} :", leftwidget)
            except ET.ParseError as ex:
                print(f"ERRO: {ex}")

        app_mode = Globvar.getAppMode()

        longlabname = Globvar.getLabPropertiesNode().find('identifier').get('desc')

        self.setWindowTitle(
            "Time{} versão {} (2025)".format(app_mode, self.appversion) + " | " + "Inmetro <-> {}".format(
                longlabname))

        # Define the UTC time zone of the local clock
        try:
            tzdnode = Globvar.getLabPropertiesNode().find('utctimezone')
            if tzdnode is not None:
                self.setTimeZoneDiff(int(tzdnode.text))
        except Union[ValueError, AttributeError] as ve:
            self.setLogError(ve)
            self.setTimeZoneDiff(-3)

        self.configtoken = True
        self.atualizaLCDNumber()
        self.atualizaQLCDStyle()
        self.generateDictPropAndLogPath()

        if mostra:
            rectbtn = QRect(100, 100, formlayout_width, formlayout_height)
            self.setGeometry(rectbtn)
            self.setFixedSize(formlayout_width, formlayout_height)
            self.formlayout.update()
            self.setLayoutMinimized(False)
        else:
            self.setLayoutMinimized(True)

        self.setAppStatus("Menu [ Configurações ] selecionado")
        self.atualizaStatusBar(self.getAppStatus(), "rgb(128, 128, 128)", "normal")

    def saveLabPropXML(self):
        appxmlproppath = os.path.join(self.approccesspath, "properties")
        # print(f"appxmlproppath = {appxmlproppath}")
        self.loadLabProperties(appxmlproppath)
        # self.xmllabproproot = Globvar.getLabPropertiesNode()
        treepropcandidate = ET.ElementTree(self.xmllabproproot)
        # print(f"Globvar.getAppConfigDIR() = {Globvar.getAppConfigDIR()}")
        treepropcandidate.write(os.path.join(Globvar.getAppConfigDIR(), "labproperties.xml"), encoding="utf-8",
                                xml_declaration=True)

    def saveXMLNode(self, chave, valor, tofile):
        # print(f"chave = {chave} | valor = {valor} | tofile = {tofile}")
        elementoxml = self.xroot.findall(f"entry[@chave='{chave}']")
        elementoxml[0].text = str(valor)
        if tofile:
            self.saveXMLConfigGui()

    def saveXMLConfigGui(self):
        # print("saveXMLConfigGui")
        se = self.updateAppLogDirFromXML(False)
        if se:
            self.xroot.set(f"timestamp", f"{self.datetimenow.isoformat()}")
            treecandidate = ET.ElementTree(self.xroot)
            # print(f"Globvar.getAppConfigDIR() em saveXMLConfigGui = {Globvar.getAppConfigDIR()}")
            treecandidate.write(os.path.join(Globvar.getAppConfigDIR(), "configui.xml"), encoding="utf-8",
                                xml_declaration=True)
            # self.saveLabPropXML()
            # self.updateAppLogDirFromXML(True)

    def saveXMLProfileFile(self):
        # print("saveXMLProfileFile")
        # *************************************************************************************************************
        # Salva as informações pertinentes do formulário self.xroot no arquivo XML clientprofiles.xml
        # *************************************************************************************************************
        # Busca o nó XML que armazena clientprofiles.xml na memória
        clientprofilesxmlnode = Globvar.getClientProfileNode()

        buscatxmodo = self.xroot.findall(f"entry[@chave='tx_modo']")
        txmodo = buscatxmodo[0].text
        buscalabuser = self.xroot.findall(f"entry[@chave='lab_name']")
        labuser = buscalabuser[0].text
        buscaappuser = self.xroot.findall(f"entry[@chave='appUser']")
        appuser = buscaappuser[0].text

        profilechildnode = clientprofilesxmlnode.find('profile')
        profilechildnode.set('labname', labuser)
        profilechildnode.set('commtype', txmodo)

        # Busca o nó XML que armazena url_scp_inm
        buscaccesslink = self.xroot.findall(f"entry[@chave='url_scp_inm']")
        accesslinkstr = buscaccesslink[0].text
        # Busca o nó XML que armazena pass_inm
        buscapass = self.xroot.findall(f"entry[@chave='pass_inm']")
        passstr = buscapass[0].text
        # Busca o nó XML que armazena rx_id
        buscarxid = self.xroot.findall(f"entry[@chave='rx_id']")
        rxidstr = buscarxid[0].text
        # print(f"rxidstr = {rxidstr}")
        profileaccesslink = profilechildnode.find('.//accesslink')
        profileuser = profilechildnode.find('.//username')
        profilepass = profilechildnode.find('.//password')
        profilerxid = profilechildnode.find('.//rxid')

        # Transfere o valor de url_scp_inm para o nó accesslink em profilexmlnode
        profileaccesslink.text = str(accesslinkstr)
        # Transfere o valor de appUser para o nó username em profilexmlnode
        profileuser.text = str(appuser)
        # Transfere o valor de pass_inm para o nó password em profilexmlnode
        profilepass.text = str(passstr)
        # Transfere o valor de rx_id para o nó rxid em profilexmlnode
        profilerxid.text = str(rxidstr)

        propertiesxmlnode = Globvar.getLabPropertiesNode()
        propertiesxmlnode.set('bipmLabName', labuser)
        propertiesxmlnode.set('mainRxID', rxidstr)
        identifier = propertiesxmlnode.find('.//identifier')
        identifier.text = str(labuser)
        identifier.set("desc", labuser)

        clockproperty_1 = propertiesxmlnode.find('.//clockproperties/clockproperty')
        clockproperty_1.set('rxid', rxidstr)

        gnssproperties = propertiesxmlnode.find('./gnssproperties')
        gnssproperties.set('rxid', rxidstr)
        tref_1 = gnssproperties.find('./tref')
        tref_1.text = "UTC({})".format(str(labuser))

        # Salva o profilexmlnode no arquivo clientprofiles.xml
        propertiescandidade = ET.ElementTree(propertiesxmlnode)
        propertiescandidade.write(os.path.join(Globvar.getLabPropertiesDIR(), "labproperties.xml"), encoding="utf-8",
                               xml_declaration=True)

        # Salva o profilexmlnode no arquivo clientprofiles.xml
        profilecandidade = ET.ElementTree(clientprofilesxmlnode)
        profilecandidade.write(os.path.join(Globvar.getAppConfigDIR(), "clientprofiles.xml"), encoding="utf-8",
                               xml_declaration=True)

    def changedForm(self):
        self.changedformtoken = True
        tokensave = False
        valorxml = ""
        chavexml = ""
        senderOrig = self.sender()
        sendername = senderOrig.__class__.__name__
        # print(sendername)
        if sendername == "QComboBox":
            index = senderOrig.currentIndex()
            datamodel = senderOrig.property('datamodel')
            chavexml = senderOrig.property('chave')
            if chavexml == "tx_modo":
                valorxml = datamodel[index]
                Globvar.setAppMode(valorxml)
            if chavexml == "epoch_id":
                selected_text = senderOrig.itemText(index)
                epoch_index = datamodel[f'{selected_text}']  # Index of STTIME list
                valorxml = selected_text  # Text in the QComBoBox
                self.setEpochIndex(self.getIntValueFromString(epoch_index))
        elif sendername == "QLineEdit":
            valor = senderOrig.text()
            chavexml = senderOrig.property('chave')
            if chavexml in ["appPassword", "pass_inm"]:
                cmdpath = os.path.join(".","exefiles")
                cmdexe = os.path.join(cmdpath,"passcodec.exe")
                cmd = [cmdexe, 'encode', f'{valor}', '6']
                process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                # with process as proc:
                valorxml = str(process.stdout.read(), 'utf-8').replace("Encoded: ", '')
                # valorxml = getEncodedPass(f"{valor}", 6)
            elif chavexml == "process_offset":
                try:
                    self.setProccessOfset(int(valor.strip()))
                    tokensave = True
                except ValueError as ve:
                    self.setFormValuesChecked(False)
                valorxml = valor
            elif chavexml == "gwnr_polarx":
                valorstr = senderOrig.text()
                valorxml = self.getIntValueFromString(valorstr)
                # print(valorxml)
                Globvar.setGwnrFactor(valorxml)
            else:
                valorxml = valor

        elif sendername == "QToolButton":
            valor = senderOrig.text()
            self.getRootPath()
            chavexml = senderOrig.property('chave')
            valorxml = valor
        elif sendername == "QTimeEdit":
            dtt = senderOrig.time().toString(senderOrig.displayFormat())
            daytasktime = datetime.strptime(dtt, '%H:%M:%S').time()
            # print(f"daytasktime = {daytasktime}")
            self.setDailytasktime(daytasktime)
            # currenttime = self.datetimenow.time()
            # newdatetosend = self.datetimenow.date()
            # if currenttime > daytasktime:
            #     newdatetosend += timedelta(days=1)
            #     # print(f"newdatetosend = {newdatetosend}")
            # newdatetimetosend = datetime.combine(newdatetosend, daytasktime)
            taskstate = 0  # definido em self.dailytaskstatedict
            # self.setDailyDatetimeToSend(newdatetimetosend, taskstate)
            self.dictQLD[3] = [daytasktime, ""]
            self.atualizaLCDNumber()
            chavexml = senderOrig.property('chave')
            valorxml = dtt
        elif sendername == "QDateTimeEdit":
            gwnredit = senderOrig.date().toString('yyyy-MM-dd')
            Globvar.setGwnrDate(gwnredit)
            chavexml = senderOrig.property('chave')
            valorxml = gwnredit
        elif sendername == "QCheckBox":
            valor = senderOrig.isChecked()
            chavexml = senderOrig.property('chave')
            if chavexml == 'zip_rinex':
                Globvar.setRinexZipped(valor)
            valorxml = valor

        # print(f"sendername = {sendername}")
        # print(f"chavexml = {chavexml} | valorxml = {valorxml} | tokensave = {tokensave}")

        self.saveXMLNode(chavexml, valorxml, tokensave)

        self.setBtnState(self.btnativa, 'disabled', '')
        self.setBtnState(self.btnconfig, 'disabled', '')
        self.setBtnState(self.btnsalva, 'ready', 'Salvar')

        message = "As propriedades foram alteradas!"
        self.setAppStatus(message)
        self.atualizaStatusBar(self.getAppStatus(), "rgb(64, 128, 128)", "normal")

    def checkThreadDailyTimerTasks(self, tc, current_mjd, result_queue):
        # print(f"current_mjd = {current_mjd}")
        gwnr_factor = Globvar.getGwnrFactor()
        gwnr_mjd = current_mjd - gwnr_factor
        successRINCGG = []
        successCLOCKD = []
        successRESULTUPLOAD = []
        successRESULTLIST = []

        if gwnr_factor > 1:
            contextdictprop = self.generateGwnrDictPropAndLogPath(current_mjd)
        else:
            contextdictprop = self.generateOffsetDictPropAndLogPath(current_mjd)

        # print(f"contextdictprop = {contextdictprop}")
        logpath = self.getContextLogPath()
        mensagem = f"Iniciando a tentativa {tc} de conversão SBF => RINEX para o MJD = {gwnr_mjd}"
        print(mensagem)
        self.setLogInfo(mensagem)

        try:
            successSBRIN = Conv.generateRINEXFromSBF(logpath, current_mjd, gwnr_factor)
            continua = self.updatelogFromResp(successSBRIN)
            # print(f"continua successSBRIN = {continua}")
            # time.sleep(1)
            if continua:
                mensagem = f"A conversão SBF => RINEX para o MJD = {gwnr_mjd} foi realizada"
                time.sleep(1)
            # print(f"successSBRIN = {successSBRIN}")
            # print(f"continua = {continua}")
        except ValueError as ve:
            continua = False
            mensagem = f"Erro em generateRINEXFromSBF no horário {self.horarioatual.isoformat(timespec='seconds')}!"
            self.setAppStatus(mensagem)
            self.atualizaStatusBar(self.getAppStatus(), "red", "bold")

        successRESULTLIST.append([continua, mensagem])

        if continua:
            try:
                cggtts_process_dir = os.path.join(self.approccesspath, self.getRinToCGGproccessDIR())

                if not os.path.exists(cggtts_process_dir):
                    os.makedirs(cggtts_process_dir)
                    self.setLogInfo(
                        f"O caminho para processamento dos arquivos CGGTTS foi criado em [ {cggtts_process_dir} ]")
                print("**************************** Iniciando a conversão RINEX => CGGTTS")
                successRINCGG = Conv.generateCGGTTSFromRINEX(logpath, cggtts_process_dir, current_mjd, True)
                # print(f"continua successRINCGG = {continua}")
                time.sleep(1)
                continua = self.updatelogFromResp(successRINCGG)

            except ValueError as ve:
                continua = False
                self.setAppStatus(
                    f"Erro em generateCGGTTSFromRINEX no horário {self.horarioatual.isoformat(timespec='seconds')}!")
                self.atualizaStatusBar(self.getAppStatus(), "red", "bold")

            successRESULTLIST.append(successRINCGG)

        if continua:

            try:
                successCLOCKD = Conv.generateDailyClockData(
                    {"lab_id": self.getLabID(), "lab_code": self.getLabCode(), "clock_code": self.getClockCode()},
                    current_mjd)

                # Gera o arquivo de clock mensal
                currentdatetime = getDateTimeFromMJD(current_mjd)
                mjdlistforCircT = getCirctMJDList(currentdatetime.date())
                lastmjd = mjdlistforCircT[-1]
                # print(f"lastmjd = {lastmjd}\nfunmjd = {funmjd}")

                if current_mjd > lastmjd:
                    Globvar.setMonthClockFileToken(True)
                    # mjdlistforCircT[0:-1] para remover o último MJD
                    # mjdlistforCircT[1:] para remover o primeiro MJD
                    mjdlisttofile = mjdlistforCircT[1:]
                    print("Iniciando a geração do arquivo de clock mensal")
                    Conv.generateMonthyClockData(contextdictprop, mjdlisttofile)
                else:
                    Globvar.setMonthClockFileToken(False)

                # Define continua em função de successSBRIN, pois a geração do clock não é mandatória
                continua = self.updatelogFromResp(successRESULTLIST)

            except ValueError as ve:
                continua = False
                self.setAppStatus(
                    f"Erro em generateDailyClockData no horário {self.horarioatual.isoformat(timespec='seconds')}!")
                self.atualizaStatusBar(self.getAppStatus(), "red", "bold")

            successRESULTLIST.append(successCLOCKD)

        if continua:

            try:
                successRESULTUPLOAD = TF.uploadfiles(contextdictprop, "FULL")
            except ValueError as ve:
                message = f"Erro em uploadfiles no horário {self.horarioatual.isoformat(timespec='seconds')}!"
                successRESULTUPLOAD.append([False, message])
                self.setAppStatus(message)
                self.atualizaStatusBar(self.getAppStatus(), "red", "bold")

            successRESULTLIST.append(successRESULTUPLOAD)

        result_queue.put(successRESULTLIST)

    def checkDailyTimerTasks(self, tc, current_mjd):
        # print(f"current_mjd = {current_mjd}")
        gwnr_factor = Globvar.getGwnrFactor()
        gwnr_mjd = current_mjd - gwnr_factor
        successRINCGG = []
        successCLOCKD = []
        successRESULTUPLOAD = []
        successRESULTLIST = []

        if gwnr_factor > 1:
            contextdictprop = self.generateGwnrDictPropAndLogPath(current_mjd)
        else:
            contextdictprop = self.generateOffsetDictPropAndLogPath(current_mjd)

        # print(f"contextdictprop = {contextdictprop}")
        logpath = self.getContextLogPath()
        mensagem = f"Iniciando a tentativa {tc} de conversão SBF => RINEX para o MJD = {gwnr_mjd}"
        print(mensagem)
        self.setLogInfo(mensagem)

        try:
            successSBRIN = Conv.generateRINEXFromSBF(logpath, current_mjd, gwnr_factor)
            continua = self.updatelogFromResp(successSBRIN)
            # print(f"continua successSBRIN = {continua}")
            # time.sleep(1)
            if continua:
                mensagem = f"A conversão SBF => RINEX para o MJD = {gwnr_mjd} foi realizada"
                time.sleep(1)
            # print(f"successSBRIN = {successSBRIN}")
            # print(f"continua = {continua}")
        except ValueError as ve:
            continua = False
            mensagem = f"Erro em generateRINEXFromSBF no horário {self.horarioatual.isoformat(timespec='seconds')}!"
            self.setAppStatus(mensagem)
            self.atualizaStatusBar(self.getAppStatus(), "red", "bold")

        successRESULTLIST.append([continua, mensagem])

        if continua:
            try:
                cggtts_process_dir = os.path.join(self.approccesspath, self.getRinToCGGproccessDIR())

                if not os.path.exists(cggtts_process_dir):
                    os.makedirs(cggtts_process_dir)
                    self.setLogInfo(
                        f"O caminho para processamento dos arquivos CGGTTS foi criado em [ {cggtts_process_dir} ]")
                print("**************************** Iniciando a conversão RINEX => CGGTTS")
                successRINCGG = Conv.generateCGGTTSFromRINEX(logpath, cggtts_process_dir, current_mjd, True)
                # print(f"continua successRINCGG = {continua}")
                time.sleep(1)
                continua = self.updatelogFromResp(successRINCGG)

            except ValueError as ve:
                continua = False
                self.setAppStatus(
                    f"Erro em generateCGGTTSFromRINEX no horário {self.horarioatual.isoformat(timespec='seconds')}!")
                self.atualizaStatusBar(self.getAppStatus(), "red", "bold")

            successRESULTLIST.append(successRINCGG)

        if continua:

            try:
                successCLOCKD = Conv.generateDailyClockData(
                    {"lab_id": self.getLabID(), "lab_code": self.getLabCode(), "clock_code": self.getClockCode()},
                    current_mjd)

                # Gera o arquivo de clock mensal
                currentdatetime = getDateTimeFromMJD(current_mjd)
                mjdlistforCircT = getCirctMJDList(currentdatetime.date())
                lastmjd = mjdlistforCircT[-1]
                # print(f"lastmjd = {lastmjd}\nfunmjd = {funmjd}")

                if current_mjd > lastmjd:
                    Globvar.setMonthClockFileToken(True)
                    # mjdlistforCircT[0:-1] para remover o último MJD
                    # mjdlistforCircT[1:] para remover o primeiro MJD
                    mjdlisttofile = mjdlistforCircT[1:]
                    print("Iniciando a geração do arquivo de clock mensal")
                    Conv.generateMonthyClockData(contextdictprop, mjdlisttofile)
                else:
                    Globvar.setMonthClockFileToken(False)

                # Define continua em função de successSBRIN, pois a geração do clock não é mandatória
                continua = self.updatelogFromResp(successRESULTLIST)

            except ValueError as ve:
                continua = False
                self.setAppStatus(
                    f"Erro em generateDailyClockData no horário {self.horarioatual.isoformat(timespec='seconds')}!")
                self.atualizaStatusBar(self.getAppStatus(), "red", "bold")

            successRESULTLIST.append(successCLOCKD)

        if continua:

            try:
                successRESULTUPLOAD = TF.uploadfiles(contextdictprop, "FULL")
            except ValueError as ve:
                message = f"Erro em uploadfiles no horário {self.horarioatual.isoformat(timespec='seconds')}!"
                successRESULTUPLOAD.append([False, message])
                self.setAppStatus(message)
                self.atualizaStatusBar(self.getAppStatus(), "red", "bold")

            successRESULTLIST.append(successRESULTUPLOAD)

        return successRESULTLIST

    # def checkProccessOfsetTaskSequence(self, funmjd):
    #     successRESULT = self.checkDailyTimerTasks(1, funmjd)
    #     return successRESULT

    def checkIntraDayTasks(self):
        successRESULT = []
        timefortask = self.horarioatual.isoformat(timespec='seconds')
        # Remove o horário da tarefa inicial realizada (ou não)
        scheduling = self.getScheduling()
        # for task in scheduling:
        #     print(f"checkIntraDayTasks = {task.dtts} | {task.tipo}")
        scheduling.popleft()
        # Define o caminho de log dos arquivos
        task_log_path = self.getLogPath()
        curr_mjd = self.getCurrentMJD()

        gwnfactor = Globvar.getGwnrFactor()
        gwnr_mjd = curr_mjd - gwnfactor

        self.generateGwnrDictPropAndLogPath(curr_mjd)

        intermessage = f"Início de execução da tarefa intermediária agendada para [ {timefortask} ] com MJD [ {gwnr_mjd} ] -> [ {curr_mjd} ]"
        print(getFramedMessage(intermessage))

        if task_log_path is not None:
            if os.path.exists(task_log_path):
                try:
                    # successSBRIN = Conv.generateRINEXFromSBF(task_log_path, file_mjd)
                    # continua = self.updatelogFromResp(successSBRIN)
                    # print(f"continua successSBRIN tarefa intermediária = {continua} \n{successSBRIN}")
                    [successRESULT, cggttsfilename] = Conv.generateCGGTTSFromSBF(task_log_path, curr_mjd, gwnfactor, timefortask)

                    continua = self.updatelogFromResp(successRESULT)
                    # print(f"continua successSBRIN tarefa intermediária = {continua} \n{successRESULT}")
                    if continua:
                        Globvar.setContextMessage([successRESULT, 'white', 'normal'])
                        # Checks the EPOCH STTIME in the cggttsfilename file
                        if not Globvar.isEpochAdjusted() and successRESULT[0]:
                            # epochlag is the time the software to process data after the estimated CGGTTS epoch
                            secdelta = Conv.getSttimeFromCggtts(cggttsfilename, 60, self.getIntersend(), self.getEpochIndex())
                            Globvar.setEpochAdjust(secdelta)
                            self.generateSchedule(False, False, 0,False)
                            # Globvar.setEpochAdjusted(True)
                except ValueError as ex:
                    message = f"O caminho {task_log_path} não foi encontrado no horário!"
                    self.atualizaStatusBar(message, "red", "bold")
                    Globvar.setContextMessage([message, 'orange', 'normal'])

                uploadparam = False
                uploadlistparam = self.updatelogFromResp(successRESULT)

                if type(uploadlistparam).__name__ == "list":
                    uploadparam = uploadlistparam[0]
                elif type(uploadlistparam).__name__ == "bool":
                    uploadparam = uploadlistparam

                uploadtoken = False

                if uploadparam:
                    try:
                        # print(f"self.getGwnrDictProp() = {self.getGwnrDictProp()}")
                        resulINFOLOCAL = TF.uploadfiles(self.getGwnrDictProp(), self.getCurrentTaskClass())
                        uploadtoken = self.updatelogFromResp(resulINFOLOCAL)
                    except OSError as e:
                        successRESULT.append([False, "Erro ao tentar fazer o upload do GGGTTS!"])
                    if uploadtoken:
                        successRESULT.append([True, "O upload do arquivo GGGTTS foi realizado com SUCESSO!"])
                    else:
                        successRESULT.append([False, "O upload do arquivo GGGTTS NÃO foi realizado!"])
                else:
                    return successRESULT
        else:
            self.setDailyTaskState(3)
            message = f"O caminho {task_log_path} não foi encontrado!"
            print(f"ERRO: {message}")
            self.setLogWarning(message)
            self.atualizaStatusBar(message, "red", "bold")
            successRESULT.append([False, message])

        return successRESULT

    def setStartingAppState(self, sa):
        self.startedApp = sa

    def getStartingAppState(self):
        return self.startedApp

    def startApp(self):
        sebtnstate = self.btnativa.text() == "Ativar"
        se = self.activateComm()
        if se and sebtnstate:
            self.setStartingAppState(se)
            self.generateSchedule(True, False, 0,True)
            self.atualizaQLCDStyle()
            self.setBtnState(self.btnativa, 'active', 'Ativado')
            self.setBtnState(self.btnconfig, 'disabled', '')
            self.setBtnState(self.btnsalva, 'ready', 'Parar')
            dictup = self.updateTimeProperties()
            self.creatLogFile(dictup['mjd'])
            message = "x" #O programa foi iniciado com OFFSET = {}!".format(self.getProccessOfset())
            self.setAppStatus(message)
            self.setLogInfo(message)


    def stopApp(self, se):
        # print(f"se = {se}")
        self.setStartingAppState(False)
        self.active = False
        self.doLayoutMinimization()
        if se:
            self.setProccessOfset(0)
            self.saveXMLNode("process_offset", 0, True)
            self.dictQLD[2] = ["PO:{:02d}".format(1), None]
        self.atualizaLCDNumber()
        self.atualizaQLCDStyle()
        message = f"O programa foi parado | O OFFSET atual é {self.getProccessOfset()}!" \
                  f"Clique em [ Ativar ] para retornar a operação!"
        self.setAppStatus(message)
        self.setLogInfo(message)
        self.atualizaStatusBar(message, 'rgb(228,128,0)', 'normal')

    def activateComm(self):
        se = self.updateAppLogDirFromXML(True)

        # Inicia a verificação da existência dos subprogamas usados pela App
        sbf2rinprog = Globvar.getSbf2RinProgParam()
        sbf2cggttsprog = Globvar.getSbf2CggttsProgParam()
        rin2cggexeprog = Globvar.getRin2CggexePathParam()
        progparam1 = str(sbf2rinprog[1])
        directory1 = os.path.abspath(os.path.join(Globvar.getSubProgDIR(), progparam1))
        progparam2 = str(sbf2cggttsprog[1])
        directory2 = os.path.abspath(os.path.join(Globvar.getSubProgDIR(), progparam2))
        progparam3 = str(rin2cggexeprog[1])
        directory3 = os.path.abspath(os.path.join('rinextocggbin', progparam3))

        tokensubprog1 = True
        tokensubprog2 = True
        tokensubprog3 = True
        existe = True
        mensagemdialog = ""

        if not os.path.exists(directory1):
            mensagemdialog = 'O subprograma {} não foi encontrado no caminho!\n{}\n'.format(progparam1, directory1)
            tokensubprog1 = False
        if not os.path.exists(directory2):
            mensagemdialog = mensagemdialog + f'\nO subprograma {progparam2} não foi encontrado no caminho!' \
                                              f'\n{directory2}\n'
            tokensubprog2 = False
        if not os.path.exists(directory3):
            mensagemdialog = mensagemdialog + f'\nO subprograma {progparam3} não foi encontrado no caminho!\n' \
                                              f'{directory3}\n'
            tokensubprog3 = False

        # Exibe CheckPathDialog caso algum dos subprogramas não sejam encontrados
        if not (tokensubprog1 and tokensubprog2 and tokensubprog3):
            errormessage = f"\nO programa Time{Globvar.getAppMode()} não poderá ser ativado com essa restrição!"
            prefdiag = CheckPathDialog(mensagem=mensagemdialog + errormessage)
            prefdiag.exec()
            existe = False
            # Clica o botão "Configurações"/"Voltar" programaticamente
            self.btnconfig.click()
            self.atualizaStatusBar(mensagemdialog, 'rgb(255,0,0)', 'normal')
        # Ativa a App apenas em caso de existência dos arquivos necessários
        cond = se and existe

        if cond:
            self.doLayoutMinimization()
            self.setActiveState(True)
            self.setTokenSended(self.getCurrentMJD(), False)
            self.active = True
        return cond

    def generateSchedule(self, serializa, expande, plusdays, selog):
        epochAdjust = 60
        self.setDailyTaskScheduled(False)
        token_for_partial_scheduled = False
        tokendailytask_scheduled = False
        # Verifica se o ajuste para sincronismo com o STTIME foi realizado
        if not Globvar.isEpochAdjusted():
            epochAdjust = Globvar.getEpochAdjust()
            # print(f"epochAdjust = {epochAdjust} segundos")
            # Globvar.setDeltaSecAdjusted(True)
        # Zera o display de horário das tarefas intermediárias
        self.dictQLD[2] = ["--:--:--", "gray"]
        self.dictQLD[3] = ["--:--", "gray"]
        # Define o datetime
        agoraUTC = self.datetimenow
        # print(f"agoraUTC = {agoraUTC}")
        timetosend = self.getDailytasktime()

        dtttosend = datetime.combine(agoraUTC.date() + timedelta(days=plusdays), timetosend)

        # Serializa o XML caso o token de configuração não esteja ativado ou quando force está ativado
        if (not self.configtoken or serializa) or self.changedformtoken:
            self.serializeXML(expande)
        # Define o número de tarefas intermediárias (SBF -> CGGTTS)
        num_tasks = int(self.getIntersend()) + 1
        curr_mjd = self.getCurrentMJD()
        # print(f"curr_mjd = {curr_mjd}")
        # Clears the self.rawScheduledTaskClasses deque()
        rawScheduledTC = self.getScheduling()
        rawScheduledTC.clear()

        fullmjd = int(Time(dtttosend).to_value('mjd'))
        taskFull = TaskClass(dtts=dtttosend, tipo=self.dictTaskClasses[1], tmjd=fullmjd, taskmode="OP")

        # Define the time for each intermediate task
        if num_tasks > 0:
            ''' O loop distribuirá os horários das tarefas no mesmo MJD'''
            for x in range(1, num_tasks, 1):
                mjdfrac = curr_mjd + np.divide(x, num_tasks)
                candidateTime = getDateTimeFromMJD(mjdfrac) + timedelta(seconds=int(epochAdjust))
                # print(f"candidateTime = {candidateTime} | {candidateTime.date() <= dtttosend.date()}")
                ########################################################################################################
                ############ Beware: The order of the code lines matters in the following  #############################
                ########################################################################################################
                if candidateTime > agoraUTC: # Checks if the candidateTime is planned to be after the current time
                    # print(f"{candidateTime} | {agoraUTC}")
                    if candidateTime.date() <= dtttosend.date(): # Checks to schedule before the dtttosend date
                        taskpart = TaskClass(dtts=candidateTime, tipo=self.dictTaskClasses[0], tmjd=mjdfrac, taskmode='OP')
                        # FULL task inserted if dtttosend after the current time
                        condition_one = dtttosend > agoraUTC
                        # condition_two = dtttosend < candidateTime # FULL task inserted if last PARTIAL has dtts before
                        token_for_partial_scheduled = True
                        if condition_one and not tokendailytask_scheduled:
                            # Inserts on left the FULL task
                            rawScheduledTC.append(taskFull)
                            tokendailytask_scheduled = True
                            self.setDailyDatetimeToSend(dtttosend, 1)
                        else:
                            rawScheduledTC.append(taskpart)

            # Define o tamanho final da fila de tarefas
            # num_inter_tasks = rawScheduledTC.__len__() # Número de tarefas intermediárias
            # rawScheduledTC.reverse()
            if token_for_partial_scheduled:
                self.setDailyDatetimeToSend(dtttosend, 0)

            # for tc in rawScheduledTC:
            #     print(tc.getTipo(), tc.dtts)
            
            # print(f"num_inter_tasks = {num_inter_tasks} | dtttosend = {dtttosend}")
        curr_po = self.getProccessOfset()

        if curr_po > 0:
            self.scheduleProcessOfsetTask(curr_po, curr_mjd, Globvar.getGwnrFactor())
            Globvar.setProcessOffsetMode(True)

        self.setScheduling(rawScheduledTC)

        if selog:
            self.creatLogFile(curr_mjd)

        ###################### Programa o reagendamento de tarefas no horário 00:00 ####################
        # schedule.every().day.at("21:10").do(self.reScheduleDailyTasks, mjd=curr_mjd, dttime=timetosend)
        ################################################################################################

    def creatLogFile(self, mjd):
        logfilename = f"LOG_{mjd}.log"
        applogdirpath = str(os.path.join(self.getAppUserHomePath()))
        cor = "red"
        message = ""
        if os.path.exists(applogdirpath):
            self.logfilepathname = os.path.join(applogdirpath, logfilename)
            if not os.path.exists(self.logfilepathname):
                message = "O arquivo de LOG será criado no caminho: {}".format(self.logfilepathname)
                try:
                    with open(self.logfilepathname, 'w') as file:
                        message = "Arquivo de LOG para o MJD = {} criado no caminho: {}\n"
                        file.write(message.format(mjd, self.logfilepathname))
                    message = "O arquivo de LOG foi criado no caminho: {}".format(self.logfilepathname)
                    cor = "green"
                except ValueError as ve:
                    message = message.format(ve)
            else:
                message = "O arquivo de LOG já existe no caminho: {}".format(self.logfilepathname)
                cor = "rgb(228, 128, 0)"
            # Fecha o log atual
            rootlogger = logging.getLogger()
            handlers = rootlogger.handlers[:]
            for handler in handlers:
                rootlogger.removeHandler(handler)
                handler.close()
            logging.basicConfig(filename=f"{self.logfilepathname}",
                                format="%(levelname)s [ %(asctime)s ] - %(message)s",
                                datefmt='%H:%M:%S',
                                level=logging.INFO)
            # Creating an object
            self.logger = rootlogger
            Globvar.setLogger(self.logger)
        else:
            message = "Não foi possível criar o arquivo de LOG em: {}".format(applogdirpath)
        self.atualizaStatusBar(message, cor, "normal")

    def getLogFile(self):
        return self.logfilepathname

    def setLogInfo(self, info):
        if self.logger is not None:
            self.logger.info(f"{info}")

    def setLogWarning(self, warn):
        if self.logger is not None:
            self.logger.warning(f"{warn}")

    def setLogError(self, erro):
        if self.logger is not None:
            self.logger.error(f"{erro}")

    def setAppStatus(self, st):
        self.status = st

    def getAppStatus(self):
        return self.status

    def doLayoutMinimization(self):
        for count in range(self.formlayout.rowCount()):
            self.formlayout.removeRow(0)
        windowsize = QSize(formlayout_width, 92)
        mainpannelgeo = QRect(QPoint(100, 100), windowsize)
        self.setGeometry(mainpannelgeo)
        self.setFixedSize(windowsize)
        self.formlayout.update()
        self.atualizaStatusBar(self.getAppStatus(), "rgb(64, 128, 128)", "normal")
        self.setLayoutMinimized(True)

    # noinspection PyUnresolvedReferences
    def retornaMenu(self):
        senderObject = self.sender()
        # Mudar ou remover o comando a seguir
        self.setFormValuesChecked(True)
        if senderObject.objectName() == "pushButton_3":
            if senderObject.text() == "Salvar":
                self.setBtnState(self.btnativa, 'ready', '')
                self.setBtnState(self.btnconfig, 'ready', '')
                self.setBtnState(self.btnsalva, 'disabled', '')
                # Verifica se os caminhos definidos pelo form existem.
                # O parâmetro False indica que o arquivo XML não será serializado
                se = self.updateAppLogDirFromXML(False)
                # Em caso positivo salva o formulário para o arquivo XML
                if se:
                    # ******************************************************************************************************
                    self.saveXMLConfigGui()
                    self.saveXMLProfileFile()
                    # ******************************************************************************************************
                    # Gera um novo agendamento e salva, condicionalmente, no XML
                    # self.generateSchedule(True, False, 0,False)  # call self.serializeXML
                    # Minimiza o QFormLayout
                    self.doLayoutMinimization()
            elif senderObject.text() == "Parar":
                self.stopApp(False)
                self.setBtnState(self.btnativa, 'ready', '')
                self.setBtnState(self.btnconfig, 'ready', '')
                self.setBtnState(self.btnsalva, 'disabled', '')
                # Salva no XML o valor de OFFSET no momento do comando de parada
                self.saveXMLNode("process_offset", self.getProccessOfset(), True)
            elif senderObject.text() == "Voltar":
                self.setBtnState(self.btnativa, 'ready', '')
                self.setBtnState(self.btnconfig, 'ready', '')
                self.setBtnState(self.btnsalva, 'disabled', 'Salvar')
                if not self.isLayoutMinimized():
                    self.doLayoutMinimization()

    def getRootPath(self):
        return self.rootpath

    def setRootPath(self, rp):
        self.rootpath = rp

    def setLabName(self, ln):
        self.labname = ln

    def getLabName(self):
        return self.labname

    def setLabID(self, pre):
        self.lab_id = pre

    def getLabID(self):
        return self.lab_id

    def setRxID(self, rid):
        self.rx_id = rid

    def getRxID(self):
        return self.rx_id

    def setProccessOfset(self, po):
        self.processofset = po
        # print(f"setProccessOfset = {po}")

    def getProccessOfset(self):
        return self.processofset

    def atualizaLCDNumber(self):
        timestring = "00:00:00"
        paramlist = ["seconds", "seconds", "minutes"]
        corlist = ["orange", "white", "orange"]
        for chave, valor in self.dictQLD.items():
            index = chave - 1
            lcdNumber = self.getChildrenObjectUI(QLCDNumber, f'lcdNumber_{chave}')
            timestringinput = valor[0]
            coreval = valor[1]

            if coreval is not None and len(coreval) > 2:
                cor = coreval
            else:
                cor = corlist[index]

            if timestringinput is not None:
                if type(timestringinput).__name__ == "str":
                    timestring = timestringinput
                elif type(timestringinput).__name__ == "time":
                    timestring = timestringinput.isoformat(timespec=paramlist[index])
            else:
                timestring = "--:--:--"

            lcdNumber.display(timestring)
            style = self.styleQLCD.format(cor)
            lcdNumber.setStyleSheet(style)
        QtCore.QCoreApplication.processEvents()

    def atualizaStatusBar(self, basemessage, bkcor, fweight):
        try:
            message = f" Status | {basemessage}"
            self.statusbar.showMessage(message)
            stylelocal = "background-color: {cor}; color: black; border: 1px solid rgb(100,156,156); font-weight:{fontweight}"
            style = stylelocal.format(cor=bkcor, fontweight=fweight)
            self.statusbar.setStyleSheet(style)
            QtCore.QCoreApplication.processEvents()
        except ValueError as ve:
            print(f"Não foi possível atualizar a barra de status: {ve}")
        self.btnsalva.setAutoDefault(True)

    def atualizaQLCDStyle(self):
        se = self.getActiveState()
        if not se:
            cor = "white"
        else:
            cor = "orange"

        style_local = self.styleQLCD.format(cor)
        self.lcdNumber_1.setStyleSheet(style_local)
        self.lcdNumber_2.setStyleSheet(style_local)
        self.lcdNumber_3.setStyleSheet(style_local)

    def setRinToCGGproccessDIR(self, rcgdir):
        self.rinToCGGproccessDIR = rcgdir.replace('/', os.sep)

    def getRinToCGGproccessDIR(self):
        return str(self.rinToCGGproccessDIR)

    def evaluateLogPath(self):
        baselinkpath = Globvar.getBaseLinksPath()
        sbflogdir = Globvar.getSBFLogDIR()
        token = False
        if baselinkpath is not None and sbflogdir is not None:
            self.logpath = os.path.join(baselinkpath, sbflogdir)
            token = True
        return [token, self.logpath]

    def evaluateContextLogPath(self):
        self.contextlogpath = os.path.join(Globvar.getBaseLinksPath(), Globvar.getSBFLogDIR())

    def generateGwnrDictPropAndLogPath(self, gwnr_mjd):
        gwnr_datetime = getDateTimeFromMJD(gwnr_mjd)
        gwnr_year = gwnr_datetime.year
        gwnr_month = gwnr_datetime.month
        root_path = "{}".format(self.getRootPath())
        short_year = gwnr_year - 2000
        lab_name = self.getLabName()
        lab_id = self.getLabID()
        rx_id = self.getRxID()
        lab_code = self.getLabCode()
        clock_code = self.getClockCode()
        context_doy = gwnr_datetime.timetuple().tm_yday

        self.gwnr_dict_prop = {"rootpath": "{}".format(root_path),
                               "labname": lab_name,
                               "labprefix": lab_id,
                               "rxid": rx_id,
                               "sbflogdir": Globvar.getSBFLogDIR(),
                               "labcode": lab_code,
                               "clockcode": clock_code,
                               "contextmjd": gwnr_mjd,
                               "previousmjd": gwnr_mjd - 1,
                               "contextdoy": context_doy,
                               "previousdoy": context_doy - 1,
                               "shortyear": short_year,
                               "contextyear": short_year,
                               "contextmonth": gwnr_month,
                               "monthnum": gwnr_month
                               }
        self.evaluateContextLogPath()
        # print(f"context_dict_prop = {self.context_dict_prop}")
        return self.gwnr_dict_prop

    def generateDictPropAndLogPath(self):
        root_path = "{}".format(self.getRootPath())
        context_mjd = Globvar.getCurrentMJD()
        context_datetime = getDateTimeFromMJD(context_mjd)
        context_year = context_datetime.year
        context_doy = context_datetime.timetuple().tm_yday
        short_year = context_year - 2000
        lab_name = Globvar.getLabName()
        lab_id = Globvar.getLabID()
        rx_id = Globvar.getRxID()
        lab_code = Globvar.getLabCode()
        clock_code = Globvar.getClockCode()
        # context_doy = self.getCurrentDOY()

        self.dict_prop = {"rootpath": "{}".format(root_path),
                          "labname": lab_name,
                          "labprefix": lab_id,
                          "rxid": rx_id,
                          "sbflogdir": Globvar.getSBFLogDIR(),
                          "labcode": lab_code,
                          "clockcode": clock_code,
                          "contextmjd": context_mjd,
                          "previousmjd": context_mjd - 1,
                          "contextdoy": context_doy,
                          "previousdoy": context_doy - 1,
                          "shortyear": short_year
                          }
        # self.makeLogPath()

    def generateOffsetDictPropAndLogPath(self, context_mjd):
        context_datetime = getDateTimeFromMJD(context_mjd)
        context_year = context_datetime.year
        context_month = context_datetime.month
        root_path = "{}".format(self.getRootPath())
        short_year = context_year - 2000
        lab_name = self.getLabName()
        lab_id = self.getLabID()
        rx_id = self.getRxID()
        lab_code = self.getLabCode()
        clock_code = self.getClockCode()
        context_doy = context_datetime.timetuple().tm_yday
        self.context_dict_prop = {"rootpath": "{}".format(root_path),
                                  "labname": lab_name,
                                  "labprefix": lab_id,
                                  "rxid": rx_id,
                                  "sbflogdir": Globvar.getSBFLogDIR(),
                                  "labcode": lab_code,
                                  "clockcode": clock_code,
                                  "contextmjd": context_mjd,
                                  "previousmjd": context_mjd - 1,
                                  "contextdoy": context_doy,
                                  "previousdoy": context_doy - 1,
                                  "shortyear": short_year,
                                  "contextyear": context_year,
                                  "contextmonth": context_month,
                                  "monthnum": context_month
                                  }
        self.evaluateContextLogPath()
        # print(f"context_dict_prop = {self.context_dict_prop}")
        return self.context_dict_prop

    def getGwnrDictProp(self):
        return self.gwnr_dict_prop

    def getDictProp(self):
        return self.dict_prop

    def getContexDictProp(self):
        return self.context_dict_prop

    def getLogPath(self):
        return self.logpath

    def getContextLogPath(self):
        return self.contextlogpath

    def setAppUserHomePath(self, uhp):
        self.userhomepath = uhp

    def getAppUserHomePath(self):
        return self.userhomepath

    def setDailyTaskScheduled(self, se):
        self.dailytaskscheduled = se

    def isDailyTaskScheduled(self):
        return self.dailytaskscheduled

    def closeEvent(self, close):
        stopFlag.set()
        self._stop_event.set()
        if close:
            sys.exit(0)

    def setCurrentTaskClass(self, taskclass):
        self.currenttaskclass = taskclass

    def getCurrentTaskClass(self):
        return self.currenttaskclass

    def updateAppLogDirFromXML(self, fromxmlfile):
        # print("updateAppLogDirFromXML")
        se = False
        config_dir_path = None
        # Monta o caminho de log e propriedades de usuário existe
        # config_dir_path = os.path.join(Globvar.getAppProcesspath(), Globvar.getRxID(), 'configuration')
        # print(f"config_dir_path = {config_dir_path}")
        # Globvar.setReceiverDIR(config_dir_path)  #################

        try:
            if fromxmlfile:
                xmlname = "configui.xml"
                # print(f"Globvar.getAppConfigDIR() = {Globvar.getAppConfigDIR()}")
                xtreegui = ET.parse(os.path.join(Globvar.getAppConfigDIR(), xmlname))
                xrootgui = xtreegui.getroot()
            else:
                xrootgui = self.xroot
            try:
                Globvar.setRootPath(getValueFromChave(xrootgui, 'root_disk'))
                Globvar.setLabName(getValueFromChave(xrootgui, 'lab_name'))
                Globvar.setRxID(getValueFromChave(xrootgui, 'rx_id'))
                # print(f'Globvar.getRxID() = {Globvar.getAppProcesspath(), Globvar.getRxID()}')
                config_dir_path = os.path.join(Globvar.getAppProcesspath(), Globvar.getRxID(), 'configuration')
                # print(f"config_dir_path = {config_dir_path}")
                Globvar.setAppConfigDIR(config_dir_path)
                Globvar.setSBFLogDIR(getValueFromChave(xrootgui, 'local_sbf_to_inm'))
                tokenindex = True
            except IndexError as ie:
                tokenindex = False

            if tokenindex:
                Globvar.setBaseLinksPath(os.path.join(Globvar.getRootPath(), Globvar.getLabName(), Globvar.getRxID()))
                logpathlist = self.evaluateLogPath()
                token = logpathlist[0]
                logpath = logpathlist[1]
                if token and logpath is not None:
                    # Verifica se o caminho de log SBF existe
                    se1 = self.verifyIfLogPathExists(logpath, False)
                    # # Monta o caminho de log e propriedades de usuário existe
                    # config_dir_path = os.path.join(Globvar.getAppProcesspath(), self.getRxID(), 'configuration')
                    # Globvar.setReceiverDIR(config_dir_path) #################
                    # Verifica se o caminho de log e propriedades de usuário existe
                    se2 = self.verifyIfConfigPathExists(config_dir_path, True)

                    # Monta o caminho de log e propriedades de usuário existe
                    prop_dir_path = os.path.join(Globvar.getAppProcesspath(), 'properties')
                    Globvar.setReceiverDIR(prop_dir_path) ###################
                    # Verifica se o caminho de log e propriedades de usuário existe
                    se3 = self.verifyIfLogPathExists(prop_dir_path, True)

                    se = se1 and se2 and se3

        except FileNotFoundError as e:
            self.atualizaStatusBar(e, 'red', 'bold')
        return se

    def verifyIfLogPathExists(self, path, token_copyxml):
        # Verifica se o caminho de log SBF existe
        directory = os.path.abspath(path)
        if not os.path.exists(directory):
            existe = False
            premsg1 = 'O caminho [ {} ] não existe!'.format(directory)
            premsg2 = 'Esse caminho deve ser o mesmo utilizado para log no RxTools!'.format(directory)
            msg = QLabel(
                f"{premsg1}\n{premsg2}\n\nDeseja criar o diretório para log SBF no caminho a seguir?\n{directory}")
            prefdiag = CreateDirDialog(self, message=msg)
            msgboxresult = prefdiag.exec()
            # Verifica a resposta do msgboxresult
            if msgboxresult == 1:
                # Carrega o valor do diretório e atualiza interface gráfica
                os.makedirs(os.path.abspath(directory))
                msg = f"O diretório de log SBF [ {directory} ] foi criado!"
                self.atualizaStatusBar(msg,"rgb(128, 128, 128)", "normal")
                existe = True
                if token_copyxml:
                    # Copia os arquivos xml locais para o caminho de log e propriedades de usuário
                    Futil.copyXmlPropertyFiles(os.path.join(".", "configuration"), directory)
            else:
                # Retorna para o menu "Configurações"
                self.atualizaStatusBar('O diretório de log SBF [ {} ] não existe!'.format(directory),
                                       "rgb(255, 0, 0)", "bold")
                self.stopApp(False)
                self.configuraApp()
        else:
            existe = True
        return existe

    def verifyIfConfigPathExists(self, path, token_copyxml):
        # print("verifyIfConfigPathExists: ", path)
        # Verifica se o caminho de log SBF existe
        directory = os.path.abspath(path)
        if not os.path.exists(directory):
            existe = False
            premsg1 = 'O caminho [ {} ] não existe!'.format(directory)
            premsg2 = 'Esse caminho deve ser o mesmo utilizado para log no RxTools!'.format(directory)
            msg = QLabel(
                f"{premsg1}\n{premsg2}\n\nDeseja criar o diretório de configuração no caminho a seguir?\n{directory}")
            prefdiag = CreateDirDialog(self, message=msg)
            msgboxresult = prefdiag.exec()
            # Verifica a resposta do msgboxresult
            if msgboxresult == 1:
                # Carrega o valor do diretório e atualiza interface gráfica
                os.makedirs(os.path.abspath(directory))
                msg = f"O diretório de log SBF [ {directory} ] foi criado!"
                self.atualizaStatusBar(msg, "rgb(128, 128, 128)", "normal")
                existe = True
                # Globvar.setAppConfigDIR(directory)
                if token_copyxml:
                    # Copia os arquivos xml locais para o caminho de log e propriedades de usuário
                    # Futil.copyXmlPropertyFiles(os.path.join(".", "configuration"), directory)
                    self.saveXMLConfigGui()
            else:
                # Retorna para o menu "Configurações"
                self.atualizaStatusBar('O diretório de log SBF [ {} ] não existe!'.format(directory),
                                       "rgb(255, 0, 0)", "bold")
                self.stopApp(False)
                self.configuraApp()
                # self.saveLabPropXML()
        else:
            existe = True
        return existe

    def verifyIfPathExists(self, path):
        # Verifica se o caminho de log SBF existe
        directory = os.path.abspath(path)
        if not os.path.exists(directory):
            existe = False
            premsg1 = 'O caminho [ {} ] não existe!'.format(directory)
            premsg2 = 'Esse caminho deve ser o mesmo utilizado para log no RxTools!'.format(directory)
            msg = QLabel(
                f"{premsg1}\n{premsg2}\n\nDeseja criar o diretório para log SBF no caminho a seguir?\n{directory}")
            prefdiag = CreateDirDialog(self, message=msg, caminho=directory)
            msgboxresult = prefdiag.exec()
            # Verifica a resposta do msgboxresult
            if msgboxresult == 1:
                # Carrega o valor do diretório e atualiza interface gráfica
                os.makedirs(os.path.abspath(directory))
                self.atualizaStatusBar('O diretório de log SBF [ {} ] foi criado!'.format(directory),
                                       "rgb(128, 128, 128)", "normal")
                existe = True
            else:
                self.atualizaStatusBar('O diretório de log SBF [ {} ] não existe!'.format(directory),
                                       "rgb(255, 0, 0)", "bold")
        else:
            existe = True
        return existe

    def isFormValuesChecked(self):
        return self.formvalueschecked

    def setFormValuesChecked(self, se):
        self.formvalueschecked = se

    def setTimeZoneDiff(self, param):
        self.timezonediff = -param

    def getTimeZoneDiff(self):
        return self.timezonediff

    def setEpochIndex(self, ei):
        self.epoch_index = ei

    def getEpochIndex(self):
        return self.epoch_index


styleSheet = '''
QMainWindow {
    background-color: rgb(100,156,156)
}
QMenuBar {
    background-color: #F0F0F0;
    color: #000000;
    border: 1px solid #000;
    font-weight:bold
}
QMenuBar::item {
    background-color: rgb(49,49,49);
    color: rgb(255,255,255)
}
QMenuBar::item::selected {
    background-color: rgb(30,30,30)
}
QGroupBox {
    border: 1.5px solid white;
    border-radius: 0px;
    background-color: rgb(100,156,156);
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px 0 3px
}
QLabel { 
    font-size: 11pt;
    font-weight: bold;
    min-height: 1em
}
QLineEdit { 
    font-size: 11pt;
    font-weight: normal;
    border-radius: 0px;
    background-color: rgb(192,192,192);
    min-height: 1em
}
QTimeEdit { 
    font-size: 11pt;
    background-color: rgb(192,192,192);
    min-height: 1em
}
QDateTimeEdit { 
    font-size: 11pt;
    background-color: rgb(192,192,192);
    min-height: 1em
}
QToolButton { 
    font-size: 11pt;
    font-weight: normal;
    background-color: rgb(192,192,192);
    border-radius: 0px;
    min-height: 1em
}
QLCDNumber {
    background-color: rgb(0,0,0);
    color: rgb(255,255,255)
}
QTabBar {
    border: 0px solid #31363B;
    color: #152464
}
QTabBar::tab:top:selected {
    background-color: #0066cc;
    color: white
}
QComboBox {
    border: 0px solid black;
    background-color: #d0d0d0;
    color: black;
    selection-color: black;
    font-size: 11pt;
    font-weight: bold;
    min-height: 1em
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
}
'''
pusbutton_style = '''
QPushButton {{
    background-color: {bkcor};
    border: 1.5px solid {border_color};
    border-radius: 3px;
    color: {cor};
    font-size: 14pt;
    font-weight: {peso}
}}'''

if __name__ == "__main__":
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_CompressHighFrequencyEvents)
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    app_icon = QtGui.QIcon()
    app_icon.addFile(os.path.join("gui", "icons", "inmetro.ico"), QtCore.QSize(256, 256))
    app.setWindowIcon(app_icon)
    # Busca os estilos disponíveis
    styles = QtWidgets.QStyleFactory.keys()
    app.setStyle(QtWidgets.QStyleFactory.create(styles[0]))
    stopFlag = Event()
    widget = MainWindow(stopFlag)
    rect = QRect(100, 100, formlayout_width, 92)
    widget.setGeometry(rect)
    widget.setFixedSize(formlayout_width, 92)
    widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
    widget.repaint()
    app.setStyleSheet(styleSheet)
    widget.show()
    widget.run()
    # sys.exit([app.exec(), app.quit()].pop())
    sys.exit(app.exec())