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
import time
import os
import errno
import os.path
import argparse
from jinja2 import Template


totalDischargingTime = 0
totalDischargingCount = 0
totalScreenOffTime = 0
totalScreenOnTime = 0
totalScreenOffProp = 0.0
totalValidCount = 0
totalOffTime = 0
totalOffCount = 0
totalOnTime = 0
totalOnCount = 0
totalAverageScreenOffTime = 0
totalAverageScreenOnTime = 0
totalAverageTime = 0

gValidDevice = 0
gValidCount = 0
gDischargingCount = 0
gDischargingTime = 0
gScreenOffTime = 0
gScreenOnTime = 0
gScreenOffProp = []
gOffCount = 0
gOffTime = 0
gOnCount = 0
gOnTime = 0
gAverageSOFFT = []
gAverageSONT = []
gAverageT = []

def initStatistics():
    global gValidDevice, gValidCount, gDischargingCount, gDischargingTime, gScreenOffTime, gScreenOnTime, gScreenOffProp, gOffCount, gOffTime, gOnCount, gOnTime
    global gAverageSOFFT, gAverageSONT, gAverageT
    gValidDevice = 0
    gValidCount = 0
    gDischargingCount = 0
    gDischargingTime = 0
    gScreenOffTime = 0
    gScreenOnTime = 0
    gOffCount = 0
    gOffTime = 0
    gOnCount = 0
    gOnTime = 0
    gScreenOffProp = []
    gAverageSOFFT = []
    gAverageSONT = []
    gAverageT = []
    for index in range(0, 10):
        tempStr = "%d%%-%d%%" % (index*10, (index+1)*10)
        gScreenOffProp.append([tempStr, 0, 0.0])
    for index in range(0, 10):
        tempStr = "%dm-%dm" % (index, index+1)
        gAverageSOFFT.append([tempStr, 0, 0.0])
        gAverageSONT.append([tempStr, 0, 0.0])
        gAverageT.append([tempStr, 0, 0.0])
    gAverageSOFFT.append([">10m", 0, 0.0])
    gAverageSONT.append([">10m", 0, 0.0])
    gAverageT.append([">10m", 0, 0.0])


def addToStatistics():
    global totalDischargingTime, totalDischargingCount, totalScreenOffTime, totalScreenOnTime, totalScreenOffProp, totalValidCount, totalOffTime, totalOffCount, totalOnTime, totalOnCount
    global totalAverageScreenOffTime, totalAverageScreenOnTime, totalAverageTime
    global gValidDevice, gValidCount, gDischargingCount, gDischargingTime, gScreenOffTime, gScreenOnTime, gScreenOffProp, gOffCount, gOffTime, gOnCount, gOnTime
    global gAverageSOFFT, gAverageSONT, gAverageT
    gValidDevice += 1
    gValidCount += totalValidCount
    gDischargingCount += totalDischargingCount
    gDischargingTime += totalDischargingTime
    gScreenOffTime += totalScreenOffTime
    gScreenOnTime += totalScreenOnTime
    gOffCount += totalOffCount
    gOffTime += totalOffTime
    gOnCount += totalOnCount
    gOnTime += totalOnTime
    if totalScreenOffProp == 0.0:
        gScreenOffProp[0][1] += 1
    for index in range(0, 10):
        if index*10.0 < totalScreenOffProp <= (index+1)*10.0:
            gScreenOffProp[index][1] += 1
    if totalAverageScreenOffTime != 0:
        for index in range(0, 10):
            if index*60*1000 < totalAverageScreenOffTime <= (index+1)*60*1000:
                gAverageSOFFT[index][1] += 1
                break
        else:
            gAverageSOFFT[10][1] += 1
    if totalAverageScreenOnTime != 0:
        for index in range(0, 10):
            if index*60*1000 < totalAverageScreenOnTime <= (index+1)*60*1000:
                gAverageSONT[index][1] += 1
                break
        else:
            gAverageSONT[10][1] += 1
    if totalAverageTime != 0:
        for index in range(0, 10):
            if index*60*1000 < totalAverageTime <= (index+1)*60*1000:
                gAverageT[index][1] += 1
                break
        else:
            gAverageT[10][1] += 1


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


def getStatistics(outputFileName):
    global gValidDevice, gValidCount, gDischargingCount, gDischargingTime, gScreenOffTime, gScreenOnTime, gScreenOffProp, gOffCount, gOffTime, gOnCount, gOnTime
    global gAverageSOFFT, gAverageSONT, gAverageT
    if gValidDevice < 1:
        return 1
    averageDischargingTime = gDischargingTime/gValidCount
    averageDischargingCount = gDischargingCount/gValidCount
    averageScreenOffTime = gScreenOffTime/gValidCount
    averageScreenOnTime = gScreenOnTime/gValidCount
    averageScreenOffProp = float(gScreenOffTime)*100.0/gDischargingTime
    for index in range(0, 10):
        gScreenOffProp[index][2] = float(gScreenOffProp[index][1])*100.0/gValidDevice
    if gOffCount >= 1:
        averageOffTimeIn100Count = gOffTime*100/gOffCount
    else:
        averageOffTimeIn100Count = 0
    if gOnCount >= 1:
        averageOnTimeIn100Count = gOnTime*100/gOnCount
    else:
        averageOnTimeIn100Count = 0
    (section, statisticsResult) = getStatisticsSection(averageDischargingTime, averageDischargingCount)
    sum1 = 0
    sum2 = 0
    sum3 = 0
    for index in range(0, 11):
        sum1 += gAverageSOFFT[index][1]
        sum2 += gAverageSONT[index][1]
        sum3 += gAverageT[index][1]
    for index in range(0, 11):
        if sum1 != 0:
            gAverageSOFFT[index][2] = gAverageSOFFT[index][1]*100.0 / float(sum1)
        if sum2 != 0:
            gAverageSONT[index][2] = gAverageSONT[index][1]*100.0 / float(sum2)
        if sum3 != 0:
            gAverageT[index][2] = gAverageT[index][1]*100.0 / float(sum3)
    if section < 255:
        outputStr = "Name: %s" % (outputFileName.split('/')[-1])
        outputStr += "\n有效设备 平均耗电量 平均放电时间 平均灭屏时间 平均亮屏时间 平均灭屏时间比例"
        outputStr += "\n   %d        %d       %s  %s  %s   %.2f%%" % (gValidDevice, averageDischargingCount, getTimeFromMs(averageDischargingTime), getTimeFromMs(averageScreenOffTime), getTimeFromMs(averageScreenOnTime), averageScreenOffProp)
        outputStr += "\n根据平均放电时间和平均耗电量换算成100%%电量计算使用时间: %s" % getTimeFromMs(statisticsResult)
        outputStr += "\n有效设备中灭屏时间占放电时间的比例分布区间:\n0-10% 10%-20% 20%-30% 30-40% 40%-50% 50-60% 60%-70% 70-80% 80%-90% 90-100%\n"
        for index in range(10):
            outputStr += " %d" % gScreenOffProp[index][1]
        outputStr += "\n"
        for index in range(10):
            outputStr += " %.2f%%" % gScreenOffProp[index][2]
        outputStr += "\nValidDevice: %d" % gValidDevice
        outputStr += "\nADC: %d" % averageDischargingCount
        outputStr += "\nADT: %s" % (getTimeFromMs(averageDischargingTime))
        outputStr += "\nCDC: %s" % (getTimeFromMs(statisticsResult))
        outputStr += "\nASO: %s" % (getTimeFromMs(averageScreenOffTime))
        outputStr += "\nASOP: %.2f%%" % averageScreenOffProp
        outputStr += "\nSOP"
        for index in range(9):
            outputStr += "\n%s    %d  %.2f%%" % (gScreenOffProp[index][0], gScreenOffProp[index][1], gScreenOffProp[index][2])
        outputStr += "\n%s  %d  %.2f%%" % (gScreenOffProp[9][0], gScreenOffProp[9][1], gScreenOffProp[9][2])
        outputStr += "\n有效灭屏时间 有效灭屏耗电 有效亮屏时间 有效亮屏耗电 100%电量在灭屏状态下可以使用的时间 100%电量在亮屏状态下可以使用的时间"
        outputStr += "\n%s %d %s %d %s %s" % (getTimeFromMs(gOffTime), gOffCount, getTimeFromMs(gOnTime), gOnCount, getTimeFromMs(averageOffTimeIn100Count), getTimeFromMs(averageOnTimeIn100Count))
        outputStr += "\n关屏状态下的下降一格电的平均时间分布"
        for index in range(0, 11):
            outputStr += "\n%s\t%d\t%.2f%%" % (gAverageSOFFT[index][0], gAverageSOFFT[index][1], gAverageSOFFT[index][2])
        outputStr += "\n开屏状态下的下降一格电的平均时间分布"
        for index in range(0, 11):
            outputStr += "\n%s\t%d\t%.2f%%" % (gAverageSONT[index][0], gAverageSONT[index][1], gAverageSONT[index][2])
        outputStr += "\n根据开屏和关屏换算后的下降一格电平均时间分布"
        for index in range(0, 11):
            outputStr += "\n%s\t%d\t%.2f%%" % (gAverageT[index][0], gAverageT[index][1], gAverageT[index][2])
        print outputStr
        fp = open(outputFileName, 'w')
        fp.write(outputStr)
        fp.close()


def handleFile(inputFileName, dischargingTimeLowLimit, dischargingTimeHighLimit):
    inputFile = inputFileName
    dischargingTimeLowCrit = dischargingTimeLowLimit
    dischargingTimeHighCrit = dischargingTimeHighLimit
    global totalDischargingTime, totalDischargingCount, totalScreenOffTime, totalScreenOnTime, totalScreenOffProp, totalValidCount, totalOffTime, totalOffCount, totalOnTime, totalOnCount
    global totalAverageScreenOffTime, totalAverageScreenOnTime, totalAverageTime
    totalDischargingTime = 0
    totalDischargingCount = 0
    totalScreenOffTime = 0
    totalScreenOnTime = 0
    totalScreenOffProp = 0.0
    totalValidCount = 0
    totalOffTime = 0
    totalOffCount = 0
    totalOnTime = 0
    totalOnCount = 0
    totalAverageScreenOffTime = 0
    totalAverageScreenOnTime = 0
    totalAverageTime = 0
    for line in fileinput.input(inputFile):
        if line.startswith(r"Total Discharging Time(ms)"):
            dischargingTime = int(line.split(":")[-1])
            if dischargingTimeLowCrit > dischargingTime: break
            continue
        if line.startswith(r"DischargeStatus: startTime"):
            line = line.replace(r"DischargeStatus: ", " ")
            line = line.strip()
            line = line.replace(",", "-")
            for spLine in line.split():
                spStr = spLine.split("-")
                dischargingTime = int(spStr[5])
                if (dischargingTimeLowCrit > dischargingTime) or (dischargingTimeHighCrit <= dischargingTime): continue
                dischargingCount = int(spStr[11])
                screenOffTime = int(spStr[13])
                screenOnTime = int(spStr[15])
                totalDischargingTime += dischargingTime
                totalDischargingCount += dischargingCount
                totalScreenOffTime += screenOffTime
                totalScreenOnTime += screenOnTime
                totalValidCount += 1
            continue
        if line.startswith(r"ScreenOffStatus: startTime"):
            line = line.replace(r"ScreenOffStatus: ", " ")
            line = line.strip()
            line = line.replace(",", "-")
            for spLine in line.split():
                spStr = spLine.split("-")
                offTime = int(spStr[5])
                offCount = int(spStr[11])
                totalOffTime += offTime
                totalOffCount += offCount
            continue
        if line.startswith(r"ScreenOnStatus: startTime"):
            line = line.replace(r"ScreenOnStatus: ", " ")
            line = line.strip()
            line = line.replace(",", "-")
            for spLine in line.split():
                spStr = spLine.split("-")
                onTime = int(spStr[5])
                onCount = int(spStr[11])
                totalOnTime += onTime
                totalOnCount += onCount
            continue
        if line.startswith(r"AverageScreenOffTime:"):
            totalAverageScreenOffTime = int(line.split(":")[-1])
            continue
        if line.startswith(r"AverageScreenOnTime:"):
            totalAverageScreenOnTime = int(line.split(":")[-1])
            continue
        if line.startswith(r"TotalAverageTime:"):
            totalAverageTime = int(line.split(":")[-1])
            continue

    fileinput.close()
    if totalValidCount >= 1:
        totalScreenOffProp = totalScreenOffTime*100.0/totalDischargingTime
        addToStatistics()


def getinfoSecondaryDirectory(directory, dischargingTimeLowLimit, dischargingTimeHighLimit, outputFileName):
    bugVersionPath = directory
    initStatistics()
    for bugReport in os.listdir(bugVersionPath):
        if not bugReport.startswith('bugreport') or not bugReport.endswith('power'): continue
        bugReportPath = bugVersionPath + "/" + bugReport
        if os.path.isfile(bugReportPath):
            handleFile(bugReportPath, dischargingTimeLowLimit, dischargingTimeHighLimit)
    getStatistics(outputFileName)

def getinfoPrimaryDirectory(directory, dischargingTimeLowLimit, dischargingTimeHighLimit, outputFileName):
    for bugVersion in os.listdir(directory):
        bugVersionPath = directory + "/" + bugVersion
        outputFile = "%s/%s_%s_%s_statistics.txt" % (directory, directory, bugVersion, outputFileName)
        if os.path.isdir(bugVersionPath):
            getinfoSecondaryDirectory(bugVersionPath, dischargingTimeLowLimit, dischargingTimeHighLimit, outputFile)


def parseArgv():
    parser = argparse.ArgumentParser()
    parser.add_argument("dischargingHourLowLimit", help = "过滤放电时间下限", type = int)
    parser.add_argument("dischargingHourHighLimit", help = "过滤放电时间上限", type = int)
    parser.add_argument("directoryLevel", help = "指定一级或者二级目录", type = int)
    parser.add_argument("directoryStr", help = "目录", type = str)
    args = parser.parse_args()
    print "We are sorting the discharging time which is longer than %dhour, %dms, shorter than %dhour, %dms" % (args.dischargingHourLowLimit, args.dischargingHourLowLimit*3600*1000, args.dischargingHourHighLimit, args.dischargingHourHighLimit*3600*1000)
    return (args.dischargingHourLowLimit, args.dischargingHourHighLimit, args.directoryLevel, args.directoryStr)


def main():
    reload(sys)
    sys.setdefaultencoding('utf-8')
    (dischargingHourLowLimit, dischargingHourHighLimit, directoryLevel, directoryStr) = parseArgv()
    (dischargingTimeLowLimit, dischargingTimeHighLimit) = (dischargingHourLowLimit*3600*1000, dischargingHourHighLimit*3600*1000)
    outputFileName = "%dh_%dh" % (dischargingHourLowLimit, dischargingHourHighLimit)
    if directoryLevel == 1:
        #getinfoPrimaryDirectory("MI_4LTE", dischargingTimeLowLimit, dischargingTimeHighLimit, outputFileName)
        #getinfoPrimaryDirectory("MI_4W", dischargingTimeLowLimit, dischargingTimeHighLimit, outputFileName)
        #getinfoPrimaryDirectory("MI_4C", dischargingTimeLowLimit, dischargingTimeHighLimit, outputFileName)
        #getinfoPrimaryDirectory("MI_3C", dischargingTimeLowLimit, dischargingTimeHighLimit, outputFileName)
        getinfoPrimaryDirectory(directoryStr, dischargingTimeLowLimit, dischargingTimeHighLimit, outputFileName)
    elif directoryLevel == 2:
        outputFileName = "%s/%s_%s_%s_statistics.txt" % (directoryStr, directoryStr.split('/')[-2], directoryStr.split('/')[-1], outputFileName)
        getinfoSecondaryDirectory(directoryStr, dischargingTimeLowLimit, dischargingTimeHighLimit, outputFileName)


def moduleMain(dischargingHourLowLimit, dischargingHourHighLimit, directoryLevel, directoryStr):
    reload(sys)
    sys.setdefaultencoding('utf-8')
    (dischargingTimeLowLimit, dischargingTimeHighLimit) = (dischargingHourLowLimit*3600*1000, dischargingHourHighLimit*3600*1000)
    outputFileName = "%dh_%dh" % (dischargingHourLowLimit, dischargingHourHighLimit)
    if directoryLevel == 1:
        #getinfoPrimaryDirectory("MI_4LTE", dischargingTimeLowLimit, dischargingTimeHighLimit, outputFileName)
        #getinfoPrimaryDirectory("MI_4W", dischargingTimeLowLimit, dischargingTimeHighLimit, outputFileName)
        #getinfoPrimaryDirectory("MI_4C", dischargingTimeLowLimit, dischargingTimeHighLimit, outputFileName)
        #getinfoPrimaryDirectory("MI_3C", dischargingTimeLowLimit, dischargingTimeHighLimit, outputFileName)
        getinfoPrimaryDirectory(directoryStr, dischargingTimeLowLimit, dischargingTimeHighLimit, outputFileName)
    elif directoryLevel == 2:
        outputFileName = "%s/%s_%s_%s_statistics.txt" % (directoryStr.split('/')[-2], directoryStr.split('/')[-2], directoryStr.split('/')[-1], outputFileName)
        getinfoSecondaryDirectory(directoryStr, dischargingTimeLowLimit, dischargingTimeHighLimit, outputFileName)


if __name__ == "__main__":
    main()
