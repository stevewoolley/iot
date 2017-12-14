#!/usr/bin/env python

import json
import awsiot
import logging
import platform
import psutil
import subprocess as sp


def os_execute(s):
    """Returns string result of os call"""
    try:
        result = sp.check_output(s.split()).rstrip('\n')
        return result
    except Exception as ex:
        return None


def get_rpi_cpu_temperature():
    """Returns raspberry pi cpu temperature in Centigrade"""
    temp = os_execute('/opt/vc/bin/vcgencmd measure_temp')
    return float(temp.split('=')[1].strip('\'C'))


if __name__ == "__main__":
    parser = awsiot.iot_arg_parser()
    args = parser.parse_args()

    logging.basicConfig(filename=awsiot.LOG_FILE, level=args.log_level, format=awsiot.LOG_FORMAT)

    publisher = awsiot.Publisher(args.endpoint, args.rootCA, args.cert, args.key, args.thing, args.groupCA)

    properties = {}
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    if platform.machine().startswith('arm') and platform.system() == 'Linux':  # raspberry pi
        properties["cpuTemp"] = get_rpi_cpu_temperature()
    properties["ramAvailable"] = int(mem.available / (1024 * 1024))
    properties["usedDiskSpaceRoot"] = int(disk.used / (1024 * 1024))
    properties["cpuLoad"] = psutil.cpu_percent(interval=3)

    t = awsiot.THING_SHADOW.format(args.thing)
    payload = json.dumps({awsiot.STATE: {awsiot.REPORTED: properties}})
    result = publisher.publish(t, payload)
