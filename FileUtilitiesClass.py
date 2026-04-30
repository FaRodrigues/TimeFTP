# -*- coding: utf-8 -*-
# TimeFTP version 2.5 (2025)
# Autor: Fernando Rodrigues (Inmetro)

import datetime
import fileinput
import os
import re
import shutil
import time
import zipfile
from pathlib import Path

from astropy.time import Time

def getFramedMessage(midmsg):
    linetext = "*" * (len(midmsg) + 4)
    intermessage = f"\n{linetext}\n{midmsg}\n{linetext}\n"
    return intermessage

def getDateTimeFromMJD(mjdparam):
    tmjd = Time(mjdparam, format='mjd')
    stringdate = Time(tmjd.to_value('iso'), out_subfmt='date_hms').iso
    return datetime.datetime.fromisoformat(stringdate)

def getDictFromLists(keys, values):
    return dict(zip(keys, values))

def copyXmlPropertyFiles(src_dir, dest_dir):
    origsrc = src_dir
    target = dest_dir
    files = os.listdir(origsrc)
    for filename in files:
        shutil.copy2(os.path.join(origsrc, filename), target)


def copyRinexAndParamFiles(dictrinex):
    '''
    Copia os arquivos RINEX de OBSERVAÇÃO e NAVEGAÇÃO com nomes próprios para o
    processamento com o programa R2CGGTTS v8.3
    '''
    success = False
    rinexPreviousfullpathExists = True

    if rinexPreviousfullpathExists:
        for chave, origdestlist in dictrinex.items():
            print("\nIniciando a cópia do arquivo {} para o caminho de processamento temporário".format(
                str(chave).upper()))
            # print(f"{chave}", f"{origdestlist}")
            origdestpaths = origdestlist
            origem = origdestpaths[0]
            destino = origdestpaths[1]
            print(f"Origem: {origem} | Destino: {destino}")
            try:
                shutil.copyfile(origem, destino)
                success = True
            except OSError as ve:
                success = False
            time.sleep(0.1)
    if success:
        print(f"Os arquivos {dictrinex} foram copiados com successo em copyRinexAndParamFiles\n")
    return success


def copyTemporaryCGGTTSFiles(dictcgg, sobrescreve, funmjd):
    '''
    Copia os arquivos RINEX de OBSERVAÇÃO e NAVEGAÇÃO com nomes próprios para o
    processamento com o programa R2CGGTTS v8.3
    '''
    success = False
    for chave, origdestlist in dictcgg.items():
        print("Iniciando a cópia do arquivo {} temporário para o caminho de LOG".format(str(chave).upper()))
        tokenrealize = True
        print(f"{chave}", f"{origdestlist}")
        origdestpaths = origdestlist
        origem = origdestpaths[0]
        destino = origdestpaths[1]

        if not sobrescreve:
            tokenrealize = not (os.path.exists(destino))
            # print(f"{tokenrealize}", f"{tokenrealize}")
        else:
            tokenrealize = os.path.exists(origem)

        print(f"Origem: {origem} | Destino: {destino}")

        if tokenrealize:
            try:
                shutil.copyfile(origem, destino)
                success = True
            except ValueError as ve:
                success = False
        time.sleep(0.1)

    print(f"Os arquivos {dictcgg} foram copiados com successo em copyTemporaryCGGTTSFiles\n")
    return success


def copyFilesToLinks(dictfiles, sobrescreve, sezip):
    '''
    Copia os arquivos RINEX, CGGTTS e CLOCK para os Links definidos no formulário
    '''
    success = [False]
    for chave, origdestlist in dictfiles.items():
        print("Iniciando a tentativa de cópia do arquivo {} para o caminho Links".format(str(chave).upper()))
        tokenrealize = True
        # print(f"{chave}", f"{origdestlist}")
        origdestpaths = origdestlist
        origem = origdestpaths[0]
        destino = origdestpaths[1]
        message = None

        if not sobrescreve:
            tokenrealize = not (os.path.exists(destino))
            # print(f"{tokenrealize}", f"{tokenrealize}")
        else:
            tokenrealize = os.path.exists(origem)

        # print(f"Origem Buscada: {origem} | Destino Buscado: {destino}")

        if tokenrealize:

            if sezip:
                try:
                    destinozip = os.path.join(Path(destino).parent, "{}.zip".format(Path(destino).name))
                    print(f"destinozip em copyFilesToLinks = {destinozip}")
                    # time.sleep(10)
                    with zipfile.ZipFile(destinozip, 'w', zipfile.ZIP_DEFLATED) as filezip:
                        filezip.write(origem, Path(origem).name)
                except ValueError as ve:
                    success[0] = False
            else:
                try:
                    shutil.copyfile(origem, destino)
                    success[0] = True
                except ValueError as ve:
                    success[0] = False

            time.sleep(0.1)

            if success[0]:
                message = f"\nO arquivo {origem} foi copiado com successo em copyFilesToLinks"
                print(message)
        else:
            message = f"\nO arquivo {origem} NÃO foi copiado em copyFilesToLinks"
            print(message)

        success.append(message)

    return success

def copyFiles(dictfiles, sobrescreve, sezip):
    '''
    Copia os arquivos RINEX, CGGTTS e CLOCK para os Links definidos no formulário
    '''
    success = [False]
    for chave, origdestlist in dictfiles.items():
        print("Iniciando a tentativa de cópia do arquivo {} para o caminho Links".format(str(chave).upper()))
        tokenrealize = True
        # print(f"{chave}", f"{origdestlist}")
        origdestpaths = origdestlist
        origem = origdestpaths[0]
        destino = origdestpaths[1]
        message = None

        if not sobrescreve:
            tokenrealize = not (os.path.exists(destino))
            # print(f"{tokenrealize}", f"{tokenrealize}")
        else:
            tokenrealize = os.path.exists(origem)

        # print(f"Origem Buscada: {origem} | Destino Buscado: {destino}")

        if tokenrealize:

            if sezip:
                try:
                    destinozip = os.path.join(Path(destino).parent, "{}.zip".format(Path(destino).name))
                    print(f"destinozip em copyFiles = {destinozip}")
                    # time.sleep(10)
                    with zipfile.ZipFile(destinozip, 'w', zipfile.ZIP_DEFLATED) as filezip:
                        filezip.write(origem, Path(origem).name)
                except ValueError as ve:
                    success[0] = False
            else:
                try:
                    shutil.copyfile(origem, destino)
                    success[0] = True
                except ValueError as ve:
                    success[0] = False

            time.sleep(0.1)

            if success[0]:
                message = f"O arquivo {origem} foi copiado com successo em copyFiles"
                print(getFramedMessage(message))
        else:
            message = f"O arquivo {origem} NÃO foi copiado em copyFiles"
            print(getFramedMessage(message))

        success.append(message)

    return success

def getReplacementsDict(mjdatual, funmjd):
    chavelist = []
    valorlist = []

    for mjddiff in range(-2, +3):

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


def copy_modified_rinex_files(dictfiles, sobrescreve, gwnr_mjd, funmjd, sezip):
    '''
    Copia os arquivos RINEX, CGGTTS e CLOCK para os Links definidos no formulário
    '''
    print(gwnr_mjd, funmjd)
    # time.sleep(10)
    success = [False]
    for chave, origdestlist in dictfiles.items():
        print("Iniciando a cópia do arquivo {} para o caminho Links".format(str(chave).upper()))
        tokenrealize = True
        print(f"copy_modified_rinex_files => {chave}", f"{origdestlist}")
        origdestpaths = origdestlist
        origem = origdestpaths[0]
        destino = origdestpaths[1]

        print(f"Origem: {origem} | Destino: {destino}")

        resultX = getReplacementsDict(funmjd, gwnr_mjd)
        rinex_replacements = getDictFromLists(resultX[0], resultX[1])

        print(f"A substituição de data será {rinex_replacements}")

        if os.path.exists(origem):
            with fileinput.FileInput(origem, inplace=True) as file:
                for line in file:
                    try:
                        pattern = re.compile("|".join(map(re.escape, rinex_replacements.keys())))
                        result = pattern.sub(lambda m: rinex_replacements[m.group(0)], line)
                    except BaseException as ex:
                        break
                    print(result, end='')

            file.close()

            try:
                nomesdiferentes = os.path.basename(origem) != os.path.basename(destino)
                novonome = os.path.join(os.path.dirname(origem), os.path.basename(destino))
                midmsg = f"Renomeando {origem} para {novonome}"
                linetext = "*" * (len(midmsg) + 4)
                intermessage = f"\n{linetext}\n{midmsg}\n{linetext}\n"
                print(intermessage)

                shutil.copy2(origem, novonome)
                os.remove(origem)
                origem = novonome
            except FileExistsError as fee:
                pass

        if not sobrescreve:
            tokenrealize = not (os.path.exists(destino))
            # print(f"{tokenrealize}", f"{tokenrealize}")
        else:
            tokenrealize = os.path.exists(origem)


        if tokenrealize:

            if sezip:
                try:
                    destinozip = os.path.join(Path(destino).parent, "{}.zip".format(Path(destino).name))
                    with zipfile.ZipFile(destinozip, 'w', zipfile.ZIP_DEFLATED) as filezip:
                        filezip.write(origem, Path(origem).name)
                except ValueError as ve:
                    success[0] = False
            else:
                try:
                    shutil.copyfile(origem, destino)
                    success[0] = True
                except ValueError as ve:
                    success[0] = False

        time.sleep(0.1)

        if success[0]:
            message = "\nOs arquivos foram copiados com successo em copy_modified_rinex_files"
            print(message)
        else:
            message = "\nOs arquivos NÃO foram copiados em copy_modified_rinex_files"
        success.append(message)
    return success


def copy_modified_cggtts_files(dictfiles, sobrescreve, from_mjd, to_mjd, sezip):
    '''
    Copia os arquivos RINEX, CGGTTS e CLOCK para os Links definidos no formulário
    '''
    success = [False]
    for chave, origdestlist in dictfiles.items():
        print("Iniciando a cópia do arquivo {} para o caminho Links".format(str(chave).upper()))
        tokenrealize = True
        print(f"copy_modified_cggtts_files => {chave}", f"{origdestlist}")
        origdestpaths = origdestlist
        origem = origdestpaths[0]
        destino = origdestpaths[1]

        print(f"Origem: {origem} | Destino: {destino}")

        replacements = {str(from_mjd): str(to_mjd)}
        print(f"A substituição de MJD será {replacements}")

        if os.path.exists(origem):
            with fileinput.FileInput(origem, inplace=True) as file:
                for line in file:
                    try:
                        pattern = re.compile("|".join(map(re.escape, replacements.keys())))
                        result = pattern.sub(lambda m: replacements[m.group(0)], line)
                    except BaseException as ex:
                        break
                    print(result, end='')

            file.close()

            try:
                # nomesiguais = origem == destino
                # Cria um nome local para armazenar/clonar o conteúdo de origem com basename do destino
                novonome = os.path.join(os.path.dirname(origem), os.path.basename(destino))
                midmsg = f"Renomeando {origem} para {novonome}"
                linetext = "*" * (len(midmsg) + 4)
                intermessage = f"\n{linetext}\n{midmsg}\n{linetext}\n"
                print(intermessage)
                # Sobrescreve ou cria arquivo local com conteúdo de origem e basename do destino
                os.replace(origem, novonome)
                # Define que a origem da cópia é o arquivo modificado e renomeado
                origem = novonome
            except FileExistsError as fee:
                pass

        if not sobrescreve:
            tokenrealize = not (os.path.exists(destino))
            # print(f"{tokenrealize}", f"{tokenrealize}")
        else:
            tokenrealize = os.path.exists(origem)

        if tokenrealize:

            if sezip:
                try:
                    destinozip = os.path.join(Path(destino).parent, "{}.zip".format(Path(destino).name))
                    with zipfile.ZipFile(destinozip, 'w', zipfile.ZIP_DEFLATED) as filezip:
                        filezip.write(origem, Path(origem).name)
                except ValueError as ve:
                    success[0] = False
            else:
                try:
                    shutil.copyfile(origem, destino)
                    success[0] = True
                except ValueError as ve:
                    success[0] = False

        time.sleep(0.1)

        if success[0]:
            message = "\nOs arquivos foram copiados com successo em copy_modified_cggtts_files"
            print(message)
        else:
            message = "\nOs arquivos NÃO foram copiados em copy_modified_cggtts_files"
        success.append(message)
    return success

def copy_and_replace(source_path, destination_path):
    if os.path.exists(destination_path):
        print(f"Removendo o arquivo: {destination_path}")
        os.remove(destination_path)
    shutil.copy2(source_path, destination_path)