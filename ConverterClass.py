# -*- coding: utf-8 -*-
# TimeFTP version 2.5 (2025)
# Autor: Fernando Rodrigues (Inmetro)

import os
import subprocess
import textwrap
import time
from collections import deque
from datetime import datetime

import numpy as np
import pandas as pd
from astropy.time import Time

import FileUtilitiesClass as Futil
from Global import GlobalVars as Globvar

def getFramedMessage(midmsg):
    linetext = "*" * (len(midmsg) + 4)
    intermessage = f"\n{linetext}\n{midmsg}\n{linetext}\n"
    return intermessage


def getDateTimeFromMJD(mjdparam):
    tmjd = Time(mjdparam, format='mjd')
    stringdate = Time(tmjd.to_value('iso'), out_subfmt='date_hms').iso
    return datetime.fromisoformat(stringdate)


def getConcatFixedPath(basepath, filenames):
    listOfPaths = []
    for filename in filenames:
        listOfPaths.append(os.path.join(basepath, filename))
    return listOfPaths


def generateCGGTTSFromSBF(logpath, context_mjd, gwnr_factor, basetime):
    global cggttslinkspath, context_cggtts_filename, cggttsFullPathfilename, cggttsFullPathOrigfilename, expected_cggtts_file, cggttsGWNRdir, strmsg

    gwnr_mjd = context_mjd - gwnr_factor

    print(f"Iniciando a geração do arquivo CGGTTS à partir do SBF para o MJD: {gwnr_mjd} => {context_mjd}")
    resultLIST = []
    xmllabpropnode = Globvar.getLabPropertiesNode()
    tokensegue = True
    gnsspropnode = None

    try:
        gnsspropnode = xmllabpropnode.find(f".//gnssproperties[@rxid='{Globvar.getRxID()}']")
    except ValueError as ex:
        tokensegue = False
        print(f"ERRO: {ex}")

    if tokensegue:
        dequetorun = deque([])
        targetDATETIME = getDateTimeFromMJD(context_mjd)
        YEAR = targetDATETIME.year
        context_doy = targetDATETIME.timetuple().tm_yday
        context_shortyear = YEAR - 2000
        dateoffile = targetDATETIME.date()
        subprogdir = Globvar.getSubProgDIR()

        rx_id = Globvar.getRxID()
        lab_id = Globvar.getLabID()

        if gwnr_factor > 1:
            # context_mjd = funmjd + Globvar.getGwnrFactor()
            # Atenção: O valor de getCurrentPO não considera o valor corrente daí ser necessário subtrair 1
            gwnr_datetime = getDateTimeFromMJD(gwnr_mjd)
            gwnr_shortyear = gwnr_datetime.year - 2000
            gwnr_doy = gwnr_datetime.timetuple().tm_yday
            tokengwnr = True
            # Define o caminho absoluto para o diretório Links CGGTTS
            cggttsGWNRdir = str(os.path.join(Globvar.getBaseLinksPath(), 'GNSS', 'Output',
                                             "{:02d}{:03d}".format(context_shortyear, context_doy)))
            # Se o caminho ainda existe, cria o diretório
            if not os.path.exists(cggttsGWNRdir):
                print("Criando o diretório cggttsGWNRdir em {}".format(cggttsGWNRdir))
                os.makedirs(cggttsGWNRdir)

            # print(f"cggttsGWNRdir = {cggttsGWNRdir}")
        else:
            tokengwnr = False
            gwnr_shortyear = context_shortyear
            gwnr_doy = context_doy

        if not os.path.exists(subprogdir):
            message = f'O caminho {subprogdir} não foi encontrado'
            Globvar.setContextMessage([message, 'red', 'normal'])
            return [[False, message], None]

        [tokenshell, sbf2cggexefilepath_param] = Globvar.getSbf2CggttsProgParam()
        sbf2cggexefilepath = os.path.join(subprogdir, sbf2cggexefilepath_param)

        sbfinputdir = os.path.join(logpath, "{:02d}{:03d}".format(gwnr_shortyear, gwnr_doy))
        # print(f"sbfinputdir = {sbfinputdir}")

        sbfnamefile = "{}{}{:03d}0.{:02d}_".format(lab_id, rx_id, gwnr_doy, gwnr_shortyear)
        sbfinputfile = os.path.join(sbfinputdir, sbfnamefile)
        # Verify if sbfinputfile exists in the path
        existesbf = os.path.exists(sbfinputfile)
        # Verify if sbf2cggtts subprogram exists in the path
        existesubprog = os.path.exists(sbf2cggexefilepath)
        cggttsinputdir = sbfinputdir

        if existesbf and existesubprog :

            dictcgginter = {}
            cggttsGwnrToContextdict = {}
            cggttsContextToLinksdict = {}

            try:
                # Define o caminho absoluto para o diretório Links CGGTTS
                cggttslinkspath = str(os.path.join(Globvar.getBaseLinksPath(), Globvar.getCggttsLinksDIR()))
                # Se o caminho ainda existe, cria o diretório
                if not os.path.exists(cggttslinkspath):
                    os.makedirs(cggttslinkspath)

                dictGenCGG = Globvar.getDictGenerateCGGTTS()

                for key, value in dictGenCGG.items():
                    # print(key, value)
                    if value:
                        cggttsfilename = "{}Z{}{}{:.3f}".format(key, lab_id, rx_id, np.divide(gwnr_mjd, 1000))
                        cggttsFullPathOrigfilename = os.path.join(sbfinputdir, cggttsfilename)

                        cggttsFullPathLinksfilename = os.path.join(cggttslinkspath, cggttsfilename)
                        dictcgginter["cggtts_{}".format(key)] = [cggttsFullPathOrigfilename, cggttsFullPathLinksfilename]

                        expected_cggtts_file = os.path.join(cggttsinputdir, cggttsfilename)  # Verify if the generated

                        if tokengwnr:

                            # Define o dict contendo os caminhos da pasta de origem GWNR para o diretório GWNR CORRIGIDO
                            cggttsGwnrToContextdict["CGGTTSGWNR_{}".format(key)] = [
                                expected_cggtts_file,
                                os.path.join(cggttsGWNRdir, cggttsfilename)
                            ]

                            context_cggtts_filename = "{}Z{}{}{:.3f}".format(key, lab_id, rx_id, np.divide(context_mjd, 1000))

                            # Define o dict contendo os caminhos da pasta GWNR CORRIGIDA para o diretório Links
                            cggttsContextToLinksdict["CGGTTSGWNRLINKS_{}".format(key)] = [
                                os.path.join(cggttsGWNRdir, cggttsfilename),
                                os.path.join(cggttslinkspath, context_cggtts_filename)
                            ]

            except ValueError as ve:
                message = f"As definições dos arquivos CGGTTS não foram geradas"
                resultLIST.append([False, message])

            dequetorun.append(sbf2cggexefilepath)

            # Verifica se o caminho sbfinputfile tem espaços vazios
            tokensbfhasspace = any(c.isspace() for c in sbfinputfile)

            if tokensbfhasspace:
                dequetorun.append("-f'{}'".format(sbfinputfile))  # Usa "-f'{}'" para caminhos com espaço
            else:
                dequetorun.append("-f{}".format(sbfinputfile))

            # Itera sobre os nós XML e busca os parâmetros para geração do arquivo CGGTTS
            # **********************************************************************************************************
            # ******************************** Adiciona parâmetros do arquivo CGGTTS ***********************************
            # **********************************************************************************************************

            for x in gnsspropnode.findall(".//*"):

                tagxml = x.tag
                paramtext = gnsspropnode.find(tagxml).text

                # Verifica se paramtext tem espaços vazios
                tokenhasspace = any(c.isspace() for c in paramtext)

                # print(f"tagxml = {tagxml}")

                if len(paramtext) > 0:

                    if tagxml == "comment":
                        valor = "-{tagparam}'{param} in {date} at {time}'".format(tagparam=tagxml, param=paramtext,
                                                                                  date=dateoffile, time=basetime)
                    elif tokenhasspace:
                        valor = "-{tagparam}'{param}'".format(tagparam=tagxml, param=paramtext)
                    else:
                        valor = "-{tagparam}{param}".format(tagparam=tagxml, param=paramtext)

                    dequetorun.append(str(valor))

            # **********************************************************************************************************
            # **********************************************************************************************************
            # **********************************************************************************************************
            # Fim do loop

            arglocal = list(dequetorun)
            # print(f'arglocal = {arglocal}')

            try:
                process = subprocess.Popen(arglocal, cwd=sbfinputdir, shell=tokenshell, stdout=subprocess.PIPE)
                with process as proc:
                    texto = str(proc.stdout.read(), 'utf-8')
                    logmessage = os.linesep.join([s for s in texto.splitlines() if s])
                    process.wait()
                    resultcode = process.returncode
                    # print(f"resultcode = {resultcode}")
                    if resultcode == 0:

                        print(getFramedMessage(logmessage))

                        confere_cggtts = os.path.exists(expected_cggtts_file)

                        if not confere_cggtts:
                            intermessage2 = f"O caminho do arquivo CGGTTS: {expected_cggtts_file} NÃO foi encontrado!"
                            print(getFramedMessage(intermessage2))
                            resultLIST.append([False, intermessage2])
                        else:
                            message = f"Os arquivos CGGTTS foram gerados com SUCESSO a partir dos arquivos SBF no caminho: {sbfinputdir}"
                            resultLIST.append([True, message])
                            intermessage2 = f"O caminho do arquivo CGGTTS é: {expected_cggtts_file}"
                            resultLIST.append([True, intermessage2])
                            print(getFramedMessage(intermessage2))

                        if tokengwnr and confere_cggtts:
                            print(f"cggttsGwnrToContextdict = {cggttsGwnrToContextdict}")
                            # Copia o arquivo CGGTTS original para a pasta de correção GWNR
                            Futil.copyFiles(cggttsGwnrToContextdict, True, False)

                            print(f"cggttsContextToLinksdict = {cggttsContextToLinksdict}")
                            # Copia o arquivo CGGTTS MODIFICADO na ORIGEM para a pasta LINKS
                            from_mjd = gwnr_mjd
                            to_mjd = context_mjd
                            Futil.copy_modified_cggtts_files(cggttsContextToLinksdict, True, from_mjd, to_mjd, False)
                        else:
                            pass
                    else:
                        message = f"Os arquivos CGGTTS não foram gerados a partir dos arquivos SBF no caminho: {sbfinputdir}"
                        resultLIST.append([False, message])
                    process.terminate()
            except ValueError as ve:
                message = f"ERRO: {ve}"
                resultLIST.append([False, message])
        else:
            print("A tarefa intermediária não foi executada!")
            strmsg = ['arquivo', sbfinputfile]
            if not existesubprog:
                strmsg = ['sub programa', sbf2cggexefilepath]
            message = f"O caminho do {strmsg[0]}: {strmsg[1]} NÃO foi encontrado."
            print(getFramedMessage(message))
            resultLIST.append([False, message])
            cggttsFullPathOrigfilename = " "
            # cggttsFullPathfilename = os.path.join(cggttsinputdir, cggttsfilename)
    else:
        message = f"As propriedades do receptor definidas em gnssproperties XML não foram encontradas"
        # print(f"message = {message}")
        resultLIST.append([False, message])

    return [resultLIST, cggttsFullPathOrigfilename]


def getDictFromLists(keys, values):
    return dict(zip(keys, values))


def generateRINEXFromSBF(rootpath, param_mjd, gwnr_factor):
    context_mjd = param_mjd

    if gwnr_factor > 1:
        context_mjd = param_mjd - gwnr_factor

    print(f"****************************************  generateRINEXFromSBF com context_mjd = {context_mjd}")

    resultLIST = []
    RXID = Globvar.getRxID()
    LABID = Globvar.getLabID()
    context_datetime = getDateTimeFromMJD(context_mjd)
    context_year = context_datetime.year
    context_doy = context_datetime.timetuple().tm_yday
    context_shortyear = context_year - 2000

    dequetorun = deque([])

    subprogdir = Globvar.getSubProgDIR()

    if not os.path.exists(subprogdir):
        message = f'O caminho {subprogdir} não foi encontrado'
        Globvar.setContextMessage([message, 'red', 'normal'])
        return [[False, message], None]

    [tokenshell, sbf2rinpath_param] = Globvar.getSbf2RinProgParam()
    sbf2rinpath = os.path.join(subprogdir, sbf2rinpath_param)

    sbfinputdir = os.path.join(f"{rootpath}", "{:02d}{:03d}".format(context_shortyear, context_doy))
    sbfnamefile = "{}{}{:03d}0.{:02d}_".format(LABID, RXID, context_doy, context_shortyear)
    sbfinputfile = os.path.join(sbfinputdir, sbfnamefile)

    rinexinputdir = sbfinputdir

    print(f"****************************************  sbfinputfile = {sbfinputfile}")
    print(f"****************************************  rinexinputdir = {rinexinputdir}")

    param_datetime = getDateTimeFromMJD(param_mjd)
    param_year = param_datetime.year
    param_shortyear = param_year - 2000
    param_doy = param_datetime.timetuple().tm_yday
    tokengwnr = False

    if gwnr_factor > 1:
        tokengwnr = True

    # Define o caminho absoluto para o diretório Links CGGTTS
    rinexolinkspath = str(os.path.join(Globvar.getBaseLinksPath(), Globvar.getRinexLinksDIR()))
    # Se o caminho ainda existe, cria o diretório
    if not os.path.exists(rinexolinkspath):
        os.makedirs(rinexolinkspath)

    # print(f"sbfinputfile = {sbfinputfile}", os.path.isfile(sbfinputfile))

    ######################################################################################################################
    ###################                   Gera os diferentes tipos de arquivo RINEX                     ##################
    ######################################################################################################################

    ConstraintDict = Globvar.getConstraintFileParams()

    if os.path.exists(sbfinputdir) and os.path.isfile(sbfinputfile):
        for chaveConstraint, valorConstraint in ConstraintDict.items():
            print("Iniciando a geração do arquivo RINEX:{}".format(chaveConstraint))
            rinexfilename = "{}{}{:03d}0.{:02d}{}".format(LABID, RXID, context_doy, context_shortyear, chaveConstraint)
            print("Iniciando a geração do arquivo RINEX com chaveConstraint = {} com nome = {}".format(chaveConstraint,
                                                                                                       rinexfilename))
            rinextipo = valorConstraint[0]

            rinexfullfileOrigpath = os.path.join(sbfinputdir, rinexfilename)
            dequetorun.append(sbf2rinpath)
            # Adiciona parâmetros do arquivo CGGTTS
            dequetorun.append("-i{}".format("30"))
            dequetorun.append("-R{}".format("304"))
            dequetorun.append('-f{}'.format(sbfinputfile))
            dequetorun.append("-o{}".format(rinexfullfileOrigpath))
            constelationConstraint = valorConstraint[2]
            if len(constelationConstraint) > 0:
                dequetorun.append("-x{}".format(constelationConstraint))
            dequetorun.append("-n{}".format(rinextipo))
            arglocal = list(dequetorun)

            rinexfullfileDestpath = os.path.join(rinexolinkspath, rinexfilename)
            # Define um dict contendo uma chave identificadora do arquivo RINEX de observação
            dictrinexo = {"rinexo": [rinexfullfileOrigpath, rinexfullfileDestpath]}
            # print(f"arglocal em generateRINEXFromSBF = {arglocal}")
            process = subprocess.Popen(arglocal, cwd=sbfinputdir, shell=tokenshell, stdout=subprocess.PIPE)

            with process as proc:
                texto = str(proc.stdout.read(), 'utf-8')
                logmessage = os.linesep.join([s for s in texto.splitlines() if s])
                process.wait()
                resultcode = process.returncode

                # print(f"resultcode = {resultcode}")

                if resultcode == 0:

                    if tokengwnr:

                        rinexGwnrToContextdict = {}
                        rinexContextToLinksdict = {}

                        # Define o caminho absoluto para o diretório Links CGGTTS
                        rinexPARAMdir = str(os.path.join(Globvar.getBaseLinksPath(), 'GNSS', 'Output',
                                                         "{:02d}{:03d}".format(param_shortyear, param_doy)))

                        param_rinex_filename = "{}{}{:03d}0.{:02d}{}".format(LABID, RXID, param_doy, param_shortyear, rinextipo)

                        print(f"param_rinex_filename = {param_rinex_filename}")

                        rinexGwnrToContextdict["RINEXGWNR_{}".format(rinextipo)] = [
                            os.path.join(rinexinputdir, rinexfilename),
                            os.path.join(rinexPARAMdir,rinexfilename)
                        ]

                        rinexContextToLinksdict["RINEXGWNRLINKS_{}".format(rinextipo)] = [
                            os.path.join(rinexPARAMdir, rinexfilename),
                            os.path.join(rinexolinkspath, param_rinex_filename)
                        ]

                        # Se o caminho ainda existe, cria o diretório
                        if not os.path.exists(rinexPARAMdir):
                            print("Criando o diretório rinexGWNRdir em {}".format(rinexPARAMdir))
                            os.makedirs(rinexPARAMdir)

                        # Copia o arquivo RINEX original para a pasta de correção GWNR
                        Futil.copyFiles(rinexGwnrToContextdict, True, False)
                        # Copia o arquivo RINEX MODIFICADO na ORIGEM para a pasta LINKS
                        # print(f" ===========================================\nrinexContextToLinksdict = {rinexContextToLinksdict}")
                        Futil.copy_modified_rinex_files(rinexContextToLinksdict, True, context_mjd, param_mjd, True)

                    else:

                        if chaveConstraint == "O":
                            Globvar.setRinexZipped(True)
                            Futil.copyFilesToLinks(dictrinexo, True, Globvar.isRinexZipped())

                    print(f"Os arquivos RINEX foram gerados com SUCESSO com resultcode = {resultcode}")
                    # Copia o arquivo RINEX de observação para o caminho Links

                    processtoken = True
                    resultmessage = f"Os arquivos RINEX foram gerados com SUCESSO a partir dos arquivos SBF no caminho: {sbfinputdir}\n{logmessage}"
                else:
                    processtoken = False
                    resultmessage = f"Os arquivos RINEX [ NÃO ] foram gerados no caminho:  {sbfinputdir} -\n{logmessage}"

            resultLIST.append([processtoken, resultmessage])
            # Encerra o processo
            process.terminate()

            time.sleep(1)
    else:
        resultmessage = f"O caminho do arquivo RINEX não foi encontrado em {sbfinputdir}"
        resultLIST.append([False, resultmessage])
    return resultLIST


def getReplacementsDict(mjdatual, funmjd):
    chavelist = []
    valorlist = []
    for mjddiff in range(-1, +2):

        mjdval = mjdatual + mjddiff
        tmj = Time(mjdval, format='mjd')
        stringdate = Time(tmj.to_value('iso'), out_subfmt='date').iso

        data_anterior = getDateTimeFromMJD(funmjd+mjddiff)
        mjd_anterior = int(Time(data_anterior).to_value('mjd'))
        tmjdant = Time(mjd_anterior, format='mjd')
        stringdate_anterior = Time(tmjdant.to_value('iso'), out_subfmt='date').iso

        chavelist.append(stringdate_anterior.replace('-', ' '))
        valorlist.append(stringdate.replace("-", " "))

        if mjddiff == 0:
            anterior_year = data_anterior.year
            anterior_shortyear = anterior_year - 2000
            anterior_doy = data_anterior.timetuple().tm_yday

    return chavelist, valorlist, anterior_shortyear, anterior_doy


def generateCGGTTSFromRINEX(logpath, cggtts_process_path, param_mjd, sobrescreve):
    print(f"\n ======================>  Iniciando a geração de arquivos CGGTTS a partir do arquivo RINEX!\n")
    processtoken = False
    resultLIST = []
    rx_id = Globvar.getRxID()
    lab_id = Globvar.getLabID()

    contextmjd = param_mjd

    gwnr_factor = Globvar.getGwnrFactor()

    if gwnr_factor > 1:
        contextmjd = param_mjd - gwnr_factor

    context_ontem_mjd = contextmjd - 1
    param_ontem_mjd = param_mjd -1

    print('generateCGGTTSFromRINEX:',context_ontem_mjd, param_ontem_mjd)
    # time.sleep(6)

    targetDATETIME = getDateTimeFromMJD(param_ontem_mjd)
    ontemDATETIME = getDateTimeFromMJD(context_ontem_mjd)

    YEAR = targetDATETIME.year
    DOY = targetDATETIME.timetuple().tm_yday
    SHORTYEAR = YEAR - 2000

    ontemYEAR = ontemDATETIME.year
    ontemDOY = ontemDATETIME.timetuple().tm_yday
    ontemSHORTYEAR = ontemYEAR - 2000

    dequetorun = deque([])

    [tokenshell, rin2cggexepath_param] = Globvar.getRin2CggexePathParam()

    rin2cggexepath = os.path.join(os.getcwd(), "rinextocggbin", rin2cggexepath_param)
    dequetorun.append(rin2cggexepath)

    rinexOntempath = os.path.join(logpath, "{:02d}{:03d}".format(ontemSHORTYEAR, ontemDOY))
    rinexpath = os.path.join(logpath, "{:02d}{:03d}".format(SHORTYEAR, DOY))
    cggttspath = rinexpath

    twopathcondition = os.path.exists(rinexOntempath) and os.path.exists(rinexpath)

    # ******************************************************************************************************************
    # ******************************************************************************************************************
    # ******************************************************************************************************************
    paramcggfilename = "paramCGGTTS.dat"

    origemParamCGGTTSfile = os.path.join(".", "templates", paramcggfilename)
    destinoParamCGGTTSfile = os.path.join(cggtts_process_path, paramcggfilename)

    # Verifica se o token isParamCGGTTSCopied já foi setado para True após cópia do arquivo paramCGGTTS.dat
    if not (Globvar.isParamCGGTTSCopied()):
        paramCGGTTSdict = {
            "paramCGGTTS": [origemParamCGGTTSfile, destinoParamCGGTTSfile]
        }
        # Copia o arquivo paramCGGTTS.dat para o diretório temporário
        resultcopy = Futil.copyRinexAndParamFiles(paramCGGTTSdict)

        time.sleep(1)

        if resultcopy:
            message = f"O arquivo {paramcggfilename} foi copiado para o caminho {destinoParamCGGTTSfile}"
            converterLOG = Globvar.getLogger()
            if converterLOG is None:
                print("ERRO")
                return None

            converterLOG.info(message)
            print(message)

        Globvar.setParamCGGTTSCopied(resultcopy)

    # ******************************************************************************************************************
    # ******************************************************************************************************************
    # ******************************************************************************************************************

    if twopathcondition and os.path.exists(destinoParamCGGTTSfile):
        # Cria um dict com os caminhos de origem e destino dos arquivos RINEX
        dictrinex2cggparams = {
            "rinexOBSontemFile": [
                os.path.join(rinexOntempath,
                             "{}{}{:03d}0.{:02d}{}".format(lab_id, rx_id, ontemDOY, ontemSHORTYEAR, "o")),
                os.path.join(cggtts_process_path, "rinex_obs")
            ],
            "rinexOBShojeFile": [
                os.path.join(rinexpath, "{}{}{:03d}0.{:02d}{}".format(lab_id, rx_id, DOY, SHORTYEAR, "o")),
                os.path.join(cggtts_process_path, "rinex_obs_p")
            ]
        }

        ConstraintDict = Globvar.getConstraintFileParams()

        for chaveConstraint, valorConstraint in ConstraintDict.items():
            dictrinex2cggparams[f"rinexNAVontemFile_{chaveConstraint}"] = [
                os.path.join(rinexOntempath,
                             "{}{}{:03d}0.{:02d}{}".format(lab_id, rx_id, ontemDOY, ontemSHORTYEAR, chaveConstraint)),
                os.path.join(cggtts_process_path, f"rinex_nav_{valorConstraint[1]}")
            ]
            dictrinex2cggparams[f"rinexNAVhojeFile_{chaveConstraint}"] = [
                os.path.join(rinexpath, "{}{}{:03d}0.{:02d}{}".format(lab_id, rx_id, DOY, SHORTYEAR, chaveConstraint)),
                os.path.join(cggtts_process_path, f"rinex_nav_p_{valorConstraint[1]}")
            ]

        # Define o caminho absoluto para o diretório Links CGGTTS
        cggttsdailylinksdir = str(os.path.join(Globvar.getBaseLinksPath(), Globvar.getCggttsLinksDIR()))
        # Se o caminho ainda existe, cria o diretório
        if not os.path.exists(cggttsdailylinksdir):
            os.makedirs(cggttsdailylinksdir)

        nofiles = []

        chaves = dictrinex2cggparams.keys()

        for filename in chaves:
            filepath = dictrinex2cggparams[filename][0]
            if not os.path.isfile(filepath):
                nofiles.append(filepath)

        if len(nofiles) == 0:
            message = f"--> Iniciando a cópia dos arquivos RINEX para o caminho {cggtts_process_path}"
            # print(message)
            resultcopy = Futil.copyRinexAndParamFiles(dictrinex2cggparams)
            resultLIST.append([resultcopy, message])
            time.sleep(0.1)
            arglocal = list(dequetorun)
            #
            if len(arglocal) == 1:
                arglocal = arglocal[0]
            # print(f"arglocal em generateCGGTTSFromRINEX = {arglocal}")
            try:
                process = subprocess.Popen(arglocal, cwd=cggtts_process_path, shell=tokenshell, stdout=subprocess.PIPE)
                with process as proc:
                    texto = str(proc.stdout.read(), 'utf-8')
                    logmessage = os.linesep.join([s for s in texto.splitlines() if s])
                    process.wait()
                    resultcode = process.returncode
                    if resultcode == 0:
                        processtoken = True
                        # generatedfiles.append(nameOffile)
                    else:
                        processtoken = False
                    process.terminate()
            except ValueError as ve:
                processtoken = False

            if processtoken:
                message = f"Os arquivos CGGTTS foram gerados com SUCESSO a partir dos arquivos RINEX no caminho: {rinexOntempath} "
                # print(message)
                resultLIST.append([True, message])
                message = f"Realizando a cópia dos arquivos CGGTTS DOY = {ontemDOY} para o caminho {rinexOntempath}"
                resultLIST.append([True, message])

                # Cria um dict com a relação entre os arquivos CGGTTS temporários e os arquivos CGGTTS padrão do BIPM
                dictGenCGGConv = Globvar.getDictGenerateCGGTTS()

                dictFreqRelations = {"G": "CGGTTS_GPS_L3P", "R": "CGGTTS_GLO_L3P", "E": "CGGTTS_GAL_L3E",
                                     "C": "CGGTTS_BDS_L3B"}

                cggttsTempToLogdict = {}
                cggttsLogToLinksdict = {}
                cgggttsFromLogToParamLogDict = {}
                cggttsParamLogToLinksdict = {}

                tokenlinks = True
                tokengwnr = False
                cggttsPARAMdir = None

                if gwnr_factor > 1:
                    # Atenção: O valor de getCurrentPO não considera o valor corrente daí ser necessário subtrair 1
                    param_datetime = getDateTimeFromMJD(param_ontem_mjd)
                    param_shortyear = param_datetime.year - 2000
                    param_doy = param_datetime.timetuple().tm_yday
                    # Define o caminho absoluto para o diretório Links CGGTTS
                    cggttsPARAMdir = str(os.path.join(Globvar.getBaseLinksPath(), 'GNSS', 'Output',
                                                     "{:02d}{:03d}".format(param_shortyear, param_doy)))
                    # Se o caminho ainda existe, cria o diretório
                    if not os.path.exists(cggttsPARAMdir):
                        os.makedirs(cggttsPARAMdir)

                    tokengwnr = True

                    # Desabilita cópia dos arquivos para Links e aguarda a modificação GWNR
                    tokenlinks = False


                for key, value in dictGenCGGConv.items():
                    # print(f"key = {key} | value = {value}")
                    if value:
                        cggttsTempToLogdict["CGGTTS_{}".format(key)] = [
                            os.path.join(cggtts_process_path, dictFreqRelations[key]),
                            os.path.join(rinexOntempath,
                                         "{}Z{}{}{:.3f}".format(key, lab_id, rx_id,
                                                                np.divide(context_ontem_mjd, 1000)))
                        ]

                        cggttsLogToLinksdict["CGGTTSLINKS_{}".format(key)] = [
                            os.path.join(rinexOntempath,
                                         "{}Z{}{}{:.3f}".format(key, lab_id, rx_id,
                                                                np.divide(context_ontem_mjd, 1000))),
                            os.path.join(cggttsdailylinksdir,
                                         "{}Z{}{}{:.3f}".format(key, lab_id, rx_id,
                                                                np.divide(context_ontem_mjd, 1000)))
                        ]

                        #############################################################################
                        #############################################################################
                        ''' Para casos de GPS Week Number Rollover '''
                        #############################################################################
                        #############################################################################

                        if tokengwnr:
                            cgggttsFromLogToParamLogDict["CGGTTSGWNR_{}".format(key)] = [
                                os.path.join(rinexOntempath, "{}Z{}{}{:.3f}".format(key, lab_id, rx_id, np.divide(context_ontem_mjd, 1000))),
                                os.path.join(cggttsPARAMdir,"{}Z{}{}{:.3f}".format(key, lab_id, rx_id, np.divide(context_ontem_mjd, 1000)))
                            ]

                            cggttsParamLogToLinksdict["CGGTTSGWNRLINKS_{}".format(key)] = [
                                os.path.join(cggttsPARAMdir, "{}Z{}{}{:.3f}".format(key, lab_id, rx_id,
                                                                    np.divide(context_ontem_mjd, 1000))),
                                os.path.join(cggttsdailylinksdir,
                                             "{}Z{}{}{:.3f}".format(key, lab_id, rx_id,
                                                                    np.divide(param_ontem_mjd, 1000)))
                            ]

                            #############################################################################
                            #############################################################################
                            ''' Para casos de GPS Week Number Rollover '''
                            #############################################################################
                            #############################################################################

                # Copia o arquivo CGGTTS para o caminho de LOG
                Futil.copyTemporaryCGGTTSFiles(cggttsTempToLogdict, sobrescreve, context_ontem_mjd)

                if tokenlinks and not tokengwnr: # Copy files to links only if not in GWNR mode
                    # Copia o arquivo CGGTTS para o caminho Links
                    Futil.copyFilesToLinks(cggttsLogToLinksdict, sobrescreve, False)

                # print(f"cggttsTempToLogdict = {cggttsTempToLogdict}")
                print(f"cgggttsFromLogToParamLogDict = {cgggttsFromLogToParamLogDict}")
                print(f"****************************  cggttsParamLogToLinksdict = {cggttsParamLogToLinksdict}")

                if tokengwnr:
                    # # Copia o arquivo CGGTTS do repositório temporário para a pasta futura GWNR
                    Futil.copyFiles(cgggttsFromLogToParamLogDict, sobrescreve, False)
                    # time.sleep(1)
                    # Copia os arquivos modificados (na origem) para as pastas Links
                    Futil.copy_modified_cggtts_files(cggttsParamLogToLinksdict, sobrescreve, context_ontem_mjd, param_ontem_mjd, False)

                message = "Os arquivos CGGTTS foram gerados com SUCESSO!"
                # print(message)
        else:
            message = (f"Os arquivos CGGTTS não foram gerados.\n"
                       f"Os arquivos seguintes não foram encontrados para o MJD =  {contextmjd} \n{nofiles}\n")
            resultLIST.append([False, message])
            # print(message)
    else:
        message = f"Os caminhos {rinexOntempath} e {rinexpath} não foram encontrados para o MJD = {contextmjd} "
        resultLIST.append([False, message])

    return resultLIST


def generateDailyClockData(clokprop, contextmjd):
    resultLIST = []
    lab_id = clokprop["lab_id"]
    lab_code = clokprop["lab_code"]
    clock_code = clokprop["clock_code"]
    previous_mjd = contextmjd - 1

    gpsclockfilename = "CD{}__{:.3f}".format(lab_id, np.divide(previous_mjd, 1000))

    clockdirpath = str(os.path.join(Globvar.getBaseLinksPath(), Globvar.getClockLinksDIR()))

    if not os.path.exists(clockdirpath):
        os.makedirs(clockdirpath)
        print("\nO diretório de clock foi criado no caminho: {}\n".format(clockdirpath))

    if os.path.exists(clockdirpath):

        clockfilepath = os.path.join(clockdirpath, gpsclockfilename)

        print("Iniciando geração do arquivo de clock será criado no caminho: {}".format(clockfilepath))

        try:
            with open(clockfilepath, 'w') as file:
                file.write(
                    "{} {} {}       0.0".format(previous_mjd, lab_code, clock_code))
                resmessage = "O arquivo de clock foi criado no caminho: {}".format(clockfilepath)
                resultLIST.extend([True, resmessage])
        except ValueError as ve:
            print("Não foi possível criar o arquivo de clock: {ve}")
    else:
        resmessage = "O caminho do arquivo de clock {} não foi encontrado".format(clockdirpath)
        resultLIST.extend([False, resmessage])

    return resultLIST


def generateMonthyClockData(clokprop, mjdlist):
    resultLIST = []
    lab_id = clokprop["labprefix"]
    lab_code = clokprop["labcode"]
    clock_code = clokprop["clockcode"]
    short_year = clokprop["shortyear"]
    month_num = clokprop["monthnum"]
    # previousmjd = contextmjd - 1

    gpsclockfilename = "CD{}__{}.{:02d}_".format(lab_id, short_year, month_num)

    clockdirpath = str(os.path.join(Globvar.getBaseLinksPath(), Globvar.getClockLinksDIR()))

    if not os.path.exists(clockdirpath):
        os.makedirs(clockdirpath)
        print("\nThe clock file directory was created in the path: {}\n".format(clockdirpath))

    if os.path.exists(clockdirpath):

        clockfilepath = os.path.join(clockdirpath, gpsclockfilename)

        print("Starting clock file generation will be created in the path: {}".format(clockfilepath))

        try:

            with open(clockfilepath, 'w') as file:
                for mjd in mjdlist:
                    file.write("{} {} {}       0.0".format(mjd, lab_code, clock_code))
                    if not (mjd == mjdlist[-1]):
                        file.write("\n")

            print("The clock file was created in the path: {}".format(clockfilepath))

        except ValueError as ve:
            print(f"Could not create clock file: {ve}")
    else:
        resmessage = "The clock file path {cdp} was not found".format(cdp=clockdirpath)
        resultLIST.append([False, resmessage])

    return resultLIST


def getSttimeFromCggtts(filepathname, epochlag, num_tasks, index):
    # epochlag is the time the software to process data after the estimated CGGTTS epoch
    epochadjust = epochlag
    task_interval = 16
    try:
        task_interval = 86400/num_tasks/60
    except ValueError as ve:
        pass
    # Define os nomes para os campos de dados
    datanames = ["SAT", "CL", "MJD", "STTIME", "TRKL", "ELV", "AZTH", "REFSV", "SRSV", "REFSYS", "SRSYS",
                 "DSG", "IOE",
                 "MDTR", "SMDT", "MDIO", "SMDI", "MSIO", "SMSI", "ISG", "FR", "HC", "FRC", "CK"]

    if os.path.exists(filepathname):
        try:
            ''' START READING THE CGGTTS FILE '''
            RAWCGGTTS_data = pd.read_csv(filepathname, sep="\\s+|;|:", header=None, names=datanames,
                                         dtype=object, engine="python", skiprows=19)
            print("Checking EPOCH STTIME in file: {}".format(filepathname))
            DF = RAWCGGTTS_data['STTIME']
            DTIME = list(DF)
            sttimelist = np.array(textwrap.wrap("{}".format(DTIME[index]), 2), dtype=int)
            # Calculates the epoch schedule to process the CGGTTS files based in the CGGTTS STTIME itself
            epochadjust = sttimelist[0] * 3600 + sttimelist[1] * 60 + sttimelist[2] + (task_interval * 60)
            del DF
        except ValueError as ex:
            pass
    return epochadjust