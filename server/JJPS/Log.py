import logging

_loggerSetup = False
def getLogger(config = None):
    global _loggerSetup

    if (_loggerSetup == False):
        logger = logging.getLogger('JJPS')
        logFormatter = logging.Formatter('%(asctime)s (%(process)d) %(levelname)s: %(message)s')
        fileHandler = logging.FileHandler(config.get("Station", "logPath"))
        fileHandler.setFormatter(logFormatter)
        level = getattr(logging, config.get("Station", "defaultLogLevel").upper())
        logger.addHandler(fileHandler)
        logger.setLevel(level)
        _loggerSetup = True
        return logger
    else:
        return logging.getLogger("JJPS")
