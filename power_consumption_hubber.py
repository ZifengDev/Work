#!/usr/bin/env python
# -*- coding: utf-8 -*-

import collections
import datetime
import fileinput
import getopt
import re
import StringIO
import subprocess
import sys
import os
import errno
import os.path
from datetime import *
import time


def tacAndcheckScreenStatus(inputFileName):
    rawList = []
    fp = open(inputFileName)
    while True:
        lines = fp.readlines()
        if not lines: break
        rawList.extend(lines)
    fp.close()

    detectionPerPID = False
    screenIsOn = "INVALID"
    retList = []
    for index in range(-1, -len(rawList)-1, -1):
        line = rawList[index]
        if not detectionPerPID and line.startswith("Per-PID"):
            detectionPerPID = True
            retList.append(line)
            continue
        elif line.startswith("Battery History") or not line:
            retList.append(line)
            break
        elif not detectionPerPID or line.isspace():
            continue
        retList.append(line)

        if screenIsOn == "INVALID":
            if r"+screen" in line:
                screenIsOn = "false"    # screen is off previously
            elif r"-screen" in line:
                screenIsOn = "true" # screen is on previously

    return (retList, screenIsOn)


def preHandleLine(s):
    lineValid = False
    statusCharging = False
    statusDischarging = False
    screenOff = False
    screenOn = False

    fmt = r"\dms \d{3}"
    p = re.compile(fmt)
    match = p.search(s)
    if match is not None:
        lineValid = True

    if r"status=charging" in s:
        statusCharging = True
    elif r"status=discharging" in s:
        statusDischarging = True

    if r"-screen" in s:
        screenOff = True
    elif r"+screen" in s:
        screenOn = True

    return (lineValid, statusCharging, statusDischarging, screenOff, screenOn)


def parseTime(s, fmt):
    if s == "0": return 0

    p = re.compile(fmt)
    match = p.search(s)
    try:
        d = match.groupdict()
    except IndexError:
        return -1

    ret = 0
    if d["day"]: ret += int(d["day"])*60*60*24*1000
    if d["hour"]: ret += int(d["hour"])*60*60*1000
    if d["min"]: ret += int(d["min"])*60*1000
    if d["sec"]: ret += int(d["sec"])*1000
    if d["ms"]: ret += int(d["ms"])
    return ret


def getTimeFromMs(timeInMs):
    msTime = int(timeInMs)
    sTime = 0
    mTime = 0
    hTime = 0
    dTime = 0
    sTime = msTime / 1000
    msTime = msTime % 1000
    if not sTime:
        return "%d%s" % (msTime, "ms")
    mTime = sTime/60
    sTime = sTime%60
    if not mTime:
        return "%d%s%d%s" % (sTime, "s", msTime, "ms")
    hTime = mTime/60
    mTime = mTime%60
    if not hTime:
        return "%d%s%d%s%d%s" % (mTime, "m", sTime, "s", msTime, "ms")
    dTime = hTime/24
    hTime = hTime%24
    if not dTime:
        return "%d%s%d%s%d%s%d%s" % (hTime, "h", mTime, "m", sTime, "s", msTime, "ms")
    return "%d%s%d%s%d%s%d%s%d%s" % (dTime, "d", hTime, "h", mTime, "m", sTime, "s", msTime, "ms")


def measureTimeBegin():
    mStartTime = datetime.now()
    return mStartTime


def measureTimeEnd(mStartTime):
    mEndTime = datetime.now()
    deltaTm = mEndTime - mStartTime
    print float(str(deltaTm).split(':')[-1])


def getTotalInfo(inputFileName):
    inputFile = inputFileName

    detectionPerPID = False
    inCharging = False
    chargingStateChanging = False
    dischargeTotalTimeInt = 0    # 总的discharge的时间
    dischargeTotalBatteryInt = 0 # 总的discharge的电量
    startTimeInt = 0   # 每一段的开始时间
    startBatteryInt = 0    # 每一段的开始电量
    currentTimeInt = 0 # 当前时间
    currentBatteryInt = 0  # 当前电量
    prevTimeInt = 0    # 上一个event的时间
    prevBatteryInt = 0 # 上一个event的电量
    contTimeInt = 0    # 这一段的持续时间
    contBatteryInt = 0 # 这一次的下降电量
    dischargeStartTimeInt = 0    # 开始放电时刻的时间
    dischargeStartBatteryInt = 0 # 开始放电时刻的电量
    dischargeStr = "DischargeStatus:"
    chargeStartTimeInt = 0    # 开始充电时刻的时间
    chargeStartBatteryInt = 0 # 开始充电时刻的电量
    chargeStr = "ChargeStatus:"
    screenIsON = "INVALID"  # 屏幕状态
    screenStateChangeTimeInt = 0 # 屏幕状态改变时刻的时间
    dischargeScreenONTimeInt = 0 # 每一段discharge时总的screen ON时间
    dischargeScreenOFFTimeInt = 0    # 每一段discharge时总的screen OFF时间
    sectionStartScreenIsON = "INVALID"
    sectionStartScreenTimeInt = 0
    sectionStartBatteryInt = 0
    sectionScreenOFFStr = "ScreenOffStatus:"
    sectionScreenONStr = "ScreenOnStatus:"

    (rawList, screenIsON) = tacAndcheckScreenStatus(inputFile)
    #tm = measureTimeBegin()
    for line in rawList:
        if not detectionPerPID and line.startswith("Per-PID"):
            detectionPerPID = True
            continue
        elif line.startswith("Battery History") or not line:
            break
        elif not detectionPerPID or line.isspace():
            continue

        line = line.strip()
        (lineValid, preSC, preSD, preSF, preSN) = preHandleLine(line)
        if not lineValid: continue

        if (not inCharging) and preSC:
            inCharging = True
            chargingStateChanging = True
        elif inCharging and preSD:
            inCharging = False
            chargingStateChanging = True

        splitLine = line.split()
        (lineTime, lineBatteryLevel) = splitLine[:2]
        fmt = r"-((?P<day>\d+)d)?((?P<hour>\d+)h)?((?P<min>\d+)m)?((?P<sec>\d+)s)?((?P<ms>\d+)ms)?$"
        currentTimeInt = parseTime(lineTime, fmt)
        if currentTimeInt < 0:
            continue
        currentBatteryInt = int(lineBatteryLevel)

        if not startTimeInt:
            startTimeInt = currentTimeInt
            startBatteryInt = currentBatteryInt
            prevTimeInt = currentTimeInt
            prevBatteryInt = currentBatteryInt
            dischargeStartTimeInt = currentTimeInt
            dischargeStartBatteryInt = currentBatteryInt
            chargeStartTimeInt = currentTimeInt
            chargeStartBatteryInt = currentBatteryInt
            screenStateChangeTimeInt = currentTimeInt
            continue

        if prevBatteryInt == currentBatteryInt:
            if chargingStateChanging:   # charging status is changing
                if inCharging:  # From discharging to charging
                    contTimeInt = currentTimeInt - startTimeInt
                    dischargeTotalTimeInt += contTimeInt
                    # screen status
                    if screenIsON != "INVALID":
                        if preSN or (screenIsON == "false"): # screen is ON from OFF or screen is OFF state
                            dischargeScreenOFFTimeInt += currentTimeInt - screenStateChangeTimeInt
                        elif preSF or (screenIsON == "true"):   # screen is OFF from ON or screen is ON state
                            dischargeScreenONTimeInt += currentTimeInt - screenStateChangeTimeInt
                    if dischargeStartTimeInt:
                        contTimeInt = currentTimeInt - dischargeStartTimeInt
                        contBatteryInt = dischargeStartBatteryInt - currentBatteryInt
                        dischargeStr = "%s%s%u%s%u%s%u%s%u%s%u%s%u%s%u%s%u" % (dischargeStr, " startTime-", dischargeStartTimeInt, ",endTime-", currentTimeInt, ",dischargeTime-", contTimeInt, ",startCount-", dischargeStartBatteryInt, ",endCount-", currentBatteryInt, ",dischargeCount-", contBatteryInt, ",screenOFFTime-", dischargeScreenOFFTimeInt, ",screenONTime-", dischargeScreenONTimeInt)

                    chargeStartTimeInt = currentTimeInt
                    chargeStartBatteryInt = currentBatteryInt
                    dischargeStartTimeInt = 0
                    dischargeScreenOFFTimeInt = 0
                    dischargeScreenONTimeInt = 0
                # if inCharging
                else:   # From charging to discharging
                    if chargeStartTimeInt:
                        contTimeInt = currentTimeInt - chargeStartTimeInt
                        contBatteryInt = currentBatteryInt - chargeStartBatteryInt
                        chargeStr = "%s%s%u%s%u%s%u%s%u%s%u%s%u" % (chargeStr, " startTime-", chargeStartTimeInt, ",endTime-", currentTimeInt, ",chargeTime-", contTimeInt, ",startCount-", chargeStartBatteryInt, ",endCount-", currentBatteryInt, ",chargeCount-", contBatteryInt)

                    dischargeStartTimeInt = currentTimeInt
                    dischargeStartBatteryInt = currentBatteryInt
                    chargeStartTimeInt = 0
                    # screen status
                    if screenIsON != "INVALID":
                        screenStateChangeTimeInt = currentTimeInt
                        dischargeScreenOFFTimeInt = 0
                        dischargeScreenONTimeInt = 0

                startTimeInt = currentTimeInt
                startBatteryInt = currentBatteryInt

                sectionStartScreenIsON = "INVALID"
            # if chargingStateChanging
            else:   # charging status stay non-changed
                # screen status
                if screenIsON != "INVALID" and not inCharging:
                    if preSN:   # screen is ON from OFF
                        dischargeScreenOFFTimeInt += currentTimeInt-screenStateChangeTimeInt
                    elif preSF: # screen is OFF from ON
                        dischargeScreenONTimeInt += currentTimeInt - screenStateChangeTimeInt
        # if prevBatteryInt == currentBatteryInt
        elif prevBatteryInt > currentBatteryInt:    # discharging
            if chargingStateChanging:
                if not inCharging:  # From charging to discharging
                    if chargeStartTimeInt:
                        contTimeInt = prevTimeInt - chargeStartTimeInt
                        contBatteryInt = prevBatteryInt - chargeStartBatteryInt
                        chargeStr = "%s%s%u%s%u%s%u%s%u%s%u%s%u" % (chargeStr, " startTime-", chargeStartTimeInt, ",endTime-", prevTimeInt, ",chargeTime-", contTimeInt, ",startCount-", chargeStartBatteryInt, ",endCount-", prevBatteryInt, ",chargeCount-", contBatteryInt)

                    dischargeStartTimeInt = currentTimeInt
                    dischargeStartBatteryInt = currentBatteryInt
                    chargeStartTimeInt = 0
                    # screen status
                    if screenIsON != "INVALID":
                        screenStateChangeTimeInt = currentTimeInt
                        dischargeScreenOFFTimeInt = 0
                        dischargeScreenONTimeInt = 0
                # if not inCharging
                else:   # From discharging to charging
                    # screen status
                    if screenIsON != "INVALID":
                        if preSN or (screenIsON == "false"):    # screen is ON from OFF or screen is OFF state
                            dischargeScreenOFFTimeInt += currentTimeInt - screenStateChangeTimeInt
                        elif preSF or (screenIsON == "true"):   # screen is OFF from ON or screen is ON state
                            dischargeScreenONTimeInt += currentTimeInt - screenStateChangeTimeInt

                    if dischargeStartTimeInt:
                        contTimeInt = currentTimeInt - dischargeStartTimeInt
                        contBatteryInt = dischargeStartBatteryInt - currentBatteryInt
                        dischargeStr = "%s%s%u%s%u%s%u%s%u%s%u%s%u%s%u%s%u" % (dischargeStr, " startTime-", dischargeStartTimeInt, ",endTime-", currentTimeInt, ",dischargeTime-", contTimeInt, ",startCount-", dischargeStartBatteryInt, ",endCount-", currentBatteryInt, ",dischargeCount-", contBatteryInt, ",screenOFFTime-", dischargeScreenOFFTimeInt, ",screenONTime-", dischargeScreenONTimeInt)

                    chargeStartTimeInt = currentTimeInt
                    chargeStartBatteryInt = currentBatteryInt
                    dischargeStartTimeInt = 0
                    dischargeScreenOFFTimeInt = 0
                    dischargeScreenONTimeInt = 0
            # if chargingStateChanging:
            elif not chargingStateChanging and inCharging:
                inCharging = False

            if not dischargeStartTimeInt:
                dischargeStartTimeInt = startTimeInt
                dischargeStartBatteryInt = startBatteryInt
            if chargeStartTimeInt:
                chargeStartTimeInt = 0
            # screen status
            if screenIsON != "INVALID" and not inCharging:
                if preSN:   # screen is ON from OFF
                    dischargeScreenOFFTimeInt += currentTimeInt - screenStateChangeTimeInt
                elif preSF: # screen is OFF from ON
                    dischargeScreenONTimeInt += currentTimeInt - screenStateChangeTimeInt

            contTimeInt = currentTimeInt - startTimeInt
            dischargeTotalTimeInt = dischargeTotalTimeInt + contTimeInt
            contBatteryInt = prevBatteryInt - currentBatteryInt
            dischargeTotalBatteryInt = dischargeTotalBatteryInt + contBatteryInt

            startTimeInt = currentTimeInt
            startBatteryInt = currentBatteryInt

            if sectionStartScreenIsON != "INVALID":
                contTimeInt = currentTimeInt - sectionStartScreenTimeInt
                contBatteryInt = sectionStartBatteryInt - currentBatteryInt
                if sectionStartScreenIsON == "false":
                    sectionScreenOFFStr = ("%s%s%u%s%u%s%u%s%u%s%u%s%u") % (sectionScreenOFFStr, " startTime-", sectionStartScreenTimeInt, ",endTime-", currentTimeInt, ",offTime-", contTimeInt, ",startCount-", sectionStartBatteryInt, ",endCount-", currentBatteryInt, ",offCount-", contBatteryInt)
                else:
                    sectionScreenONStr = ("%s%s%u%s%u%s%u%s%u%s%u%s%u") % (sectionScreenONStr, " startTime-", sectionStartScreenTimeInt, ",endTime-", currentTimeInt, ",onTime-", contTimeInt, ",startCount-", sectionStartBatteryInt, ",endCount-", currentBatteryInt, ",onCount-", contBatteryInt)
                sectionStartScreenTimeInt = currentTimeInt
                sectionStartBatteryInt = currentBatteryInt
            elif screenIsON != "INVALID":
                sectionStartScreenIsON = screenIsON
                sectionStartScreenTimeInt = currentTimeInt
                sectionStartBatteryInt = currentBatteryInt
        # if prevBatteryInt == currentBatteryInt
        elif prevBatteryInt < currentBatteryInt:    # charging
            if chargingStateChanging:
                if inCharging:  # From discharging to charging
                    contTimeInt = prevTimeInt - startTimeInt
                    dischargeTotalTimeInt += contTimeInt
                    # screen status
                    if screenIsON != "INVALID":
                        if preSN or (screenIsON == "false"):  # screen is ON from OFF or screen is OFF state
                            dischargeScreenOFFTimeInt += currentTimeInt - screenStateChangeTimeInt
                        elif preSF or (screenIsON == "true"): # screen is OFF from ON or screen is ON state
                            dischargeScreenONTimeInt += currentTimeInt - screenStateChangeTimeInt
                    if dischargeStartTimeInt:
                        contTimeInt = prevTimeInt - dischargeStartTimeInt
                        contBatteryInt = dischargeStartBatteryInt - prevBatteryInt
                        dischargeStr = "%s%s%u%s%u%s%u%s%u%s%u%s%u%s%u%s%u" % (dischargeStr, " startTime-", dischargeStartTimeInt, ",endTime-", prevTimeInt, ",dischargeTime-", contTimeInt, ",startCount-", dischargeStartBatteryInt, ",endCount-", prevBatteryInt, ",dischargeCount-", contBatteryInt, ",screenOFFTime-", dischargeScreenOFFTimeInt, ",screenONTime-", dischargeScreenONTimeInt)

                    chargeStartTimeInt = currentTimeInt
                    chargeStartBatteryInt = currentBatteryInt
                    dischargeStartTimeInt = 0
                    dischargeScreenOFFTimeInt = 0
                    dischargeScreenONTimeInt = 0
                # if inCharging
                else:   # From charging to discharging
                    if chargeStartTimeInt:
                        contTimeInt = currentTimeInt - chargeStartTimeInt
                        contBatteryInt = currentBatteryInt - chargeStartBatteryInt
                        chargeStr = "%s%s%u%s%u%s%u%s%u%s%u%s%u" % (chargeStr, " startTime-", chargeStartTimeInt, ",endTime-", currentTimeInt, ",chargeTime-", contTimeInt, ",startCount-", chargeStartBatteryInt, ",endCount-", currentBatteryInt, ",chargeCount-", contBatteryInt)

                    dischargeStartTimeInt = currentTimeInt
                    dischargeStartBatteryInt = currentBatteryInt
                    chargeStartTimeInt = 0
                    # screen status
                    if screenIsON != "INVALID":
                        screenStateChangeTimeInt = currentTimeInt
                        dischargeScreenOFFTimeInt = 0
                        dischargeScreenONTimeInt = 0
            # if chargingStateChanging:
            elif not chargingStateChanging and not inCharging:
                inCharging = True

            if not chargeStartTimeInt:
                chargeStartTimeInt = startTimeInt
                chargeStartBatteryInt = startBatteryInt
            if dischargeStartTimeInt:
                dischargeStartTimeInt = 0
            # screen status
            screenStateChangeTimeInt = currentTimeInt
            dischargeScreenOFFTimeInt = 0
            dischargeScreenONTimeInt = 0

            startTimeInt = currentTimeInt
            startBatteryInt = currentBatteryInt

            sectionStartScreenIsON = "INVALID"

        if chargingStateChanging:
            chargingStateChanging = False
        # screen status change
        if screenIsON != "INVALID":
            if preSN:   # screen is ON from OFF
                screenIsON = "true"
                screenStateChangeTimeInt = currentTimeInt

                sectionStartScreenIsON = "INVALID"
            elif preSF: # screen is OFF from ON
                screenIsON = "false"
                screenStateChangeTimeInt = currentTimeInt

                sectionStartScreenIsON = "INVALID"
        prevTimeInt=currentTimeInt
        prevBatteryInt=currentBatteryInt
        # if prevBatteryInt == currentBatteryInt

    #measureTimeEnd(tm)
    return (dischargeTotalTimeInt, dischargeTotalBatteryInt, dischargeStr, chargeStr ,sectionScreenOFFStr ,sectionScreenONStr)


def getStatisticsSection(dischargeTotalTimeInt, dischargeTotalBatteryInt):
    totalTimeInt = dischargeTotalTimeInt
    totalBatteryInt = dischargeTotalBatteryInt
    if not totalTimeInt or not totalBatteryInt:
        return (255, 0) # invalid number
    result = totalTimeInt * 100 / totalBatteryInt
    for index in range(48):
        if index*60*60*1000 <= result < (index+1)*60*60*1000:
            return (index, result)
    return (48, result)


def calScreenOnOffTime(screenOnInfo, screenOffInfo, dischargeStatus):
    onTime = 0
    onCount = 0
    line = screenOnInfo
    if line.startswith(r"ScreenOnStatus: startTime"):
        line = line.replace(r"ScreenOnStatus: ", " ")
        line = line.strip()
        line = line.replace(",", "-")
        for spLine in line.split():
            spStr = spLine.split("-")
            onTime += int(spStr[5])
            onCount += int(spStr[11])
    if not onCount or not onTime:
        onTime = 0
    else:
        onTime = onTime/onCount

    offTime = 0
    offCount = 0
    line = screenOffInfo
    if line.startswith(r"ScreenOffStatus: startTime"):
        line = line.replace(r"ScreenOffStatus: ", " ")
        line = line.strip()
        line = line.replace(",", "-")
        for spLine in line.split():
            spStr = spLine.split("-")
            offTime += int(spStr[5])
            offCount += int(spStr[11])
    if not offCount or not offTime:
        offTime = 0
    else:
        offTime = offTime/offCount

    dischargeOffTime = 0
    dischargeOnTime = 0
    line = dischargeStatus
    if line.startswith(r"DischargeStatus: startTime"):
        line = line.replace(r"DischargeStatus: ", " ")
        line = line.strip()
        line = line.replace(",", "-")
        for spLine in line.split():
            spStr = spLine.split("-")
            dischargeOffTime += int(spStr[13])
            dischargeOnTime += int(spStr[15])
    if not onTime or not offTime:
        averageTime = 0.0
    elif not dischargeOffTime and not dischargeOnTime:
        averageTime = 0.0
    else:
        averageTime = (float(dischargeOffTime)+float(dischargeOnTime))/(float(dischargeOffTime)/offTime+float(dischargeOnTime)/onTime)

    return "AverageScreenOffTime: %d\nAverageScreenOnTime: %d\nTotalAverageTime: %d" % (offTime, onTime, int(averageTime))


def parseArgv():
    inputFile = sys.argv[1]
    [bugDevice, bugVersion, bugReport] = inputFile.split('/')[-3:]
    directory = '%s/%s' % (bugDevice, bugVersion)
    outputFile = '%s/%s.power' % (directory, bugReport)
    #try:
    #    os.makedirs(directory)
    #except OSError as exc:
    #    if exc.errno == errno.EEXIST and os.path.isdir(directory): pass
    #    else: raise
    if not os.path.isdir(directory):
        os.makedirs(directory)
    if os.path.isfile(outputFile):
        sys.exit(0)
    return (inputFile, outputFile)


def main():
    (inputFile, outputFile) = parseArgv()
    (totalTimeInt, totalBatteryInt, dischargingInfo, chargingInfo, screenOffInfo, screenOnInfo) = getTotalInfo(inputFile)
    (section, statisticsResult) = getStatisticsSection(totalTimeInt, totalBatteryInt)
    ret = calScreenOnOffTime(screenOnInfo, screenOffInfo, dischargingInfo)
    if section < 255:
        outputStr = "Name: %s\n\nLogFileName: %s\nTotal Discharging Time: %s\nTotal Discharging Battery Count(%%): %d\nConversion Result(In 100%% Battery): %s\nTotal Discharging Time(ms): %d\nConversion Result(ms in 100%% Battery): %d\n%s\n%s\n%s\n%s\n%s" % (outputFile, inputFile, getTimeFromMs(totalTimeInt), totalBatteryInt, getTimeFromMs(statisticsResult), totalTimeInt, statisticsResult, dischargingInfo, chargingInfo, screenOffInfo, screenOnInfo, ret)
        fp = open(outputFile, 'w')
        fp.write(outputStr)
        fp.close()


def parseModuleArgv(bugReportName):
    inputFile = bugReportName
    [bugDevice, bugVersion, bugReport] = inputFile.split('/')[-3:]
    directory = '%s/%s' % (bugDevice, bugVersion)
    outputFile = '%s/%s.power' % (directory, bugReport)
    #try:
    #    os.makedirs(directory)
    #except OSError as exc:
    #    if exc.errno == errno.EEXIST and os.path.isdir(directory): pass
    #    else: raise
    if not os.path.isdir(directory):
        os.makedirs(directory)
    if os.path.isfile(outputFile):
        sys.exit(0)
    return (inputFile, outputFile)


def moduleMain(bugReportName):
    (inputFile, outputFile) = parseModuleArgv(bugReportName)
    (totalTimeInt, totalBatteryInt, dischargingInfo, chargingInfo, screenOffInfo, screenOnInfo) = getTotalInfo(inputFile)
    (section, statisticsResult) = getStatisticsSection(totalTimeInt, totalBatteryInt)
    ret = calScreenOnOffTime(screenOnInfo, screenOffInfo, dischargingInfo)
    if section < 255:
        outputStr = "Name: %s\n\nLogFileName: %s\nTotal Discharging Time: %s\nTotal Discharging Battery Count(%%): %d\nConversion Result(In 100%% Battery): %s\nTotal Discharging Time(ms): %d\nConversion Result(ms in 100%% Battery): %d\n%s\n%s\n%s\n%s\n%s" % (outputFile, inputFile, getTimeFromMs(totalTimeInt), totalBatteryInt, getTimeFromMs(statisticsResult), totalTimeInt, statisticsResult, dischargingInfo, chargingInfo, screenOffInfo, screenOnInfo, ret)
        fp = open(outputFile, 'w')
        fp.write(outputStr)
        fp.close()


if __name__ == "__main__":
    main()
