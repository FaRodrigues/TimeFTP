# -*- coding: utf-8 -*-
# TimeFTP version 2.5 (2025)
# Autor: Fernando Rodrigues (Inmetro)

import os


class GlobalVars:
    gwnrdate = None
    gwnrfactor = 0
    currentMJD = 0
    po = 1
    sbf2rinprogparam = None
    sbf2cggttsprogparam = None
    rin2cggexeprogparam = None
    epochadjusted = False
    epochadjust = 0
    month_clock_file = False
    labpropertiesnode = None
    gnsspropertiesnode = None
    xmlprofilesnode = None
    lab_id = None
    count_error = 0
    token_error = False
    status_color = {0: "white", 1: "rgb(254, 200, 114)", 2: "orange", 3: "rgb(255, 64, 64)"}
    context_message = ["", "white"]
    app_mode = "None"
    clock_code = 0
    lab_code = 0
    dictTaskClasses = {}
    zip_rinex = False
    baselinkspath = None
    root_path = None
    lab_name = None
    rx_id = None
    cggttslinksdir = None
    clocklinksdir = None
    rinexlinksdir = None
    xmlpropdir = None
    subprodir = None
    sbflogdir = None
    rinexlogdir = None
    cggttslogdir = None
    global_logger = None
    pcggcopied = False
    dictGenCGGTTS = {}
    pom = False  # process offset mode
    prop_dir = None
    app_pro_path = None
    lab_prop_dir = None


    @classmethod
    def setGwnrFactor(cls, gwnr):
        cls.gwnrfactor = gwnr

    @classmethod
    def getGwnrFactor(cls):
        # Para ajuste e sincronismo com o STTIME
        return cls.gwnrfactor

    @classmethod
    def setRootPath(cls, rp):
        cls.root_path = rp

    @classmethod
    def getRootPath(cls):
        return cls.root_path

    @classmethod
    def setLabPropertiesNode(cls, lpn):
        cls.labpropertiesnode = lpn

    @classmethod
    def getLabPropertiesNode(cls):
        return cls.labpropertiesnode

    @classmethod
    def setGnssPropertiesNode(cls, gnsspn):
        cls.gnsspropertiesnode = gnsspn

    @classmethod
    def getGnssPropertiesNode(cls):
        return cls.gnsspropertiesnode

    @classmethod
    def setLabName(cls, ln):
        cls.lab_name = ln

    @classmethod
    def getLabName(cls):
        return cls.lab_name

    @classmethod
    def setLabID(cls, lid):
        cls.lab_id = lid

    @classmethod
    def getLabID(cls):
        return cls.lab_id

    @classmethod
    def setRxID(cls, rid):
        cls.rx_id = rid

    @classmethod
    def getRxID(cls):
        return cls.rx_id

    @classmethod
    def setSubProgDIR(cls, spd):
        cls.subprodir = str(spd).replace("/", os.sep)

    @classmethod
    def getSubProgDIR(cls):
        return cls.subprodir

    @classmethod
    def setAppConfigDIR(cls, xpd):
        cls.xmlpropdir = str(xpd).replace("/", os.sep)

    @classmethod
    def getAppConfigDIR(cls):
        return cls.xmlpropdir

    @classmethod
    def setRinexLinksDIR(cls, rld):
        cls.rinexlinksdir = str(rld).replace("/", os.sep)

    @classmethod
    def getRinexLinksDIR(cls):
        return cls.rinexlinksdir

    @classmethod
    def setCggttsLinksDIR(cls, cgld):
        cls.cggttslinksdir = str(cgld).replace("/", os.sep)

    @classmethod
    def getCggttsLinksDIR(cls):
        return cls.cggttslinksdir

    @classmethod
    def setClockLinksDIR(cls, cld):
        cls.clocklinksdir = str(cld).replace("/", os.sep)

    @classmethod
    def getClockLinksDIR(cls):
        return cls.clocklinksdir

    @classmethod
    def setBaseLinksPath(cls, blp):
        cls.baselinkspath = str(blp).replace("/", os.sep)

    @classmethod
    def getBaseLinksPath(cls):
        return cls.baselinkspath

    @classmethod
    def setRinexZipped(cls, zr):
        cls.zip_rinex = zr

    @classmethod
    def isRinexZipped(cls):
        return cls.zip_rinex

    @classmethod
    def setDictTaskClasses(cls, dtc):
        cls.dictTaskClasses = dtc

    @classmethod
    def getDictTaskClasses(cls):
        return cls.dictTaskClasses

    @classmethod
    def setLabCode(cls, lc):
        cls.lab_code = lc

    @classmethod
    def getLabCode(cls):
        return cls.lab_code

    @classmethod
    def setClockCode(cls, cc):
        cls.clock_code = cc

    @classmethod
    def getClockCode(cls):
        return cls.clock_code

    @classmethod
    def setAppMode(cls, am):
        cls.app_mode = am

    @classmethod
    def getAppMode(cls):
        return cls.app_mode

    @classmethod
    def setContextMessage(cls, message):
        cls.context_message = message

    @classmethod
    def getContextMessage(cls):
        if cls.isTokenError() and len(cls.context_message[1]) > 1:
            # print(f"cls.context_message = {cls.context_message}")
            cls.context_message[1] = cls.status_color[cls.getCountError()]
        return cls.context_message

    @classmethod
    def setTokenError(cls, te):
        cls.token_error = te
        if cls.getCountError() <= 2:
            cls.count_error += 1

    @classmethod
    def isTokenError(cls):
        return cls.token_error

    @classmethod
    def getCountError(cls):
        return cls.count_error

    @classmethod
    def resetCountError(cls):
        cls.count_error = 0

    @classmethod
    def setMonthClockFileToken(cls, mc):
        cls.month_clock_file = mc

    @classmethod
    def isMonthClockFileToken(cls):
        return cls.month_clock_file

    @classmethod
    def setEpochAdjust(cls, sd):
        # Para ajuste e sincronismo com o STTIME
        cls.epochadjust = sd

    @classmethod
    def getEpochAdjust(cls):
        # Para ajuste e sincronismo com o STTIME
        return cls.epochadjust

    @classmethod
    def setEpochAdjusted(cls, dsa):
        # Para ajuste e sincronismo com o STTIME
        cls.epochadjusted = dsa

    @classmethod
    def isEpochAdjusted(cls):
        # Para ajuste e sincronismo com o STTIME
        return cls.epochadjusted

    @classmethod
    def setLogger(cls, logger):
        cls.global_logger = logger

    @classmethod
    def getLogger(cls):
        return cls.global_logger

    @classmethod
    def setGlobalLogError(cls, erro):
        if cls.global_logger is not None:
            cls.global_logger.error(f"{erro}")

    @classmethod
    def setClientProfileNode(cls, xmlprofilesnode):
        cls.xmlprofilesnode = xmlprofilesnode

    @classmethod
    def getClientProfileNode(cls):
        return cls.xmlprofilesnode

    @classmethod
    def setSBFLogDIR(cls, txt):
        cls.sbflogdir = txt.replace("/", os.sep)

    @classmethod
    def getSBFLogDIR(cls):
        return cls.sbflogdir

    @classmethod
    def setCGGTTSLogDIR(cls, txt):
        cls.cggttslogdir = txt.replace("/", os.sep)

    @classmethod
    def setRinexLogDIR(cls, txt):
        cls.rinexlogdir = txt.replace("/", os.sep)

    @classmethod
    def setSbf2RinProgParam(cls, lista):
        cls.sbf2rinprogparam = lista

    @classmethod
    def getSbf2RinProgParam(cls):
        return cls.sbf2rinprogparam

    @classmethod
    def setSbf2CggttsProgParam(cls, lista):
        cls.sbf2cggttsprogparam = lista

    @classmethod
    def getSbf2CggttsProgParam(cls):
        return cls.sbf2cggttsprogparam

    @classmethod
    def setRin2CggexePathParam(cls, lista):
        cls.rin2cggexeprogparam = lista

    @classmethod
    def getRin2CggexePathParam(cls):
        return cls.rin2cggexeprogparam

    @classmethod
    def setParamCGGTTSCopied(cls, resultcopy):
        cls.pcggcopied = resultcopy

    @classmethod
    def isParamCGGTTSCopied(cls):
        return cls.pcggcopied

    @classmethod
    def setDictGenerateCGGTTS(cls, dictgencggtts):
        cls.dictGenCGGTTS = dictgencggtts

    @classmethod
    def getDictGenerateCGGTTS(cls):
        return cls.dictGenCGGTTS

    @classmethod
    def setConstraintFileParams(cls, cfp):
        cls.constraintFileParams = cfp

    @classmethod
    def getConstraintFileParams(cls):
        return cls.constraintFileParams

    @classmethod
    def setCurrentMJD(cls, mjd):
        cls.currentMJD = mjd

    @classmethod
    def getCurrentMJD(cls):
        return cls.currentMJD

    @classmethod
    def setCurrentPO(cls, po):
        cls.po = po

    @classmethod
    def getCurrentPO(cls):
        return cls.po

    @classmethod
    def setGwnrDate(cls, gwnrdate):
        cls.gwnrdate = gwnrdate

    @classmethod
    def getGwnrDate(cls):
        return cls.gwnrdate

    @classmethod
    def setProcessOffsetMode(cls, pom):
        cls.pom = pom

    @classmethod
    def isProcessOffsetMode(cls):
        return cls.pom

    @classmethod
    def setReceiverDIR(cls, prop_dir_path):
        cls.prop_dir = prop_dir_path

    @classmethod
    def getReceiverDIR(cls):
        return cls.prop_dir

    @classmethod
    def getPropertiesDIR(cls):
        return cls.prop_dir

    @classmethod
    def setAppProcesspath(cls, approccesspath):
        cls.app_pro_path = approccesspath

    @classmethod
    def getAppProcesspath(cls):
        return cls.app_pro_path

    @classmethod
    def setLabPropertiesDIR(cls, lab_properties_dir):
        cls.lab_prop_dir = lab_properties_dir

    @classmethod
    def getLabPropertiesDIR(cls):
        return cls.lab_prop_dir