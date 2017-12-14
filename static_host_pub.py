#!/usr/bin/env python

import json
import awsiot
import logging
import platform
import psutil
import datetime

NET_INTERFACES = ['en0', 'en1', 'en2', 'en3', 'wlan0', 'wlan1', 'eth0', 'eth1']


def get_ip(i):
    if i in psutil.net_if_addrs():
        try:
            for k in psutil.net_if_addrs()[i]:
                family, address, netmask, broadcast, ptp = k
                if family == 2:
                    return address
            return None
        except Exception as ex:
            logging.info("get_ip {} {}".format(i, ex.message))
            return None
    else:
        return None


if __name__ == "__main__":
    parser = awsiot.iot_pub_arg_parser()
    args = parser.parse_args()

    logging.basicConfig(filename=awsiot.LOG_FILE, level=args.log_level, format=awsiot.LOG_FORMAT)

    publisher = awsiot.Publisher(args.endpoint, args.rootCA, args.cert, args.key, args.thing, args.groupCA)

    properties = {}
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    properties["bootTime"] = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime(awsiot.DATE_FORMAT).strip()
    if platform.system() == 'Darwin':  # mac
        properties["release"] = platform.mac_ver()[0]
    elif platform.machine().startswith('arm') and platform.system() == 'Linux':  # raspberry pi
        properties["distribution"] = "{} {}".format(platform.dist()[0], platform.dist()[1])
    properties["hostname"] = platform.node()
    properties["machine"] = platform.machine()
    properties["system"] = platform.system()
    properties["totalDiskSpaceRoot"] = int(disk.total / (1024 * 1024))
    properties["cpuProcessorCount"] = psutil.cpu_count()
    properties["ramTotal"] = int(mem.total / (1024 * 1024))
    for iface in NET_INTERFACES:
        properties["{}IpAddress".format(iface)] = get_ip(iface)

    t = awsiot.THING_SHADOW.format(args.thing)
    payload = json.dumps({awsiot.STATE: {awsiot.REPORTED: properties}})
    result = publisher.publish(t, payload)
