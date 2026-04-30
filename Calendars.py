# -*- coding: utf-8 -*-
# TimeFTP version 2.5 (2025)
# Autor: Fernando Rodrigues (Inmetro)

from collections import deque

import numpy as np
from astropy.time import Time


class RapidYear:
    def __init__(self, refyear):
        self.rapidmjdweeklist = None
        self.monthmjddeque = None
        self.refyear = refyear
        self.STARTMJD = int(Time('{}-01-01'.format(refyear)).to_value('mjd'))
        self.STOPMJD = int(Time('{}-12-31'.format(refyear)).to_value('mjd'))
        finalofstartmjd = self.STARTMJD % 10

        if finalofstartmjd in [4, 9]:
            retroAdjust = 2
        else:
            retroAdjust = 4

        circtStartMjd = self.STARTMJD - retroAdjust
        circtFinalMjd = self.STOPMJD + 4

        self.mjdlist = range(circtStartMjd, circtFinalMjd, 1)
        dmjdlist = deque()
        dmjdlist.extend(self.mjdlist)
        mjddeque = deque()
        monthdmjdlist = dmjdlist

        count = 0

        for x in range(len(self.mjdlist)):
            pedaco = list(dmjdlist)
            if pedaco[2] % 10 in [4, 9]:
                mjddeque.append(pedaco[0:5])
                count = count + 1
            dmjdlist.rotate(-1)

        self.setRapidWeekList(np.array(mjddeque))
        tempdeque = deque()

        for x in range(len(self.mjdlist)):
            pedaco = list(monthdmjdlist)
            if pedaco[0] % 10 in [4, 9]:
                tempdeque.append(pedaco[0])

            monthdmjdlist.rotate(-1)

        self.setCirctMonthList(tempdeque)

    def setCirctMonthList(self, monthmjddeque):
        self.monthmjddeque = monthmjddeque

    def getCirctMonthList(self):
        return self.monthmjddeque

    def setRapidWeekList(self, rmjdwl):
        self.rapidmjdweeklist = rmjdwl

    def getRapidWeekList(self):
        rmwl = self.rapidmjdweeklist
        minv = min([sublist[0] for sublist in rmwl])
        maxv = max([sublist[-1] for sublist in rmwl])
        return [[minv, maxv], rmwl]

    def getRapidMjdWeekNumber(self, mjd):
        contextWeekList = self.getRapidWeekList()
        rapidmjdweeknumber = 0
        rapidmjdweekout = []
        descript = "calendário RAPID {}".format(self.refyear)
        # Registra o mjd inicial e mjd final do calendário do processo RAPID do BIPM
        minmjd = contextWeekList[0][0]
        maxmjd = contextWeekList[0][1]
        # Verifica se o mjd parâmetro está no calendário do '''ano RAPID'''
        if minmjd <= mjd <= maxmjd:
            indexweeklist = 0
            for rapidmjdweek in contextWeekList[1]:
                indexweeklist = indexweeklist + 1
                if mjd in rapidmjdweek:
                    rapidmjdweeknumber = indexweeklist
                    rapidmjdweekout = rapidmjdweek
        else:
            print("MJD não pertence ao {}".format(descript), '|',
                  "O {} começa no MJD {} e termina no MJD {}".format(descript, minmjd, maxmjd))
        return [rapidmjdweeknumber, rapidmjdweekout]