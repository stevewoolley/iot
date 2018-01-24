#!/usr/bin/env python

import json
import awsiot
import logging
import sys
import time

try:
    from gpiozero import DigitalOutputDevice
except ImportError:
    logging.error("Unable to import gpiozero")
    pass


def device(cmd):
    logging.info("device command: {}".format(cmd))
    if args.pin is not None:
        if cmd < 0:
            output.on()
        elif cmd == 0:
            output.off()
        elif cmd > 0:
            output.blink(args.on_time, args.off_time, cmd)


def callback(client, user_data, message):
    try:
        msg = json.loads(message.payload)
    except ValueError:
        msg = None
    logging.debug("received {} {}".format(message.topic, msg))
    device(args.default)


def level_callback(client, user_data, message):
    try:
        msg = json.loads(message.payload)
    except ValueError:
        msg = None
    logging.debug("received {} {}".format(message.topic, msg))
    for x in args.topic:
        if message.topic.startswith(x):
            commands = filter(None, message.topic.replace(x, '').split('/'))
            if len(commands) > 0:
                cmd = commands.pop(0)
                if cmd in awsiot.TOPIC_STATUS_ON:
                    device(-1)
                elif cmd in awsiot.TOPIC_STATUS_OFF:
                    device(0)
                elif cmd in awsiot.TOPIC_STATUS_PULSE:
                    if len(commands) > 0:
                        cmd = commands.pop(0)
                        if awsiot.int_val(cmd) is not None:
                            device(awsiot.int_val(cmd))
                    else:
                        device(args.default)
                else:
                    logging.warning('Device command ignored: {}'.format(cmd))


if __name__ == "__main__":
    parser = awsiot.iot_arg_parser()
    parser.add_argument("-p", "--pin", help="gpio pin (using BCM numbering)", type=int)
    parser.add_argument("-x", "--on_time", help="Number of seconds on", type=float, default=1)
    parser.add_argument("-y", "--off_time", help="Number of seconds off", type=float, default=1)
    parser.add_argument("-z", "--default", help="Pattern 0=off, -1=on, 1..n=number of blinks", type=int, default=1)
    args = parser.parse_args()

    logging.basicConfig(filename=awsiot.LOG_FILE, level=args.log_level, format=awsiot.LOG_FORMAT)

    subscriber = awsiot.Subscriber(args.endpoint, args.rootCA, args.cert, args.key)

    if args.pin is not None:
        output = DigitalOutputDevice(args.pin)

    if args.topic is not None and len(args.topic) > 0:
        for t in args.topic:
            subscriber.subscribe(t, callback)
            time.sleep(2)  # pause
            subscriber.subscribe("{}/#".format(t), level_callback)
            time.sleep(2)  # pause

    # Loop forever
    try:
        while True:
            time.sleep(0.5)  # sleep needed because CPU race
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
