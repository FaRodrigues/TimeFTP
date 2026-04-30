from Global import GlobalVars as Globvar

rx_id = Globvar.getRxID()
lab_id = Globvar.getLabID()


sbfnamefile = "{}{}{:03d}0.{:02d}_".format(lab_id, rx_id, gwnr_doy, gwnr_shortyear)

gwnr_datetime = getDateTimeFromMJD(gwnr_mjd)
gwnr_shortyear = gwnr_datetime.year - 2000
gwnr_doy = gwnr_datetime.timetuple().tm_yday

dictGenCGG = Globvar.getDictGenerateCGGTTS()

for key, value in dictGenCGG.items():
    cggttsfilename = "{}Z{}{}{:.3f}".format(key, lab_id, rx_id, np.divide(gwnr_mjd, 1000))


rinexfilename = "{}{}{:03d}0.{:02d}{}".format(lab_id, rx_id, context_doy, context_shortyear, chaveConstraint)

rinex_yesterday_path = os.path.join(logpath, "{:02d}{:03d}".format(ontemSHORTYEAR, ontemDOY))
rinex_today_path = os.path.join(logpath, "{:02d}{:03d}".format(SHORTYEAR, DOY))