# -*- coding: utf-8 -*-
# TimeFTP version 2.5 (2025)
# Autor: Fernando Rodrigues (Inmetro)

import base64
import os
import time
from collections import deque

import paramiko  # em caso de erro com bcript usar pip install --upgrade bcrypt==4.1.1
from ftplib import FTP
from scp import SCPClient
import numpy as np
from Global import GlobalVars as Globvar
global listOfFilesToTransferToUTC, listOfFilesToTransferToUTCR

def getFramedMessage(midmsg):
    linetext = "*" * (len(midmsg) + 4)
    intermessage = f"\n{linetext}\n{midmsg}\n{linetext}\n"
    return intermessage


def createSSHClient(server, port, user, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(server, port, user, password, timeout=10)
    except BaseException as e:
        # print(f"Erro em createSSHClient: {e}")
        Globvar.setContextMessage([str(e), 'red', 'bold'])
    return client


def getDecodedPass(sina, cluster):
    sina_string = ""
    for x in range(cluster):
        base64_bytes = sina[::-1].encode("utf-8")
        sina_string_bytes = base64.b64decode(base64_bytes)
        sina_string = sina_string_bytes.decode("utf-8")
        sina = sina_string
    return sina_string


def getOrigDir(chave_lower):
    origdir = "None"

    if "cggtts" in chave_lower:
        origdir = str(os.path.join(Globvar.getBaseLinksPath(), Globvar.getCggttsLinksDIR()))
    elif chave_lower == "rinex":
        origdir = str(os.path.join(Globvar.getBaseLinksPath(), Globvar.getRinexLinksDIR()))
    elif chave_lower == "clock":
        origdir = str(os.path.join(Globvar.getBaseLinksPath(), Globvar.getClockLinksDIR()))
    return origdir


def uploadfiles(dictprop, taskclass):

    global listOfFilesToTransferToUTCR, listOfFilesToTransferToUTC

    listOfFilesToTransferToUTCR = {}
    listOfFilesToTransferToUTC = {}

    transferlogger = Globvar.getLogger()
    resultINFO = deque([])

    localcontextdyndir = os.path.join(
        dictprop["rootpath"],
        dictprop["labname"],
        dictprop["rxid"],
        dictprop["sbflogdir"],
        "{:02d}{:03d}".format(dictprop["shortyear"], dictprop["contextdoy"]))

    localpreviousdyndir = os.path.join(
        dictprop["rootpath"],
        dictprop["labname"],
        dictprop["rxid"],
        dictprop["sbflogdir"],
        "{:02d}{:03d}".format(dictprop["shortyear"], dictprop["previousdoy"]))

    dicttaskclasses = Globvar.getDictTaskClasses()

    # globvar.getDictTaskClasses()[0] = "Partial"
    preconditiontotransfer = os.path.exists(localcontextdyndir) and (
            os.path.exists(localpreviousdyndir) or taskclass == dicttaskclasses[0])

    print(f"preconditiontotransfer = {preconditiontotransfer}", localpreviousdyndir, localcontextdyndir)
    # print(f"dictprop = {dictprop['labprefix']}")
    # print(f"taskclass = {taskclass}")
    # ConstraintDict = Globvar.getConstraintFileParams()

    if preconditiontotransfer:

        gpsrinexfilename = "{}{}{:03d}0.{}O".format(dictprop['labprefix'], dictprop["rxid"], dictprop["contextdoy"],
                                                    dictprop["shortyear"])

        gpsdailyclockfilename = "CD{}__{:.3f}".format(dictprop["labprefix"], np.divide(dictprop["previousmjd"], 1000))

        # print(f"Globvar.isRinexZipped() = {Globvar.isRinexZipped()}")
        if Globvar.isRinexZipped():
            gpsrinexfilename = "{}{}".format(gpsrinexfilename, ".zip")

        if taskclass == dicttaskclasses[1]:
            listOfFilesToTransferToUTC = {"rinex": gpsrinexfilename.lower()}
            listOfFilesToTransferToUTCR = {"RINEX": gpsrinexfilename,"CLOCK": gpsdailyclockfilename}

        dictGenCGG = Globvar.getDictGenerateCGGTTS()

        for key, value in dictGenCGG.items():
            # print(taskclass, key, value)
            if value:
                previouscggtsfilename = "{}Z{}{}{:.3f}".format(key, dictprop["labprefix"], dictprop["rxid"],
                                                                 np.divide(dictprop["previousmjd"], 1000))

                dailycggtsfilename = "{}Z{}{}{:.3f}".format(key, dictprop["labprefix"], dictprop["rxid"],
                                                              np.divide(dictprop["contextmjd"], 1000))

                if taskclass == dicttaskclasses[1]:
                    listOfFilesToTransferToUTC["cggtts_{}".format(key)] = previouscggtsfilename.lower()

                    listOfFilesToTransferToUTCR = {"RINEX": gpsrinexfilename, "CGGTTS_{}".format(key): previouscggtsfilename,
                                                   "CLOCK": gpsdailyclockfilename}

                elif taskclass == dicttaskclasses[0]: # Envia apenas o CGGTTS do dia
                    listOfFilesToTransferToUTC["cggtts_{}".format(key)] = dailycggtsfilename
                    listOfFilesToTransferToUTCR["CGGTTS_{}".format(key)] = dailycggtsfilename

            # Se isMonthClockFileToken == True, inclui o arquivo de clock mensal em listOfFilesToTransferToUTCR
            if Globvar.isMonthClockFileToken():
                gpsmonthyclockfilename = "CD{}__{}.{:02d}_".format(dictprop["labprefix"], dictprop["shortyear"],
                                                                   dictprop["contextmonth"])
                listOfFilesToTransferToUTC["CLOCK"] = gpsmonthyclockfilename.lower()

        # serializa o arquivo XML contendo os perfis
        # treeprofiles = et.parse(os.path.join(globvar.getXmlPropertiesDIR(), "clientprofiles.xml"))
        # xmlprofilesroot = treeprofiles.getroot()
        xmlprofilesroot = Globvar.getClientProfileNode()

        print(f"listOfFilesToTransferToUTCR = {listOfFilesToTransferToUTCR}")
        print(f"listOfFilesToTransferToUTC = {listOfFilesToTransferToUTC}")

        # define o nó XML de contexto
        cxnlist = xmlprofilesroot.findall(f".//profile[@labname='{dictprop['labname']}']")

        for cxn in cxnlist:
            labname = cxn.get('labname')
            message = '--> A atualização dos arquivos CGGTTS para o repositório de {} foi iniciada'.format(labname)
            Globvar.setContextMessage(message)
            # print("labname = {}".format(labname))
            contextcommtype = cxn.attrib['commtype']
            contextlink = cxn.find('accesslink').text
            contextuser = cxn.find('username').text
            contextpass = cxn.find('password').text
            contextrxid = Globvar.getRxID()
            # print('usern: {}'.format(cxn.find('username').text))
            # QtCore.QCoreApplication.processEvents()

            failedtrans = []

            if contextcommtype == 'FTP':
                message = f'Iniciando a conexão FTP ao repositório do BIPM'
                # atualizaStatusBar(message, "orange")
                transferlogger.info(f"{message}")
                print(getFramedMessage(message))
                # print("contextlink = {}".format(contextlink))
                try:
                    ftps_client = FTP(contextlink)  # replace with your host name or IP
                    ftps_client.login(user=contextuser, passwd='{}'.format(getDecodedPass(contextpass, 6)))
                    message = str(ftps_client.getwelcome())
                    print(f"{message}")

                    utcmessage = "Preparando a transferência de arquivos UTC!"
                    print(f"\n{utcmessage}")
                    transferlogger.info(f"{utcmessage}")

                    for chaveparam, filename in listOfFilesToTransferToUTC.items():
                        labRootFileDESTpath = f"/data/UTC/{labname}"
                        chave_lower = str(chaveparam).lower()
                        filenamelower = str(filename).lower()

                        # print(f"chaveparam = {chaveparam} | filename =  {filename}")
                        # print("cggtts" in chave_lower)

                        if chaveparam == "CLOCK":
                            relativeFileDESTpath = f"{labRootFileDESTpath}/clocks"
                        elif "cggtts" in chave_lower:
                            relativeFileDESTpath = f"{labRootFileDESTpath}/links/cggtts"
                        elif "rinex" in chave_lower:
                            relativeFileDESTpath = f"{labRootFileDESTpath}/links/rinex"
                        else:
                            relativeFileDESTpath = f"{labRootFileDESTpath}/links/{chaveparam}"
                            filenamelower = str(filename).lower()

                        origdir = getOrigDir(chave_lower)
                        localdynpath = os.path.join(origdir, filename)
                        # print(f"localdynpath = {localdynpath}", os.path.exists(localdynpath))
                        # print(f"relativeFileDESTpath = {relativeFileDESTpath}")
                        ftps_client.cwd(relativeFileDESTpath)  # change into "debian" directory
                        fileDESTpath = f"{relativeFileDESTpath}/{filenamelower}"

                        if os.path.exists(localdynpath):

                            print(f"Iniciando a transferência:\nOrigem: {localdynpath}\nDestino: {fileDESTpath}")

                            if chave_lower in ["cggtts_g", "cggtts_r", "cggtts_e", "cggtts_c", "clock"]:

                                try:
                                    with open(str(localdynpath), 'rb') as file:
                                        resp = ftps_client.storlines('STOR {}'.format(filenamelower), file)
                                        # resp = [226]
                                        time.sleep(1)
                                        if str(226) in resp:
                                            Globvar.setMonthClockFileToken(False)
                                            print(f"Transferência completa | código = {226}\n")
                                        else:
                                            print(f"{resp}\n")

                                except ValueError as ex:
                                    print(f"Não foi possível transferir o arquivo {chave} {localdynpath}\n")
                                    failedtrans.append(localdynpath)
                            else:
                                try:
                                    with open(str(localdynpath), 'rb') as file:
                                        resp = ftps_client.storbinary('STOR {}'.format(filenamelower), file)
                                        # resp = [226]
                                        time.sleep(1)
                                        if str(226) in resp:
                                            print(f"Transferência completa | código = {226}\n")
                                        else:
                                            print(f"{resp}\n")
                                except ValueError as ex:
                                    message = f"Não foi possível transferir o arquivo {chave}: {localdynpath}\n"
                                    failedtrans.append(message)
                        else:
                            message = f"O caminho {localdynpath} não foi encontrado!"
                            failedtrans.append(message)

                    ''' REALIZA TRANSFERÊNCIA UTCR '''

                    utcrmessage = "Preparando a transferência de arquivos UTCR!"
                    print(f"\n{utcrmessage}")
                    transferlogger.info(f"{utcrmessage}")

                    for chaveparam, filename in listOfFilesToTransferToUTCR.items():
                        labRootFileDESTpath = f"/data/UTCr/{labname}"
                        # Caminho "/data/UTCr/INXE/CLOCK"
                        # print(f"chave = {chave} | filename =  {filename}")
                        chave_lower = str(chaveparam).lower()
                        filenameTo = str(filename)

                        origdir = getOrigDir(chave_lower)

                        localdynpath = os.path.join(origdir, filename)
                        # print(f"localdynpath UTCR = {localdynpath}", os.path.exists(localdynpath))

                        if chaveparam == "CLOCK":
                            relativeFileDESTpath = f"{labRootFileDESTpath}/CLOCK"
                        elif "CGGTTS" in chaveparam:
                            relativeFileDESTpath = f"{labRootFileDESTpath}/CGGTTS"
                        elif "RINEX" in chaveparam:
                            relativeFileDESTpath = f"{labRootFileDESTpath}/RINEX"
                        else:
                            relativeFileDESTpath = f"{labRootFileDESTpath}/{chaveparam}"

                        ftps_client.cwd(relativeFileDESTpath)  # change into "debian" directory
                        fileDESTpath = f"{relativeFileDESTpath}/{filenameTo}"

                        if os.path.exists(localdynpath):

                            print(f"Iniciando a transferência:\nOrigem: {localdynpath}\nDestino: {fileDESTpath}")

                            if chave_lower in ["cggtts_g", "cggtts_r", "cggtts_e", "cggtts_c"]:

                                try:
                                    with open(str(localdynpath), 'rb') as file:
                                        resp = ftps_client.storlines('STOR {}'.format(filenameTo), file)
                                        time.sleep(2)
                                        if str(226) in resp:
                                            print(f"Transferência completa | código = {226}\n")
                                        else:
                                            print(f"{resp}\n")
                                except ValueError as ex:
                                    print(f"Não foi possível transferir o arquivo {chave} {localdynpath}\n")
                                    failedtrans.append(localdynpath)
                            else:
                                try:
                                    with open(str(localdynpath), 'rb') as file:
                                        resp = ftps_client.storbinary('STOR {}'.format(filenameTo), file)
                                        time.sleep(2)
                                        if str(226) in resp:
                                            print(f"Transferência completa | código = {226}\n")
                                        else:
                                            print(f"{resp}\n")
                                except ValueError as ex:
                                    message = f"Não foi possível transferir o arquivo {chave}: {localdynpath}\n"
                                    failedtrans.append(message)
                        else:
                            message = f"O caminho {localdynpath} não foi encontrado!"
                            failedtrans.append(message)

                    ftps_client.quit()
                    ftps_client.close()

                    if len(failedtrans) == 0:
                        finalstatusmessage = "Os arquivos foram atualizados com SUCESSO e a conexão FTP foi encerrada"
                        transferlogger.info(f"{finalstatusmessage}")
                        resultINFO.extend([True, finalstatusmessage])
                    else:
                        finalstatusmessage = f"Falha no envio dos arquivos: {failedtrans}"
                        transferlogger.error(f"{finalstatusmessage}")
                        resultINFO.extend([False, finalstatusmessage])

                    print(f"STATUS em uploadfiles = {finalstatusmessage}")

                except BaseException as ex:
                    message = "Não foi possível realizar a conexão {} : {}".format(contextcommtype, contextlink)
                    print(message)
                    resultINFO.append([False, message])
            else:
                # ******************************************************************************************************
                # **************************************  Realiza uma conexão SCP **************************************
                # ******************************************************************************************************
                scpmessage = f"Iniciando a conexão SCP ao repositório do {labname}"
                transferlogger.info(f"listOfFilesToTransferToUTC = {listOfFilesToTransferToUTC}")
                print(getFramedMessage(scpmessage))
                transferlogger.info(getFramedMessage(scpmessage))

                try:
                    tokenauth = False
                    ssh = createSSHClient(contextlink, 22, contextuser, getDecodedPass(contextpass, 6))
                    tokenconnect = ssh.get_transport()
                    if tokenconnect is not None:
                        tokenauth = tokenconnect.authenticated
                    if tokenauth:
                        # **********************************************************************************************
                        ssh.load_system_host_keys()
                        # Cria o cliente SCP com base no transporte SSH
                        scp = SCPClient(ssh.get_transport())
                        print("\nIniciando a transferência de arquivos UTC!")
                        for chave, filename in listOfFilesToTransferToUTC.items():
                            labRootFileDESTpath = f"/home/{contextuser}/data/UTC/{labname}/{contextrxid}"
                            filenamelower = str(filename).lower()
                            chave_lower = str(chave).lower()
                            origdir = getOrigDir(chave_lower)
                            localdynpath = os.path.join(origdir, filename)
                            # print(f"chave_lower = {chave_lower} | localdynpath = {localdynpath} | filename =  {filename}")

                            relativeFileDESTpath = None
                            if chave_lower in ["clocks", "rinex"]:
                                relativeFileDESTpath = f"{labRootFileDESTpath}/{chave}"
                            elif "cggtts" in chave_lower:
                                relativeFileDESTpath = f"{labRootFileDESTpath}/links/cggtts"

                            fileDESTpath = f"{relativeFileDESTpath}/{filenamelower}"

                            if os.path.exists(localdynpath):
                                print(f"Preparando a transferência:\nOrigem: {localdynpath}\nDestino: {fileDESTpath}")
                                try:
                                    scp.put(localdynpath, fileDESTpath)
                                    time.sleep(2)
                                    print(f"Transferência completa | código = {226}\n")
                                except ValueError as ex:
                                    print(f"Não foi possível transferir o arquivo {chave} {localdynpath}\n")
                                    failedtrans.append(localdynpath)
                            else:
                                print(f"O caminho {localdynpath} não foi encontrado!")
                                failedtrans.append(localdynpath)

                        ''' REALIZA TRANSFERÊNCIA UTCR '''

                        print(f"Iniciando a transferência de arquivos UTCR!")

                        for chave, filename in listOfFilesToTransferToUTCR.items():

                            labRootFileDESTpath = f"/home/{contextuser}/data/UTCr/{labname}/{contextrxid}"
                            filenameTo = str(filename)
                            chave_lower = str(chave).lower()
                            origdir = getOrigDir(chave_lower)
                            localdynpath = os.path.join(origdir, filename)

                            relativeFileDESTpath = None
                            if chave_lower in ["clock", "rinex"]:
                                relativeFileDESTpath = f"{labRootFileDESTpath}/{chave}"
                            elif "cggtts" in chave_lower:
                                relativeFileDESTpath = f"{labRootFileDESTpath}/CGGTTS"
                            # relativeFileDESTpath = f"{labRootFileDESTpath}/{chave}"

                            fileDESTpath = f"{relativeFileDESTpath}/{filenameTo}"

                            if os.path.exists(localdynpath):
                                print(f"Preparando a transferência:\nOrigem: {localdynpath}\nDestino: {fileDESTpath}")
                                try:
                                    scp.put(localdynpath, fileDESTpath)
                                    time.sleep(1)
                                    print(f"Transferência completa | código = {226}\n")
                                except ValueError as ex:
                                    print(f"Não foi possível transferir o arquivo {chave} {localdynpath}\n")
                                    failedtrans.append(localdynpath)
                            else:
                                print(f"O caminho {localdynpath} não foi encontrado!")
                                failedtrans.append(localdynpath)

                        scp.close()
                        ssh.close()
                        message = "Os arquivos foram atualizados e a conexão SCP foi encerrada\n"
                        resultINFO.append([True, message])
                    else:

                        ssh.close()
                        if not tokenconnect:
                            message = "Erro de conexão | Verifique a disponibilidade de rede\n"
                            resultINFO.extend([False, message])
                        elif not tokenauth:
                            message = "Erro de autenticação no servidor {}\n".format(contextlink)
                            resultINFO.extend([False, message])

                        transferlogger.error(f"{message}")
                        print(message)
                        failedtrans.append(message)
                        Globvar.setGlobalLogError(message)

                except ConnectionError as excon:
                    message = "Não foi possível realizar a conexão {} : {}\n{}".format(contextcommtype, contextlink, excon)
                    print(message)
                    resultINFO.append([False, message])
    else:
        message = f"A transferência de arquivos NÃO foi realizada pois a variável [ preconditiontotransfer = {preconditiontotransfer} ] não permite!"
        print(message)
        resultINFO.append([False, message])

    return list(resultINFO)
