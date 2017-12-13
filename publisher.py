#!/usr/bin/env python

import argparse
import json
import awsiot
import logging

LOG_FILE = '/var/log/iot.log'

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
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

    publisher = awsiot.Publisher(args.endpoint, args.rootCA, args.cert, args.key)

    logging.basicConfig(filename=LOG_FILE, level=args.log_level)

    message = {}
    message['foo'] = 'bar'
    messageJson = json.dumps(message)
    logging.info("Publish {} to {}".format(messageJson, args.topic))
    publisher.publish(args.topic, messageJson)

