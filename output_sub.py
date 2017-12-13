#!/usr/bin/env python

import argparse
import json
import awsiot
import logging
import datetime
import sys
import time
from gpiozero import DigitalOutputDevice

LOG_FILE = '/var/log/iot.log'


def my_callback(client, user_data, message):
    msg = json.loads(message.payload)
    logging.info(
        "output_sub {} {} {}".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), message.topic, msg))
    if message.topic == args.topic:
        if args.default == 0:
            output.off()
        elif args.default < 0:
            output.on()
        else:
            output.blink(args.on_time, args.off_time, args.default)
    if message.topic.replace(args.topic,'') in ['/1','/on']:
        output.on()
    elif message.topic.replace(args.topic,'') in ['/0','/off']:
        output.off()
    elif message.topic.replace(args.topic,'') in ['/blink','/pulse']:
        output.blink(args.on_time, args.off_time, args.default)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--endpoint", required=True, help="Your AWS IoT custom endpoint")
    parser.add_argument("-r", "--rootCA", required=True, help="Root CA file path")
    parser.add_argument("-c", "--cert", required=True, help="Certificate file path")
    parser.add_argument("-k", "--key", required=True, help="Private key file path")
    parser.add_argument("-n", "--thing", help="Targeted thing name")

    parser.add_argument("-g", "--groupCA", default=None, help="Group CA file path")
    parser.add_argument("-m", "--mqttHost", default=None, help="Targeted mqtt host")

    parser.add_argument("-t", "--topic", help="MQTT topic(s)", required=False)
    parser.add_argument("-l", "--log_level", help="Log Level", default=logging.INFO)

    parser.add_argument("-p", "--pin", help="gpio pin (using BCM numbering)", type=int, required=True)
    parser.add_argument("-x", "--on_time", help="Number of seconds on", type=float, default=1)
    parser.add_argument("-y", "--off_time", help="Number of seconds off", type=float, default=1)
    parser.add_argument("-z", "--default", help="Pattern 0=off, -1=on, 1..n=number of blinks", type=int, default=1)

    args = parser.parse_args()

    logging.basicConfig(filename=LOG_FILE, level=args.log_level,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')

    subscriber = awsiot.Subscriber(args.endpoint, args.rootCA, args.cert, args.key)

    output = DigitalOutputDevice(args.pin)

    logging.info("Subscribing to {}".format(args.topic))
    subscriber.subscribe(args.topic, my_callback)
    time.sleep(2)  # pause
    logging.info("Subscribing to {}/#".format(args.topic))
    subscriber.subscribe("{}/#".format(args.topic), my_callback)
    time.sleep(2)  # pause

    # Loop forever
    try:
        while True:
            time.sleep(0.5)  # sleep needed because CPU race
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
