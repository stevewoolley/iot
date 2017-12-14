#!/usr/bin/env python

import argparse
import json
import awsiot
import logging
import sys
import time
from gpiozero import OutputDevice


def pulse():
    output.off()
    time.sleep(args.pulse_delay)
    output.on()


def my_callback(client, user_data, message):
    try:
        msg = json.loads(message.payload)
    except ValueError:
        msg = None
    logging.info("received {} {}".format(message.topic, msg))
    if message.topic == args.topic:
        if args.default == 0:
            output.off()
        elif args.default < 0:
            pulse()
        else:
            output.on()
    if message.topic.replace(args.topic, '') in awsiot.TOPIC_STATUS_ON:
        output.on()
    elif message.topic.replace(args.topic, '') in awsiot.TOPIC_STATUS_OFF:
        output.off()
    elif message.topic.replace(args.topic, '') in awsiot.TOPIC_STATUS_PULSE:
        pulse()
    elif message.topic.replace(args.topic, '') in awsiot.TOPIC_STATUS_TOGGLE:
        output.toggle()


if __name__ == "__main__":
    parser = awsiot.iot_sub_arg_parser()
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
    parser.add_argument("-z", "--default", help="Pattern 0=off, 1=on, 1=pulse", type=int, default=1)
    args = parser.parse_args()

    logging.basicConfig(filename=awsiot.LOG_FILE, level=args.log_level, format=awsiot.LOG_FORMAT)

    output = OutputDevice(args.pin, args.active_high, args.initial_value)

    subscriber = awsiot.Subscriber(args.endpoint, args.rootCA, args.cert, args.key, args.thing, args.groupCA)

    subscriber.subscribe(args.topic, my_callback)
    time.sleep(2)  # pause
    subscriber.subscribe("{}/#".format(args.topic), my_callback)
    time.sleep(2)  # pause

    # Loop forever
    try:
        while True:
            time.sleep(0.5)  # sleep needed because CPU race
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
