#!/usr/bin/env bash
#Program:
#   This bash script is used to check the power-consumption of MIUI.
#Author: Qiu Zifeng

# check whether this line is valid or not
# return value is passed via "echo"
function isLineValid() {
    if [ $# -lt 3 ]; then
        echo "false"
        return 1
    fi
    local seg1=$1
    local seg2=$2
    local seg3=$3
    if [[ $(echo ${seg1} | grep '[0-9]ms$') == "" ]]; then
        echo "false"
        return 1
    elif [[ $(echo ${seg2} | grep '[0-9][0-9][0-9]') == "" ]]; then
        echo "false"
        return 1
    elif [[ $(echo ${seg3} | grep '[[:alnum:]\{7\}]') == "" ]]; then
        echo "false"
        return 1
    fi
    echo "true"
    return 0
}

function getTimeInt() {
    declare -i local dayInt=0
    declare -i local hourInt=0
    declare -i local minuteInt=0
    declare -i local secondInt=0
    declare -i local microsecondInt=0
    declare -i local timeInt=0
    case $# in
        1)
            timeInt=$1
            ;;
        2)
            microsecondInt=$2
            secondInt=$1
            let "timeInt=secondInt*1000+microsecondInt"
            ;;
        3)
            microsecondInt=$3
            secondInt=$2
            minuteInt=$1
            let "timeInt=minuteInt*60*1000+secondInt*1000+microsecondInt"
            ;;
        4)
            microsecondInt=$4
            secondInt=$3
            minuteInt=$2
            hourInt=$1
            let "timeInt=hourInt*60*60*1000+minuteInt*60*1000+secondInt*1000+microsecondInt"
            ;;
        5)
            microsecondInt=$5
            secondInt=$4
            minuteInt=$3
            hourInt=$2
            dayInt=$1
            let "timeInt=dayInt*24*60*60*1000+hourInt*60*60*1000+minuteInt*60*1000+secondInt*1000+microsecondInt"
            ;;
        *)
            timeInt=0
            ;;
    esac
    echo ${timeInt}
    return 0
}

# getTime function
# $1 is the "-1d01h07m36s313ms"
# return value is passed via "echo"
function getTime() {
    local timeStr=$1
    local timeInt=$(getTimeInt $(echo ${timeStr} | sed -e 's/^-//g' -e 's/d0*/ /g' -e 's/h0*/ /g' -e 's/m0*/ /g' -e 's/s0*/ /g'))
    echo ${timeInt}
}

# getBattery function
# $1 is the "086"
# return value is passed via "echo"
function getBattery() {
    declare -i local batteryInt=0
    local batteryStr=$1
    batteryStr=$(echo ${batteryStr} | sed 's/^0*//')
    batteryInt=${batteryStr}
    echo ${batteryInt}
}

# getTimeBattery function
# $1 is the "-1d01h07m36s313ms"
# $2 is the "086"
# return value is passed via "echo"
function getTimeBattery() {
    # local startTime=$(date +%s.%N)
    local timeStr=$1
    local timeInt=$(getTimeInt $(echo ${timeStr} | sed -e 's/^-//g' -e 's/d0\{0,1\}/ /g' -e 's/h0\{0,1\}/ /g' -e 's/m0\{0,1\}/ /g' -e 's/s0\{0,2\}/ /g'))
    local batteryStr=$2
    batteryStr=$(echo ${batteryStr} | sed 's/^0*//')
    batteryInt=${batteryStr}
    echo "${timeInt} ${batteryInt}"
    # local endTime=$(date +%s.%N)
    # ~6ms
    # echo "getTimeBattery: $(getElapseTime ${startTime} ${endTime})" >> ${timeFile}
}

# check whether this bugreport is valid and generate the new file for parsing if valid
# return value is passed via "return" value, but count not "echo" anything here since used by getTotalInfo()
function checkAndGenerateFile() {
    local inputFile=$1
    local outputFile=$2
    local bhLine=$(grep -a -n "^Battery History" ${inputFile})
    local ppLine=$(grep -a -n "^Per-PID" ${inputFile})
    if [ "${bhLine}" == "" ] || [ "${ppLine}" == "" ] ; then
        return 1
    fi
    local startLine=$(echo ${bhLine} | awk -F ":" '{print $1}')
    local endLine=$(echo ${ppLine} | awk -F ":" '{print $1}')
    sed -n "${startLine}"','"${endLine}"'p' ${inputFile} > "${outputFile}"
    return 0
}

# remove the file selected
function removeFile() {
    rm -f $1
}

# check init screen status
# return value is passed via "echo ON or OFF or INVALID"
function checkScreenStatus() {
    local inputFile=$1
    local tempStr=$(grep -n "+screen" ${inputFile} | awk -F ":" '{print $1}')
    if [ -z "${tempStr}" ]; then
        echo "INVALID"
        return 1
    fi
    declare -i local firstOnScreenLine=$(echo ${tempStr} | awk '{print $NF}')
    local tempStr=$(grep -n "-screen" ${inputFile} | awk -F ":" '{print $1}')
    if [ -z "${tempStr}" ]; then
        echo "INVALID"
        return 1
    fi
    declare -i local firstOffScreenLine=$(echo ${tempStr} | awk '{print $NF}')
    if [ ${firstOnScreenLine} -lt ${firstOffScreenLine} ]; then
        echo "true" # echo "ON", screen is on previously
        return 0
    elif [ ${firstOnScreenLine} -gt ${firstOffScreenLine} ]; then
        echo "false"    # echo "OFF", screen is off previously
        return 0
    else
        echo "INVALID"
        return 1
    fi
}

# get time info AND battery info
# return value is passed via echo "${dischargeTotalTimeInt} ${dischargeTotalBatteryInt} \t${dischargeStr} \t${chargeStr}"
function getTotalInfo() {
    local file=$1
    local tempFile="$2""__temp.txt"
    local lineValid=false
    local detectionPerPID=false
    local detectionBatteryHistory=false
    local inCharging=false
    local chargingStateChanging=false
    local currentTimeStr=""
    local currentBatteryStr=""
    local currentStr=""
    declare -i local dischargeTotalTimeInt=0    # 总的discharge的时间
    declare -i local dischargeTotalBatteryInt=0 # 总的discharge的电量
    declare -i local startTimeInt=0   # 每一段的开始时间
    declare -i local startBatteryInt=0    # 每一段的开始电量
    declare -i local currentTimeInt=0 # 当前时间
    declare -i local currentBatteryInt=0  # 当前电量
    declare -i local prevTimeInt=0    # 上一个event的时间
    declare -i local prevBatteryInt=0 # 上一个event的电量
    declare -i local contTimeInt=0    # 这一段的持续时间
    declare -i local contBatteryInt=0 # 这一次的下降电量
    declare -i local dischargeStartTimeInt=0    # 开始放电时刻的时间
    declare -i local dischargeStartBatteryInt=0 # 开始放电时刻的电量
    local dischargeStr="DischargeStatus:"
    declare -i local chargeStartTimeInt=0    # 开始充电时刻的时间
    declare -i local chargeStartBatteryInt=0 # 开始充电时刻的电量
    local chargeStr="ChargeStatus:"
    local screenIsON=false  # 屏幕状态
    declare -i local screenStateChangeTimeInt=0 # 屏幕状态改变时刻的时间
    declare -i local dischargeScreenONTimeInt=0 # 每一段discharge时总的screen ON时间
    declare -i local dischargeScreenOFFTimeInt=0    # 每一段discharge时总的screen OFF时间
    local startTime=""
    local endTime=""
    local sectionStartScreenIsON="INVALID"
    declare -i local sectionStartScreenTimeInt=0
    declare -i local sectionStartBatteryInt=0
    local sectionScreenOFFStr="ScreenOffStatus:"
    local sectionScreenONStr="ScreenOnStatus:"

    # check whether this bugreport is valid and generate the new file for parsing
    checkAndGenerateFile $file $tempFile
    local ret=$(echo $?)
    if [ "$ret" -ne 0 ]; then
        echo "0 0"
        removeFile ${tempFile}
        return 1
    fi
    screenIsON=$(checkScreenStatus ${tempFile})

    # Read and handle
    tac ${tempFile} | while read line
    do
        # Pre handle
        # startTime=$(date +%s.%N)
        # preLine=$(echo ${line} | awk '{if(NF > 2) {print "LV"}} /Per-PID/{print "PP"} /Battery History/{print "BH"} /status=charging/{print "SC"} /status=discharging/{print "SD"} /-screen/{print "SF"} /\+screen/{print "SN"}')
        preLine=$(echo ${line} | awk '/[0-9]ms [0-9][0-9][0-9]/{print "LV"} /Per-PID/{print "PP"} /Battery History/{print "BH"} /status=charging/{print "SC"} /status=discharging/{print "SD"} /-screen/{print "SF"} /\+screen/{print "SN"}')
        lineValid=false
        prePP=false
        preBH=false
        preSC=false
        preSD=false
        preSF=false
        preSN=false
        for preC in ${preLine}
        do
            case ${preC} in
                LV)
                    lineValid=true
                    ;;
                PP)
                    prePP=true
                    ;;
                BH)
                    preBH=true
                    ;;
                SC)
                    preSC=true
                    ;;
                SD)
                    preSD=true
                    ;;
                SF)
                    preSF=true
                    ;;
                SN)
                    preSN=true
                    ;;
            esac
        done
        # endTime=$(date +%s.%N)
        # echo "getTotalInfo: preHandle: $(getElapseTime ${startTime} ${endTime})" >> ${timeFile}
        # ~3ms
        # battery stats start
        # startTime=$(date +%s.%N)
        if [ "${detectionPerPID}" == "false" -a "${prePP}" == "true" ]; then
            detectionPerPID=true
            continue
        # battery stats end
        elif [ "${detectionBatteryHistory}" == "false" -a "${preBH}" == "true" ]; then
            detectionBatteryHistory=true
            echo "${dischargeTotalTimeInt} ${dischargeTotalBatteryInt} \t${dischargeStr} \t${chargeStr} \t${sectionScreenOFFStr} \t${sectionScreenONStr}"
            break
        fi
        if [ "${detectionPerPID}" != "true" ] || [ "${line}" == "" ]; then
            continue
        fi
    
        #lineValid=$(isLineValid ${line})
        #lineValid=$(echo ${line} | awk '{if(NF < 3) {print "false"} else {print "true"}}')
        if [ "${lineValid}" != "true" ]; then
            continue
        fi

        # Calculate Start
        if [ "${inCharging}" == "false" ] && [ "${preSC}" == "true" ]; then
            inCharging=true
            chargingStateChanging=true
        elif [ "${inCharging}" == "true" ] && [ "${preSD}" == "true" ]; then
            inCharging=false
            chargingStateChanging=true
        fi
        # endTime=$(date +%s.%N)
        # echo "getTotalInfo: preCheck: $(getElapseTime ${startTime} ${endTime})" >> ${timeFile}
        # ~1ms

        # startTime=$(date +%s.%N)
        #currentTimeInt=$(echo ${line} | awk '{print $1}' | sed -e 's/^-//g' -e 's/d0\{0,1\}/ /g' -e 's/h0\{0,1\}/ /g' -e 's/m0\{0,1\}/ /g' -e 's/s0\{0,2\}/ /g' | awk '{if(NF == 1) {print $1} else if(NF == 2) {print ($1 * 1000 + $2)} else if(NF ==3) {print ($1 * 60000 + $2 * 1000 + $3)} else if(NF == 4) {print ($1 * 3600000 + $2 * 60000 + $3 * 1000 + $4)} else if(NF == 5) {print ($1 * 24 * 3600000 + $2 * 3600000 + $3 * 60000 + $4 * 1000 + $5)} else {print "0"}}')
        currentTimeInt=$(getTimeInt $(echo ${line} | awk '{print $1}' | sed -e 's/^-//g' -e 's/d0\{0,1\}/ /g' -e 's/h0\{0,1\}/ /g' -e 's/m0\{0,1\}/ /g' -e 's/s0\{0,2\}/ /g'))
        currentBatteryInt=$(echo ${line} | awk '{print $2}' | sed 's/^0*//')
        # endTime=$(date +%s.%N)
        # echo "getTotalInfo: preCalculate: $(getElapseTime ${startTime} ${endTime})" >> ${timeFile}
        # ~7ms

        # Get the info first time, do some initialization
        # startTime=$(date +%s.%N)
        if [ ${startTimeInt} -eq 0 ]; then
            startTimeInt=${currentTimeInt}
            startBatteryInt=${currentBatteryInt}
            prevTimeInt=${currentTimeInt}
            prevBatteryInt=${currentBatteryInt}
            dischargeStartTimeInt=${currentTimeInt}
            dischargeStartBatteryInt=${currentBatteryInt}
            chargeStartTimeInt=${currentTimeInt}
            chargeStartBatteryInt=${currentBatteryInt}
            screenStateChangeTimeInt=${currentTimeInt}
            continue
        fi
        if [ ${prevBatteryInt} -eq ${currentBatteryInt} ]; then
            if [ "${chargingStateChanging}" == "true" ]; then   # charging status is changing
                if [ "${inCharging}" == "true" ]; then # From discharging to charging
                    contTimeInt=${currentTimeInt}-${startTimeInt}
                    dischargeTotalTimeInt=${dischargeTotalTimeInt}+${contTimeInt}
                    # screen status
                    if [ "${screenIsON}" != "INVALID" ]; then
                        if [ "${preSN}" == "true" ] || [ "${screenIsON}" == "false" ]; then # screen is ON from OFF or screen is OFF state
                            let "dischargeScreenOFFTimeInt+=currentTimeInt-screenStateChangeTimeInt"
                        elif [ "${preSF}" == "true" ] || [ "${screenIsON}" == "true" ]; then    # screen is OFF from ON or screen is ON state
                            let "dischargeScreenONTimeInt+=currentTimeInt-screenStateChangeTimeInt"
                        fi
                    fi
                    if [ ${dischargeStartTimeInt} -ne 0 ]; then
                        contTimeInt=${currentTimeInt}-${dischargeStartTimeInt}
                        contBatteryInt=${dischargeStartBatteryInt}-${currentBatteryInt}
                        dischargeStr="${dischargeStr} startTime-${dischargeStartTimeInt},endTime-${currentTimeInt},dischargeTime-${contTimeInt},startCount-${dischargeStartBatteryInt},endCount-${currentBatteryInt},dischargeCount-${contBatteryInt},screenOFFTime-${dischargeScreenOFFTimeInt},screenONTime-${dischargeScreenONTimeInt}"
                    fi
                    chargeStartTimeInt=${currentTimeInt}
                    chargeStartBatteryInt=${currentBatteryInt}
                    dischargeStartTimeInt=0
                    dischargeScreenOFFTimeInt=0
                    dischargeScreenONTimeInt=0
                else    # From charging to discharging
                    if [ ${chargeStartTimeInt} -ne 0 ]; then
                        contTimeInt=${currentTimeInt}-${chargeStartTimeInt}
                        contBatteryInt=${currentBatteryInt}-${chargeStartBatteryInt}
                        chargeStr="${chargeStr} startTime-${chargeStartTimeInt},endTime-${currentTimeInt},chargeTime-${contTimeInt},startCount-${chargeStartBatteryInt},endCount-${currentBatteryInt},chargeCount-${contBatteryInt}"
                    fi
                    dischargeStartTimeInt=${currentTimeInt}
                    dischargeStartBatteryInt=${currentBatteryInt}
                    chargeStartTimeInt=0
                    # screen status
                    if [ "${screenIsON}" != "INVALID" ]; then
                        screenStateChangeTimeInt=${currentTimeInt}
                        dischargeScreenOFFTimeInt=0
                        dischargeScreenONTimeInt=0
                    fi
                fi
                startTimeInt=${currentTimeInt}
                startBatteryInt=${currentBatteryInt}

                sectionStartScreenIsON="INVALID"
            else    # charging status stay non-changed
                # screen status
                if [ "${screenIsON}" != "INVALID" ] && [ "${inCharging}" == "false" ]; then
                    if [ "${preSN}" == "true" ]; then   # screen is ON from OFF
                        let "dischargeScreenOFFTimeInt+=currentTimeInt-screenStateChangeTimeInt"
                    elif [ "${preSF}" == "true" ]; then # screen is OFF from ON
                        let "dischargeScreenONTimeInt+=currentTimeInt-screenStateChangeTimeInt"
                    fi
                fi
            fi
        elif [ ${prevBatteryInt} -gt ${currentBatteryInt} ]; then # discharging
            if [ "${chargingStateChanging}" == "true" ]; then
                if [ "${inCharging}" == "false" ]; then # From charging to discharging
                    if [ ${chargeStartTimeInt} -ne 0 ]; then
                        contTimeInt=${prevTimeInt}-${chargeStartTimeInt}
                        contBatteryInt=${prevBatteryInt}-${chargeStartBatteryInt}
                        chargeStr="${chargeStr} startTime-${chargeStartTimeInt},endTime-${prevTimeInt},chargeTime-${contTimeInt},startCount-${chargeStartBatteryInt},endCount-${prevBatteryInt},chargeCount-${contBatteryInt}"
                    fi
                    dischargeStartTimeInt=${currentTimeInt}
                    dischargeStartBatteryInt=${currentBatteryInt}
                    chargeStartTimeInt=0
                    # screen status
                    if [ "${screenIsON}" != "INVALID" ]; then
                        screenStateChangeTimeInt=${currentTimeInt}
                        dischargeScreenOFFTimeInt=0
                        dischargeScreenONTimeInt=0
                    fi
                else    # From discharging to charging
                    # screen status
                    if [ "${screenIsON}" != "INVALID" ]; then
                        if [ "${preSN}" == "true" ] || [ "${screenIsON}" == "false" ]; then # screen is ON from OFF or screen is OFF state
                            let "dischargeScreenOFFTimeInt+=currentTimeInt-screenStateChangeTimeInt"
                        elif [ "${preSF}" == "true" ] || [ "${screenIsON}" == "true" ]; then    # screen is OFF from ON or screen is ON state
                            let "dischargeScreenONTimeInt+=currentTimeInt-screenStateChangeTimeInt"
                        fi
                    fi
                    if [ ${dischargeStartTimeInt} -ne 0 ]; then
                        contTimeInt=${currentTimeInt}-${dischargeStartTimeInt}
                        contBatteryInt=${dischargeStartBatteryInt}-${currentBatteryInt}
                        dischargeStr="${dischargeStr} startTime-${dischargeStartTimeInt},endTime-${currentTimeInt},dischargeTime-${contTimeInt},startCount-${dischargeStartBatteryInt},endCount-${currentBatteryInt},dischargeCount-${contBatteryInt},screenOFFTime-${dischargeScreenOFFTimeInt},screenONTime-${dischargeScreenONTimeInt}"
                    fi
                    chargeStartTimeInt=${currentTimeInt}
                    chargeStartBatteryInt=${currentBatteryInt}
                    dischargeStartTimeInt=0
                    dischargeScreenOFFTimeInt=0
                    dischargeScreenONTimeInt=0
                fi
            elif [ "${chargingStateChanging}" != "true" ] && [ "${inCharging}" == "true" ]; then
                inCharging=false
            fi
            if [ ${dischargeStartTimeInt} -eq 0 ]; then
                dischargeStartTimeInt=${startTimeInt}
                dischargeStartBatteryInt=${startBatteryInt}
            fi
            if [ ${chargeStartTimeInt} -ne 0 ]; then
                chargeStartTimeInt=0
            fi
            # screen status
            if [ "${screenIsON}" != "INVALID" ] && [ "${inCharging}" == "false" ]; then
                if [ "${preSN}" == "true" ]; then   # screen is ON from OFF
                    let "dischargeScreenOFFTimeInt+=currentTimeInt-screenStateChangeTimeInt"
                elif [ "${preSF}" == "true" ]; then # screen is OFF from ON
                    let "dischargeScreenONTimeInt+=currentTimeInt-screenStateChangeTimeInt"
                fi
            fi
            contTimeInt=${currentTimeInt}-${startTimeInt}
            dischargeTotalTimeInt=${dischargeTotalTimeInt}+${contTimeInt}
            contBatteryInt=${prevBatteryInt}-${currentBatteryInt}
            dischargeTotalBatteryInt=${dischargeTotalBatteryInt}+${contBatteryInt}
    
            startTimeInt=${currentTimeInt}
            startBatteryInt=${currentBatteryInt}

            if [ "${sectionStartScreenIsON}" != "INVALID" ]; then
                contTimeInt=${currentTimeInt}-${sectionStartScreenTimeInt}
                contBatteryInt=${sectionStartBatteryInt}-${currentBatteryInt}
                if [ "${sectionStartScreenIsON}" == "false" ]; then
                    sectionScreenOFFStr="${sectionScreenOFFStr} startTime-${sectionStartScreenTimeInt},endTime-${currentTimeInt},offTime-${contTimeInt},startCount-${sectionStartBatteryInt},endCount-${currentBatteryInt},offCount-${contBatteryInt}"
                else
                    sectionScreenONStr="${sectionScreenONStr} startTime-${sectionStartScreenTimeInt},endTime-${currentTimeInt},onTime-${contTimeInt},startCount-${sectionStartBatteryInt},endCount-${currentBatteryInt},onCount-${contBatteryInt}"
                fi
                sectionStartScreenTimeInt=${currentTimeInt}
                sectionStartBatteryInt=${currentBatteryInt}
            elif [ "${screenIsON}" != "INVALID" ]; then
                sectionStartScreenIsON=${screenIsON}
                sectionStartScreenTimeInt=${currentTimeInt}
                sectionStartBatteryInt=${currentBatteryInt}
            fi
        elif [ ${prevBatteryInt} -lt ${currentBatteryInt} ]; then # charging
            if [ "${chargingStateChanging}" == "true" ]; then
                if [ "${inCharging}" == "true" ]; then # From discharging to charging
                    contTimeInt=${prevTimeInt}-${startTimeInt}
                    dischargeTotalTimeInt=${dischargeTotalTimeInt}+${contTimeInt}
                    # screen status
                    if [ "${screenIsON}" != "INVALID" ]; then
                        if [ "${preSN}" == "true" ] || [ "${screenIsON}" == "false" ]; then # screen is ON from OFF or screen is OFF state
                            let "dischargeScreenOFFTimeInt+=currentTimeInt-screenStateChangeTimeInt"
                        elif [ "${preSF}" == "true" ] || [ "${screenIsON}" == "true" ]; then    # screen is OFF from ON or screen is ON state
                            let "dischargeScreenONTimeInt+=currentTimeInt-screenStateChangeTimeInt"
                        fi
                    fi
                    if [ ${dischargeStartTimeInt} -ne 0 ]; then
                        contTimeInt=${prevTimeInt}-${dischargeStartTimeInt}
                        contBatteryInt=${dischargeStartBatteryInt}-${prevBatteryInt}
                        dischargeStr="${dischargeStr} startTime-${dischargeStartTimeInt},endTime-${prevTimeInt},dischargeTime-${contTimeInt},startCount-${dischargeStartBatteryInt},endCount-${prevBatteryInt},dischargeCount-${contBatteryInt},screenOFFTime-${dischargeScreenOFFTimeInt},screenONTime-${dischargeScreenONTimeInt}"
                    fi
                    chargeStartTimeInt=${currentTimeInt}
                    chargeStartBatteryInt=${currentBatteryInt}
                    dischargeStartTimeInt=0
                    dischargeScreenOFFTimeInt=0
                    dischargeScreenONTimeInt=0
                else    # From charging to discharging
                    if [ ${chargeStartTimeInt} -ne 0 ]; then
                        contTimeInt=${currentTimeInt}-${chargeStartTimeInt}
                        contBatteryInt=${currentBatteryInt}-${chargeStartBatteryInt}
                        chargeStr="${chargeStr} startTime-${chargeStartTimeInt},endTime-${currentTimeInt},chargeTime-${contTimeInt},startCount-${chargeStartBatteryInt},endCount-${currentBatteryInt},chargeCount-${contBatteryInt}"
                    fi
                    dischargeStartTimeInt=${currentTimeInt}
                    dischargeStartBatteryInt=${currentBatteryInt}
                    chargeStartTimeInt=0
                    # screen status
                    if [ "${screenIsON}" != "INVALID" ]; then
                        screenStateChangeTimeInt=${currentTimeInt}
                        dischargeScreenOFFTimeInt=0
                        dischargeScreenONTimeInt=0
                    fi
                fi
            elif [ "${chargingStateChanging}" != "true" ] && [ "${inCharging}" == "false" ]; then
                inCharging=true
            fi
            if [ ${chargeStartTimeInt} -eq 0 ]; then
                chargeStartTimeInt=${startTimeInt}
                chargeStartBatteryInt=${startBatteryInt}
            fi
            if [ ${dischargeStartTimeInt} -ne 0 ]; then
                dischargeStartTimeInt=0
            fi
            # screen status
            screenStateChangeTimeInt=${currentTimeInt}
            dischargeScreenOFFTimeInt=0
            dischargeScreenONTimeInt=0

            startTimeInt=${currentTimeInt}
            startBatteryInt=${currentBatteryInt}

            sectionStartScreenIsON="INVALID"
        fi
        if [ "${chargingStateChanging}" == "true" ]; then
            chargingStateChanging=false
        fi
        # screen status change
        if [ "${screenIsON}" != "INVALID" ]; then
            if [ "${preSN}" == "true" ]; then # screen is ON from OFF
                screenIsON="true"
                screenStateChangeTimeInt=${currentTimeInt}

                sectionStartScreenIsON="INVALID"
            elif [ "${preSF}" == "true" ]; then # screen is OFF from ON
                screenIsON="false"
                screenStateChangeTimeInt=${currentTimeInt}

                sectionStartScreenIsON="INVALID"
            fi
        fi
        prevTimeInt=${currentTimeInt}
        prevBatteryInt=${currentBatteryInt}
        # endTime=$(date +%s.%N)
        # echo "getTotalInfo: calculate: $(getElapseTime ${startTime} ${endTime})" >> ${timeFile}
        # 1-2ms
    done
    removeFile ${tempFile}
    return 0
}

# get the section which this battery info is in
# return value is passed via "echo index result"
function getStatisticsSection() {
    # local startTime=$(date +%s.%N)
    declare -i local totalTimeInt=$1
    declare -i local totalBatteryInt=$2
    if [ ${totalTimeInt} -eq 0 ] || [ ${totalBatteryInt} -eq 0 ]; then
        echo "255 0"
        return 255 # invalid number
    fi
    declare -i local result=${totalTimeInt}*100/${totalBatteryInt}
    for ((index=0; index<=47; index++))
    do
        if [ ${result} -ge $[$index*60*60*1000] ] && [ ${result} -lt $[$[index+1]*60*60*1000] ]; then
            echo "${index} ${result}"
            return ${index}
        fi
    done
    echo "48 ${result}"
    # local endTime=$(date +%s.%N)
    # echo "getStatisticsSection: $(getElapseTime ${startTime} ${endTime})" >> ${timeFile}
    return 48 # means more than 2 days
}

# get the "day hour minute second ms" from "ms"
# return value is passed via "echo wholeTimeFormat"
function getTimeFromMs() {
    declare -i local msTime=$1
    declare -i local sTime=0
    declare -i local mTime=0
    declare -i local hTime=0
    declare -i local dTime=0
    let "sTime = msTime/1000"
    let "msTime = msTime%1000"
    if [ ${sTime} -lt 1 ]; then
        echo -ne "${msTime}ms"
        return 0
    fi
    let "mTime = sTime/60"
    let "sTime = sTime%60"
    if [ ${mTime} -lt 1 ]; then
        echo -ne "${sTime}s${msTime}ms"
        return 0
    fi
    let "hTime = mTime/60"
    let "mTime = mTime%60"
    if [ ${hTime} -lt 1 ]; then
        echo -ne "${mTime}m${sTime}s${msTime}ms"
        return 0
    fi
    let "dTime = hTime/24"
    let "hTime = hTime%24"
    if [ ${dTime} -lt 1 ]; then
        echo -ne "${hTime}h${mTime}m${sTime}s${msTime}ms"
        return 0
    fi
    echo -ne "${dTime}d${hTime}h${mTime}m${sTime}s${msTime}ms"
    return 0
}

# main function
LANG=C

if [ "$#" -ne 1 ]; then
    echo "Parameter is NONE!!!"
    exit 1
fi

fileName=$1
outputFileDetail=""

bugReport=$(echo $1 | awk -F '/' '{print $(NF)}')
bugVersion=$(echo $1 | awk -F '/' '{print $(NF-1)}')
bugDevice=$(echo $1 | awk -F '/' '{print $(NF-2)}')
dir="${bugDevice}/${bugVersion}"
outputFileDetail="${dir}/${bugReport}.power"
mkdir -p ${dir}

test -f ${outputFileDetail} && exit 0

# start to handle
declare -i totalTimeInt=0
declare -i totalBatteryInt=0
declare -i section=0
declare -i statisticsResult=0

if [ "${fileName}" != "" ]; then
    echo "handling ${fileName}"
    getTotalString=$(getTotalInfo ${fileName} ${outputFileDetail})
    totalTimeInt=$(echo ${getTotalString} | awk '{print $1}')
    totalBatteryInt=$(echo ${getTotalString} | awk '{print $2}')
    echo "totalTimeInt is ${totalTimeInt}"
    echo "totalBatteryInt is ${totalBatteryInt}"
    dischargingInfo=$(echo -e ${getTotalString} | awk -F "\t" '{print $2}')
    chargingInfo=$(echo -e ${getTotalString} | awk -F "\t" '{print $3}')
    screenOffInfo=$(echo -e ${getTotalString} | awk -F "\t" '{print $4}')
    screenOnInfo=$(echo -e ${getTotalString} | awk -F "\t" '{print $5}')
    getTotalString=$(getStatisticsSection ${getTotalString})
    section=$(echo ${getTotalString} | awk '{print $1}')
    statisticsResult=$(echo ${getTotalString} | awk '{print $2}')
    echo "the statisticsResult is ${statisticsResult}"
    echo "the section is ${section}"
    if [ ${section} -lt 255 ]; then
        echo -ne "Name: ${outputFileDetail}\n" > ${outputFileDetail}
        echo -ne "\nLogFileName: ${fileName}\nTotal Discharging Time: $(getTimeFromMs ${totalTimeInt})\n\
Total Discharging Battery Count(%): ${totalBatteryInt}\nConversion Result(In 100% Battery): $(getTimeFromMs ${statisticsResult})\n\
Total Discharging Time(ms): ${totalTimeInt}\nConversion Result(ms in 100% Battery): ${statisticsResult}\n${dischargingInfo}\n${chargingInfo}\n${screenOffInfo}\n${screenOnInfo}" >> ${outputFileDetail}
    fi
fi

exit 0
