#!/usr/bin/env bash

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

# get the section which this battery info is in
# return value is passed via "echo index result"
function getStatisticsSection() {
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
    return 48 # means more than 2 days
}

function handleFile() {
    local file=$1
    declare -i local dischargingTimeLowCrit=$2
    declare -i local dischargingTimeHighCrit=$3
    local fileName=$(awk '/^Name:/{print $2}' ${file})
    declare -i local totalDischargingTime=$(awk -F ":" '/^Total Discharging Time\(ms\):/{print $2}' ${file})
    if [ ${totalDischargingTime} -lt ${dischargingTimeLowCrit} ] ; then
        echo "INVALID"
        return 1
    fi

    local line=$(awk -F ":" '/^DischargeStatus: startTime/{print $2}' ${file})
    totalDischargingTime=0
    declare -i local totalDischargingCount=0
    declare -i local totalScreenOffTime=0
    declare -i local totalScreenOffProp=0
    declare -i local totalValidCount=0
    declare -i local dischargingTime=0
    declare -i local dischargingCount=0
    declare -i local screenOffTime=0
    declare -i local offTime=0
    declare -i local offCount=0
    declare -i local onTime=0
    declare -i local onCount=0
    declare -i local totalOffTime=0
    declare -i local totalOffCount=0
    declare -i local totalOnTime=0
    declare -i local totalOnCount=0
    for str in ${line}
    do
        dischargingTime=$(echo ${str} | awk -F ",|-" '{print $6}')
        if [ ${dischargingTime} -lt ${dischargingTimeLowCrit} ] || [ ${dischargingTime} -ge ${dischargingTimeHighCrit} ] ; then
            continue
        fi
        dischargingCount=$(echo ${str} | awk -F ",|-" '{print $12}')
        screenOffTime=$(echo ${str} | awk -F ",|-" '{print $14}')
        let "totalDischargingTime+=dischargingTime"
        let "totalDischargingCount+=dischargingCount"
        let "totalScreenOffTime+=screenOffTime"
        let "totalValidCount+=1"
    done
    line=$(awk -F ":" '/^ScreenOffStatus: startTime/{print $2}' ${file})
    for str in ${line}
    do
        offTime=$(echo ${str} | awk -F ",|-" '{print $6}')
        offCount=$(echo ${str} | awk -F ",|-" '{print $12}')
        let "totalOffTime+=offTime"
        let "totalOffCount+=offCount"
    done
    line=$(awk -F ":" '/^ScreenOnStatus: startTime/{print $2}' ${file})
    for str in ${line}
    do
        onTime=$(echo ${str} | awk -F ",|-" '{print $6}')
        onCount=$(echo ${str} | awk -F ",|-" '{print $12}')
        let "totalOnTime+=onTime"
        let "totalOnCount+=onCount"
    done
    if [ ${totalValidCount} -lt 1 ]; then
        echo "INVALID"
        return 1
    else
        let "totalScreenOffProp=totalScreenOffTime*10000/totalDischargingTime"
        echo "${fileName} ${totalValidCount} ${totalDischargingCount} ${totalDischargingTime} ${totalScreenOffTime} ${totalScreenOffProp} ${totalOffCount} ${totalOffTime} ${totalOnCount} ${totalOnTime}"
        return 0
    fi
}

declare -i gValidDevice=0
declare -i gValidCount=0
declare -i gDischargingCount=0
declare -i gDischargingTime=0
declare -i gScreenOffTime=0
declare -i gScreenOffProp0010=0
declare -i gScreenOffProp1020=0
declare -i gScreenOffProp2030=0
declare -i gScreenOffProp3040=0
declare -i gScreenOffProp4050=0
declare -i gScreenOffProp5060=0
declare -i gScreenOffProp6070=0
declare -i gScreenOffProp7080=0
declare -i gScreenOffProp8090=0
declare -i gScreenOffProp9000=0
declare -i gOffCount=0
declare -i gOffTime=0
declare -i gOnCount=0
declare -i gOnTime=0
function addToStatistics() {
    echo $*
    let "gValidDevice+=1"
    let "gValidCount+=$2"
    let "gDischargingCount+=$3"
    let "gDischargingTime+=$4"
    let "gScreenOffTime+=$5"
    let "gOffCount+=$7"
    let "gOffTime+=$8"
    let "gOnCount+=$9"
    let "gOnTime+=${10}"
    if [ $6 -lt 1000 ]; then
        let "gScreenOffProp0010+=1"
    elif [ $6 -lt 2000 ]; then
        let "gScreenOffProp1020+=1"
    elif [ $6 -lt 3000 ]; then
        let "gScreenOffProp2030+=1"
    elif [ $6 -lt 4000 ]; then
        let "gScreenOffProp3040+=1"
    elif [ $6 -lt 5000 ]; then
        let "gScreenOffProp4050+=1"
    elif [ $6 -lt 6000 ]; then
        let "gScreenOffProp5060+=1"
    elif [ $6 -lt 7000 ]; then
        let "gScreenOffProp6070+=1"
    elif [ $6 -lt 8000 ]; then
        let "gScreenOffProp7080+=1"
    elif [ $6 -lt 9000 ]; then
        let "gScreenOffProp8090+=1"
    else
        let "gScreenOffProp9000+=1"
    fi
    return 0
}

function getStatistics() {
    if [ ${gValidDevice} -lt 1 ]; then
        echo "INVALID"
        return 1
    fi
    let "averageDischargingTime=gDischargingTime/gValidCount"
    let "averageDischargingCount=gDischargingCount/gValidCount"
    let "averageScreenOffTime=gScreenOffTime/gValidCount"
    let "averageScreenOffProp=gScreenOffTime*10000/gDischargingTime"
    let "averageScreenOffProp0010=gScreenOffProp0010*10000/gValidDevice"
    let "averageScreenOffProp1020=gScreenOffProp1020*10000/gValidDevice"
    let "averageScreenOffProp2030=gScreenOffProp2030*10000/gValidDevice"
    let "averageScreenOffProp3040=gScreenOffProp3040*10000/gValidDevice"
    let "averageScreenOffProp4050=gScreenOffProp4050*10000/gValidDevice"
    let "averageScreenOffProp5060=gScreenOffProp5060*10000/gValidDevice"
    let "averageScreenOffProp6070=gScreenOffProp6070*10000/gValidDevice"
    let "averageScreenOffProp7080=gScreenOffProp7080*10000/gValidDevice"
    let "averageScreenOffProp8090=gScreenOffProp8090*10000/gValidDevice"
    let "averageScreenOffProp9000=gScreenOffProp9000*10000/gValidDevice"
    if [ ${gOffCount} -ge 1 ]; then
        let "averageOffTimeIn100Count=gOffTime*100/gOffCount"
    else
        let "averageOffTimeIn100Count=0"
    fi
    if [ ${gOnCount} -ge 1 ]; then
        let "averageOnTimeIn100Count=gOnTime*100/gOnCount"
    else
        let "averageOnTimeIn100Count=0"
    fi
    str=$(getStatisticsSection ${averageDischargingTime} ${averageDischargingCount})
    section=$(echo ${str} | awk '{print $1}')
    statisticsResult=$(echo ${str} | awk '{print $2}')
    if [ ${section} -lt 255 ]; then
        echo "有效设备 平均耗电量 平均放电时间 平均灭屏时间 平均灭屏时间比列\
有效灭屏时间 有效灭屏耗电 有效亮屏时间 有效开屏耗电 100%电量在灭屏状态下可以使用的时间 100%电量在亮屏状态下可以使用的时间\n\
\t\t${gValidDevice} ${averageDischargingCount} $(getTimeFromMs ${averageDischargingTime}) $(getTimeFromMs ${averageScreenOffTime}) ${averageScreenOffProp}/10000 $(getTimeFromMs ${gOffTime}) ${gOffCount} $(getTimeFromMs ${gOnTime}) ${gOnCount} $(getTimeFromMs ${averageOffTimeIn100Count}) $(getTimeFromMs ${averageOnTimeIn100Count})\n\
换算成100%电量计算\n\
$(getTimeFromMs ${statisticsResult})\n\
灭屏时间比例区间 0-10% 10%-20% 20%-30% 30-40% 40%-50% 50-60% 60%-70% 70-80% 80%-90% 90-100%\n\
\t\t${gScreenOffProp0010} ${gScreenOffProp1020} ${gScreenOffProp2030} ${gScreenOffProp3040} ${gScreenOffProp4050} ${gScreenOffProp5060} ${gScreenOffProp6070} ${gScreenOffProp7080} ${gScreenOffProp8090} ${gScreenOffProp9000}\n\
\t\t${averageScreenOffProp0010} ${averageScreenOffProp1020} ${averageScreenOffProp2030} ${averageScreenOffProp3040} ${averageScreenOffProp4050} ${averageScreenOffProp5060} ${averageScreenOffProp6070} ${averageScreenOffProp7080} ${averageScreenOffProp8090} ${averageScreenOffProp9000}\n\
ADC: ${averageDischargingCount}\n\
ADT: $(getTimeFromMs ${averageDischargingTime})\n\
CDC: $(getTimeFromMs ${statisticsResult})\n\
ASO: $(getTimeFromMs ${averageScreenOffTime})\n\
ASOP: ${averageScreenOffProp}%\n\
  SOP\n\
0-10%    ${gScreenOffProp0010}    ${averageScreenOffProp0010}%\n\
10%-20%  ${gScreenOffProp1020}    ${averageScreenOffProp1020}%\n\
20%-30%  ${gScreenOffProp2030}    ${averageScreenOffProp2030}%\n\
30%-40%  ${gScreenOffProp3040}    ${averageScreenOffProp3040}%\n\
40%-50%  ${gScreenOffProp4050}    ${averageScreenOffProp4050}%\n\
50%-60%  ${gScreenOffProp5060}    ${averageScreenOffProp5060}%\n\
60%-70%  ${gScreenOffProp6070}    ${averageScreenOffProp6070}%\n\
70%-80%  ${gScreenOffProp7080}    ${averageScreenOffProp7080}%\n\
80%-90%  ${gScreenOffProp8090}    ${averageScreenOffProp8090}%\n\
90%-100% ${gScreenOffProp9000}    ${averageScreenOffProp9000}%\n\
"
    else
        echo "INVALID"
        return 1
    fi
    return 0
}

function clearStatistics() {
    gValidDevice=0
    gValidCount=0
    gDischargingCount=0
    gDischargingTime=0
    gScreenOffTime=0
    gScreenOffProp0010=0
    gScreenOffProp1020=0
    gScreenOffProp2030=0
    gScreenOffProp3040=0
    gScreenOffProp4050=0
    gScreenOffProp5060=0
    gScreenOffProp6070=0
    gScreenOffProp7080=0
    gScreenOffProp8090=0
    gScreenOffProp9000=0
    gOffCount=0
    gOffTime=0
    gOnCount=0
    gOnTime=0
}

# main function
LANG=C

if [ $# -ne 2 ]; then
    echo "Invalid Usage"
    exit 1
fi

dischargingHourLowLimit=$1
dischargingHourHighLimit=$2
let "dischargingTimeLowCrit=dischargingHourLowLimit*3600*1000"
let "dischargingTimeHighCrit=dischargingHourHighLimit*3600*1000"
echo "We are sorting the discharging time which is longer than ${dischargingHourLowLimit}hour, ${dischargingTimeLowCrit}ms, shorter than ${dischargingHourHighLimit}hour, ${dischargingTimeHighCrit}ms"

deviceName="MI_4LTE"
cd ${deviceName}
for dir in $(ls)
do
    if [ -d ${dir} ]; then
        cd ${dir}
        outputFile="${deviceName}_${dir}_${dischargingHourLowLimit}h_${dischargingHourHighLimit}h_statistics.txt"
        for file in $(ls)
        do
            # echo ${file}
            if [ -f ${file} ]; then
                ret=$(handleFile ${file} ${dischargingTimeLowCrit} ${dischargingTimeHighCrit})
                if [ "${ret}" == "INVALID" ]; then
                    continue
                fi
                addToStatistics ${ret}
            fi
        done
        ret=$(getStatistics)
        if [ "${ret}" != "INVALID" ]; then
            # echo -ne "Name: ${outputFile}\n" > ${outputFile}
            echo -ne "Name: ${outputFile}\n" | tee "../${outputFile}"
            echo -ne ${ret} | tee -a "../${outputFile}"
        fi
        clearStatistics
        cd ..
    fi
done
cd ..

deviceName="MI_4C"
cd ${deviceName}
for dir in $(ls)
do
    if [ -d ${dir} ]; then
        cd ${dir}
        outputFile="${deviceName}_${dir}_${dischargingHourLowLimit}h_${dischargingHourHighLimit}h_statistics.txt"
        for file in $(ls)
        do
            # echo ${file}
            if [ -f ${file} ]; then
                ret=$(handleFile ${file} ${dischargingTimeLowCrit} ${dischargingTimeHighCrit})
                if [ "${ret}" == "INVALID" ]; then
                    continue
                fi
                addToStatistics ${ret}
            fi
        done
        ret=$(getStatistics)
        if [ "${ret}" != "INVALID" ]; then
            # echo -ne "Name: ${outputFile}\n" > ${outputFile}
            echo -ne "Name: ${outputFile}\n" | tee "../${outputFile}"
            echo -ne ${ret} | tee -a "../${outputFile}"
        fi
        clearStatistics
        cd ..
    fi
done
cd ..

deviceName="MI_4W"
cd ${deviceName}
for dir in $(ls)
do
    if [ -d ${dir} ]; then
        cd ${dir}
        outputFile="${deviceName}_${dir}_${dischargingHourLowLimit}h_${dischargingHourHighLimit}h_statistics.txt"
        for file in $(ls)
        do
            # echo ${file}
            if [ -f ${file} ]; then
                ret=$(handleFile ${file} ${dischargingTimeLowCrit} ${dischargingTimeHighCrit})
                if [ "${ret}" == "INVALID" ]; then
                    continue
                fi
                addToStatistics ${ret}
            fi
        done
        ret=$(getStatistics)
        if [ "${ret}" != "INVALID" ]; then
            # echo -ne "Name: ${outputFile}\n" > ${outputFile}
            echo -ne "Name: ${outputFile}\n" | tee "../${outputFile}"
            echo -ne ${ret} | tee -a "../${outputFile}"
        fi
        clearStatistics
        cd ..
    fi
done
cd ..

#deviceName="MI_3"
#cd ${deviceName}
#for dir in $(ls)
#do
#    if [ -d ${dir} ]; then
#        cd ${dir}
#        outputFile="${deviceName}_${dir}_${dischargingHourLowLimit}h_${dischargingHourHighLimit}h_statistics.txt"
#        for file in $(ls)
#        do
#            # echo ${file}
#            if [ -f ${file} ]; then
#                ret=$(handleFile ${file} ${dischargingTimeLowCrit} ${dischargingTimeHighCrit})
#                if [ "${ret}" == "INVALID" ]; then
#                    continue
#                fi
#                addToStatistics ${ret}
#            fi
#        done
#        ret=$(getStatistics)
#        if [ "${ret}" != "INVALID" ]; then
#            # echo -ne "Name: ${outputFile}\n" > ${outputFile}
#            echo -ne "Name: ${outputFile}\n" | tee "../${outputFile}"
#            echo -ne ${ret} | tee -a "../${outputFile}"
#        fi
#        clearStatistics
#        cd ..
#    fi
#done
#cd ..

#deviceName="MI_3C_3W"
#for dir in $(ls "MI_3C")
#do
#    if [ -d "MI_3C/${dir}" ] && [ -d "MI_3W/${dir}" ]; then
#        outputFile="${deviceName}_${dir}_${dischargingHourLowLimit}h_${dischargingHourHighLimit}h_statistics.txt"
#        for file in $(ls "MI_3C/${dir}")
#        do
#            # echo ${file}
#            if [ -f "MI_3C/${dir}/${file}" ]; then
#                ret=$(handleFile "MI_3C/${dir}/${file}" ${dischargingTimeLowCrit} ${dischargingTimeHighCrit})
#                if [ "${ret}" == "INVALID" ]; then
#                    continue
#                fi
#                addToStatistics ${ret}
#            fi
#        done
#        for file in $(ls "MI_3W/${dir}")
#        do
#            # echo ${file}
#            if [ -f "MI_3W/${dir}/${file}" ]; then
#                ret=$(handleFile "MI_3W/${dir}/${file}" ${dischargingTimeLowCrit} ${dischargingTimeHighCrit})
#                if [ "${ret}" == "INVALID" ]; then
#                    continue
#                fi
#                addToStatistics ${ret}
#            fi
#        done
#        ret=$(getStatistics)
#        if [ "${ret}" != "INVALID" ]; then
#            # echo -ne "Name: ${outputFile}\n" > ${outputFile}
#            echo -ne "Name: ${outputFile}\n" | tee "../${outputFile}"
#            echo -ne ${ret} | tee -a "../${outputFile}"
#        fi
#        clearStatistics
#    fi
#done

#deviceName="MI_3C"
#cd ${deviceName}
#for dir in $(ls)
#do
#    if [ -d ${dir} ]; then
#        cd ${dir}
#        outputFile="${deviceName}_${dir}_${dischargingHourLowLimit}h_${dischargingHourHighLimit}h_statistics.txt"
#        for file in $(ls)
#        do
#            # echo ${file}
#            if [ -f ${file} ]; then
#                ret=$(handleFile ${file} ${dischargingTimeLowCrit} ${dischargingTimeHighCrit})
#                if [ "${ret}" == "INVALID" ]; then
#                    continue
#                fi
#                addToStatistics ${ret}
#            fi
#        done
#        ret=$(getStatistics)
#        if [ "${ret}" != "INVALID" ]; then
#            # echo -ne "Name: ${outputFile}\n" > ${outputFile}
#            echo -ne "Name: ${outputFile}\n" | tee "../${outputFile}"
#            echo -ne ${ret} | tee -a "../${outputFile}"
#        fi
#        clearStatistics
#        cd ..
#    fi
#done
#cd ..
#
#deviceName="MI_3W"
#cd ${deviceName}
#for dir in $(ls)
#do
#    if [ -d ${dir} ]; then
#        cd ${dir}
#        outputFile="${deviceName}_${dir}_${dischargingHourLowLimit}h_${dischargingHourHighLimit}h_statistics.txt"
#        for file in $(ls)
#        do
#            # echo ${file}
#            if [ -f ${file} ]; then
#                ret=$(handleFile ${file} ${dischargingTimeLowCrit} ${dischargingTimeHighCrit})
#                if [ "${ret}" == "INVALID" ]; then
#                    continue
#                fi
#                addToStatistics ${ret}
#            fi
#        done
#        ret=$(getStatistics)
#        if [ "${ret}" != "INVALID" ]; then
#            # echo -ne "Name: ${outputFile}\n" > ${outputFile}
#            echo -ne "Name: ${outputFile}\n" | tee "../${outputFile}"
#            echo -ne ${ret} | tee -a "../${outputFile}"
#        fi
#        clearStatistics
#        cd ..
#    fi
#done
#cd ..
