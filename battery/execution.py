#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import collections
import datetime
import fileinput
import getopt
import re
import StringIO
import subprocess
import sys
import errno
import os.path
import argparse
import power_consumption_hubber
import power_consumption_sort
from jinja2 import Template

LOW_LIMIT_LIST = ["0h", "1h", "2h", "4h", "6h", "8h"]
LOW_LIMIT_DICT = {"0h": "2h", "1h": "2h", "2h": "4h", "4h": "6h", "6h": "8h", "8h": "48h"}
MI3_VERSION_LIST = ["4.11.7", "4.11.14", "V6.1.2.0.KXCCNBJ", "KXCCNBH31.0"]
MI3W_VERSION_LIST = ["4.11.7", "4.11.14", "V6.1.2.0.KXDCNBJ", "KXDCNBH34.0"]
MI3C_VERSION_LIST = ["4.11.7", "4.11.14", "V6.1.2.0.KXDCNBJ"]
MI4LTE_VERSION_LIST = ["4.11.7", "4.11.14", "V6.1.2.0.KXDCNBJ"]
MI4W_VERSION_LIST = ["4.11.7", "4.11.14", "V6.1.2.0.KXDCNBJ"]
MI4C_VERSION_LIST = ["4.11.7", "4.11.14", "V6.1.2.0.KXDCNBJ"]
KLO_HTML = "klo_report.html"
VERSION_LIST = []
TABLE_NAME = ""

def getDict(directory):
    lowLimitDict = LOW_LIMIT_DICT
    devInfo = {}
    for index in lowLimitDict.keys():
        devInfo[index] = {}
    for statisticsResult in os.listdir(directory):
        if not statisticsResult.startswith(directory) or not statisticsResult.endswith("statistics.txt"): continue
        statisticsResultPath = directory + "/" + statisticsResult
        if os.path.isfile(statisticsResultPath):
            (validDevice, version, lowLimit, highLimit, refList) = ("", "", "", "", [])
            fp = open(statisticsResultPath)
            refStart = False
            for line in fp:
                if line.startswith(r"Name:"):
                    spList = line.split("_")
                    version = spList[1]
                    lowLimit = spList[2]
                    highLimit = spList[3]
                elif line.startswith(r"ValidDevice:"):
                    validDevice = line.split()[-1]
                elif line.startswith(r"ADC:"):
                    adc = line.split()[-1]
                elif line.startswith(r"ADT:"):
                    adt = line.split()[-1]
                elif line.startswith(r"CDC:"):
                    cdc = line.split()[-1]
                elif line.startswith(r"ASO:"):
                    aso = line.split()[-1]
                elif line.startswith(r"ASOP:"):
                    asop = line.split()[-1]
                elif line.startswith(r"SOP"):
                    refStart = True
                elif line.startswith(r"90%-100%"):
                    refList.append(line)
                    refStart = False
                    break
                elif refStart:
                    refList.append(line)
            fp.close()
            devInfo[lowLimit].update({version: (validDevice, version, lowLimit, highLimit, adc, adt, cdc, aso, asop, refList)})
    return devInfo


def generateHtml(directory):
    global VERSION_LIST, TABLE_NAME
    devDict = getDict(directory)
    tmpl = Template(u'''\
    <p>CDT: Continuous Discharging TIme, 连续放电时间</p>
    <p>ADC: Average Discharging Count, 平均放电量</p>
    <p>ADT: Average Discharging Time, 平均放电时间</p>
    <p>CDC: Calculation the discharging time after Conversion to 100% battery, 换算成100%电量计算放电时间</p>
    <p>ASO: Average Screen Off Time, 平均灭屏时间</p>
    <p>ASOP: Average Screen Off Proportion, 平均灭屏时间占平均放电时间的比例</p>
    <p>SOP: Screen Off Proportion, 每个设备灭屏时间占放电时间的比例</p>
    <h2>{{ tableName }}</h2>
    <div class="table-wrap">
        <table class="confluenceTable">
            <tbody>
                <tr>
                    <td style="text-align: center;" class="confluenceTd"><strong>版本</strong></td>
                    {% for version in versionList %}
                    <td style="text-align: center;" class="confluenceTd"><strong>{{ version }}</strong></td>
                    {% endfor %}
                </tr>
                {% for lowLimit in lowLimitList %}
                <tr>
                    <td style="text-align: center;" class="confluenceTd"><strong>有效设备({{ lowLimit }}=&lt;CDT&lt;{{ lowLimitDict[lowLimit] }})</strong></td>
                    {% for version in versionList %}
                    {% if version in devInfo[lowLimit] %}
                    <td style="text-align: center;" class="confluenceTd">{{ devInfo[lowLimit][version][0] }}</td>
                    {% else %}
                    <td style="text-align: center;" class="confluenceTd"></td>
                    {% endif %}
                    {% endfor %}
                </tr>
                <tr>
                    <td style="text-align: center;" class="confluenceTd"><p><strong><br /></strong></p><p><strong><br /></strong></p><p><strong><br /></strong></p><p><strong><br /></strong></p><p><strong><br /></strong></p><p><strong><br /></strong></p><p><strong><br /></strong></p><p><strong>参考指标</strong></p></td>
                    {% for version in versionList %}
                    {% if version in devInfo[lowLimit] %}
                    <td style="text-align: center;" class="confluenceTd">
                        <p>ADC: {{devInfo[lowLimit][version][4]}}</p>
                        <p>ADT: {{devInfo[lowLimit][version][5]}}</p>
                        <p>CDC: {{devInfo[lowLimit][version][6]}}</p>
                        <p>ASO: {{devInfo[lowLimit][version][7]}}</p>
                        <p>ASOP: {{devInfo[lowLimit][version][8]}}</p>
                        <p style="text-align: left;">   SOP</p>
                        {% for line in devInfo[lowLimit][version][9] %}
                        <p style="text-align: left;">{{ line }}</p>
                        {% endfor %}
                    </td>
                    {% else %}
                    <td style="text-align: left;" class="confluenceTd"></td>
                    {% endif %}
                    {% endfor %}
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    ''')

    htmlContent = tmpl.render(
        tableName = (TABLE_NAME).decode('utf-8'),
        versionList = VERSION_LIST,
        lowLimitDict = LOW_LIMIT_DICT,
        lowLimitList = LOW_LIMIT_LIST,
        devInfo = devDict,
    )
    f = open(KLO_HTML, 'w')
    f.write(htmlContent)
    f.close()

def uploadHtml(dest):
    username = "qiuzifeng"
    passwd = "123QWEasdZXC"
    try:
        upload_html_command = './klopublish.py ' + '\"'+ username + '\" ' + '\"'+ passwd + '\" ' + KLO_HTML + ' ' + dest
        upload_html_process = subprocess.Popen(upload_html_command, shell=True, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, close_fds=True)
        upload_html_out, upload_html_err = upload_html_process.communicate()

        print 'upload html successfully'
    except Exception as e:
        print e

    finally:
        print 'upload html done!'

def executionSecondaryDirectory(directory):
    bugVersionPath = directory
    for bugReport in os.listdir(bugVersionPath):
        if not bugReport.startswith('bugreport'): continue
        bugReportPath = bugVersionPath + "/" + bugReport
        if os.path.isfile(bugReportPath):
            power_consumption_hubber.moduleMain(bugReportPath)
            #osCommand = "/home/qiuzifeng/script/power_consumption_hubber.py " + bugReportPath
            #os.system(osCommand)


def executionPrimaryDirectory(directory):
    for bugVersion in os.listdir(directory):
        bugVersionPath = directory + "/" + bugVersion
        if os.path.isdir(bugVersionPath):
            executionSecondaryDirectory(bugVersionPath)


def main():
    global VERSION_LIST, TABLE_NAME
    reload(sys)
    sys.setdefaultencoding('utf-8')
    #executionPrimaryDirectory("/home/ritter/klo-tools/MI_3")
    #executionSecondaryDirectory("/home/work/builder/brm/data/bugreport/MI 3/KXCCNBH31.0")
    VERSION_LIST = MI3W_VERSION_LIST
    TABLE_NAME = "MI 3W V6开发版Battery Stats反馈数据(From BugReport)"
    directory = "MI3W"
    dest = "MI3W_V6_BatteryStatsReport"
    power_consumption_sort.moduleMain(0, 2, 1,  directory)
    power_consumption_sort.moduleMain(1, 2, 1,  directory)
    power_consumption_sort.moduleMain(2, 4, 1,  directory)
    power_consumption_sort.moduleMain(4, 6, 1,  directory)
    power_consumption_sort.moduleMain(6, 8, 1,  directory)
    power_consumption_sort.moduleMain(8, 48, 1, directory)
    generateHtml(directory)
    uploadHtml(dest)

if __name__ == "__main__":
    main()
