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
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--endpoint", action="store", required=True, dest="host",
                        help="Your AWS IoT custom endpoint")
    parser.add_argument("-r", "--rootCA", action="store", required=True, dest="rootCAPath", help="Root CA file path")
    parser.add_argument("-g", "--groupCA", action="store", default='groupCA.crt', dest="groupCAPath",
                        help="Group CA file path")
    parser.add_argument("-c", "--cert", action="store", required=True, dest="certificatePath",
                        help="Certificate file path")
    parser.add_argument("-k", "--key", action="store", required=True, dest="privateKeyPath",
                        help="Private key file path")
    parser.add_argument("-n", "--thingName", action="store", dest="thingName",
                        help="Targeted thing name")
    parser.add_argument("-m", "--mqttHost", action="store", dest="mqttHost", default=None,
                        help="Targeted mqtt host")
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    args = parser.parse_args()

    publisher = awsiot.Publisher(args.host, args.thingName, args.privateKeyPath, args.certificatePath, args.rootCAPath,
                                 args.groupCAPath, args.mqttHost)
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
        publisher.log_level = logging.DEBUG

    properties = {}
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    properties["bootTime"] = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime(DATE_FORMAT)
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

    topic = THING_SHADOW.format(args.thingName)
    payload = json.dumps({STATE: {REPORTED: properties}})
    result = publisher.publish(topic, payload)
    publisher.close()
