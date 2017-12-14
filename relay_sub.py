#!/usr/bin/env python

import argparse
import json
import awsiot
import logging
import sys
import time
from gpiozero import OutputDevice

LOG_FILE = '/var/log/iot.log'


def pulse():
    output.off()
    time.sleep(args.pulse_delay)
    output.on()


def my_callback(client, user_data, message):
    try:
        msg = json.loads(message.payload)
    except ValueError:
        msg = ""
    logging.info(
        "relay_sub mqtt {} {}".format(message.topic, msg))
    if message.topic == args.topic:
        if args.default == 0:
            output.off()
        elif args.default < 0:
            pulse()
        else:
            output.on()
    if message.topic.replace(args.topic, '') in ['/1', '/on']:
        output.on()
    elif message.topic.replace(args.topic, '') in ['/0', '/off']:
        output.off()
    elif message.topic.replace(args.topic, '') in ['/blink', '/pulse']:
        pulse()
    elif message.topic.replace(args.topic, '') in ['/toggle']:
        output.toggle()


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
    parser.add_argument("-d", "--pulse_delay", help="length of pulse in seconds", type=float, default=0.5)
    parser.add_argument("-z", "--default", help="Pattern 0=off, 1=on, 1=pulse", type=int, default=1)
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

    logging.basicConfig(filename=LOG_FILE, level=args.log_level,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')

    output = OutputDevice(args.pin, args.active_high, args.initial_value)

    subscriber = awsiot.Subscriber(args.endpoint, args.rootCA, args.cert, args.key)

    logging.info("relay_sub subscribing: {}".format(args.topic))
    subscriber.subscribe(args.topic, my_callback)
    time.sleep(2)  # pause
    logging.info("relay_sub subscribing: {}/#".format(args.topic))
    subscriber.subscribe("{}/#".format(args.topic), my_callback)
    time.sleep(2)  # pause

    # Loop forever
    try:
        while True:
            time.sleep(0.5)  # sleep needed because CPU race
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
