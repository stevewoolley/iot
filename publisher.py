#!/usr/bin/env python

import argparse
import json
import awsiot
import logging

STATE = 'state'
REPORTED = 'reported'
DESIRED = 'desired'
THING_SHADOW = "$aws/things/{}/shadow/update"

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
    parser.add_argument("-n", "--thingName", action="store", dest="thingName", default="Bot",
                        help="Targeted thing name")
    parser.add_argument("-t", "--topic", action="store", dest="topic", default="sdk/test/Python", help="Targeted topic")
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    args = parser.parse_args()

    publisher = awsiot.Publisher(args.host, args.thingName, args.privateKeyPath, args.certificatePath, args.rootCAPath,
                                 args.groupCAPath)
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
        publisher.log_level = logging.DEBUG

    properties = dict([('foo', 'bar')])
    topic = THING_SHADOW.format(args.topic)
    payload = json.dumps({STATE: {REPORTED: properties}})
    print("Publish {} to {}".format(payload, topic))
    result = publisher.publish(topic, payload)
    print("Published result: {}".format(result))
