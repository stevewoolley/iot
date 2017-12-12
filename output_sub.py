#!/usr/bin/env python

import argparse
import json
import awsiot
import logging
import datetime
import sys
import time
from gpiozero import DigitalOutputDevice


def my_callback(client, user_data, message):
    msg = json.loads(message.payload)
    logging.info(
        "output_sub {} {} {}".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), message.topic, msg))
    if args.blinks == 0:
        output.off()
    elif args.blinks < 0:
        output.on()
    else:
        output.blink(args.on_time, args.off_time, args.blinks)


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
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")

    parser.add_argument("-p", "--pin", help="gpio pin (using BCM numbering)", type=int, required=True)
    parser.add_argument("-n", "--blinks", help="Number of times to blink", type=int, default=1)
    parser.add_argument("-x", "--on_time", help="Number of seconds on", type=float, default=1)
    parser.add_argument("-y", "--off_time", help="Number of seconds off", type=float, default=1)

    args = parser.parse_args()

    output = DigitalOutputDevice(args.pin)

    subscriber = awsiot.Subscriber(args.endpoint, args.rootCA, args.cert, args.key)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
        subscriber.log_level = logging.DEBUG

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
