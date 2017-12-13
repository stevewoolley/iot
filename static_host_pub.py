#!/usr/bin/env python

import argparse
import json
import awsiot
import logging
import platform
import psutil
import datetime

STATE = 'state'
REPORTED = 'reported'
DESIRED = 'desired'
THING_SHADOW = "$aws/things/{}/shadow/update"
DATE_FORMAT = '%Y/%m/%d %-I:%M %p %Z'
NET_INTERFACES = ['en0', 'en1', 'en2', 'en3', 'wlan0', 'wlan1', 'eth0', 'eth1']
LOG_FILE = '/var/log/iot.log'


def get_ip(i):
    if i in psutil.net_if_addrs():
        try:
            for k in psutil.net_if_addrs()[i]:
                family, address, netmask, broadcast, ptp = k
                if family == 2:
                    return address
            return None
        except Exception as ex:
            logging.info("iot_host_pub get_ip {} {}".format(i, ex.message))
            return None
    else:
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--endpoint", required=True, help="Your AWS IoT custom endpoint")
    parser.add_argument("-r", "--rootCA", required=True, help="Root CA file path")
    parser.add_argument("-c", "--cert", required=True, help="Certificate file path")
    parser.add_argument("-k", "--key", required=True, help="Private key file path")
    parser.add_argument("-n", "--thing", help="Targeted thing name")

    parser.add_argument("-g", "--groupCA", default=None, help="Group CA file path")
    parser.add_argument("-m", "--mqttHost", default=None, help="Targeted mqtt host")

    parser.add_argument("-t", "--topic", default="/test", help="Targeted topic")
    parser.add_argument("-l", "--log_level", help="Log Level", default=logging.INFO)
    args = parser.parse_args()

    logging.basicConfig(filename=LOG_FILE, level=args.log_level)

    publisher = awsiot.Publisher(args.endpoint, args.rootCA, args.cert, args.key, args.thing, args.groupCA)

    properties = {}
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    properties["bootTime"] = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime(DATE_FORMAT).strip()
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
    for i in NET_INTERFACES:
        properties["{}IpAddress".format(i)] = get_ip(i)

    topic = THING_SHADOW.format(args.thing)
    payload = json.dumps({STATE: {REPORTED: properties}})
    result = publisher.publish(topic, payload)
