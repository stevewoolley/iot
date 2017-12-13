#!/usr/bin/env python

import argparse
import json
import awsiot
import logging
import datetime
import sys
import time

LOG_FILE = '/var/log/iot.log'

def my_callback(client, user_data, message):
    msg = json.loads(message.payload)
    print("{} {} {}".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), message.topic, msg))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--endpoint", required=True, help="Your AWS IoT custom endpoint")
    parser.add_argument("-r", "--rootCA", required=True, help="Root CA file path")
    parser.add_argument("-c", "--cert", required=True, help="Certificate file path")
    parser.add_argument("-k", "--key", required=True, help="Private key file path")
    parser.add_argument("-n", "--thing", help="Targeted thing name")

    parser.add_argument("-g", "--groupCA", default=None, help="Group CA file path")
    parser.add_argument("-m", "--mqttHost", default=None, help="Targeted mqtt host")

    parser.add_argument("-t", "--topic", help="MQTT topic(s)", nargs='+', required=False)
    parser.add_argument("-l", "--log_level", help="Log Level", default=logging.INFO)
    args = parser.parse_args()

    logging.basicConfig(filename=LOG_FILE, level=args.log_level)

    subscriber = awsiot.Subscriber(args.endpoint, args.rootCA, args.cert, args.key)

    for t in args.topic:
        logging.info("Subscribing to {}".format(t))
        subscriber.subscribe(t, my_callback)
        time.sleep(2)  # pause

    # Loop forever
    try:
        while True:
            time.sleep(1)  # sleep needed because CPU race
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
