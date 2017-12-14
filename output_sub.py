#!/usr/bin/env python

import json
import awsiot
import logging
import sys
import time
from gpiozero import DigitalOutputDevice


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
            output.on()
        else:
            output.blink(args.on_time, args.off_time, args.default)
    if message.topic.replace(args.topic, '') in awsiot.TOPIC_STATUS_ON:
        output.on()
    elif message.topic.replace(args.topic, '') in awsiot.TOPIC_STATUS_OFF:
        output.off()
    elif message.topic.replace(args.topic, '') in awsiot.TOPIC_STATUS_PULSE:
        output.blink(args.on_time, args.off_time, args.default)


if __name__ == "__main__":
    parser = awsiot.iot_sub_arg_parser()
    parser.add_argument("-p", "--pin", help="gpio pin (using BCM numbering)", type=int, required=True)
    parser.add_argument("-x", "--on_time", help="Number of seconds on", type=float, default=1)
    parser.add_argument("-y", "--off_time", help="Number of seconds off", type=float, default=1)
    parser.add_argument("-z", "--default", help="Pattern 0=off, -1=on, 1..n=number of blinks", type=int, default=1)
    args = parser.parse_args()

    logging.basicConfig(filename=awsiot.LOG_FILE, level=args.log_level, format=awsiot.LOG_FORMAT)

    subscriber = awsiot.Subscriber(args.endpoint, args.rootCA, args.cert, args.key, args.thing, args.groupCA)

    output = DigitalOutputDevice(args.pin)

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
