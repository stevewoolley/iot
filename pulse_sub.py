#!/usr/bin/env python

import argparse
import json
import awsiot
import logging
import datetime
import sys
import time
from gpiozero import OutputDevice

LOG_FILE = '/var/log/iot.log'

def pulse():
    output.off()
    time.sleep(args.pulse_delay)
    output.on()


def my_callback(client, user_data, message):
    msg = json.loads(message.payload)
    logging.info(
        "pulse_sub {} {} {}".format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), message.topic, msg))
    pulse()


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

    parser.add_argument("-p", "--pin", help="gpio pin (using BCM numbering)", type=int, required=True)
    parser.add_argument("-d", "--pulse_delay", help="length of pulse in seconds", type=float, default=0.5)
    parser.add_argument("-a", "--active_high",
                        help="If True (the default), the on() method will set the GPIO to HIGH. " +
                             "If False, the on() method will set the GPIO to LOW " +
                             "(the off() method always does the opposite).",
                        type=bool, default=True)
    parser.add_argument("-i", "--initial_value",
                        help="If False (the default), the device will be off initially. " +
                             "If None, the device will be left in whatever state the pin is found " +
                             "in when configured for output (warning: this can be on). " +
                             "If True, the device will be switched on initially.",
                        type=bool, default=False)

    args = parser.parse_args()

    logging.basicConfig(filename=LOG_FILE, level=args.log_level)

    output = OutputDevice(args.pin, args.active_high, args.initial_value)

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
