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
    context_datetime = getDateTimeFromMJD(context_mjd)
    context_year = context_datetime.year
    context_month = context_datetime.month
    root_path = "{}".format(self.getRootPath())
    short_year = context_year - 2000
    lab_name = self.getLabName()
    context_mjd = self.getCurrentMJD()
    lab_id = self.getLabID()
    rx_id = self.getRxID()
    lab_code = self.getLabCode()
    clock_code = self.getClockCode()
    context_doy = self.getCurrentDOY()

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
                      "shortyear": short_year,
                      "contextmonth": context_month,
                      "monthnum": context_month
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