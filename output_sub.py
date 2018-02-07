#!/usr/bin/env python

import awsiot
import logging
import sys
import time
from gpiozero import DigitalOutputDevice


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
    logging.debug("received {} {}".format(message.topic, message))
    for topic in args.topic:
        cmd, arg = awsiot.topic_search(topic, message.topic)
        if cmd in awsiot.TOPIC_STATUS_PULSE:
            logging.debug("command: {}".format(cmd))
            device(int(arg))
        elif cmd in awsiot.TOPIC_STATUS_ON:
            logging.debug("command: {}".format(cmd))
            device(-1)
        elif cmd in awsiot.TOPIC_STATUS_OFF:
            logging.debug("command: {}".format(cmd))
            device(0)
        else:
            logging.warning('Unrecognized command: {}'.format(cmd))


if __name__ == "__main__":
    parser = awsiot.iot_arg_parser()
    parser.add_argument("-p", "--pin", help="gpio pin (using BCM numbering)", type=int)
    parser.add_argument("-x", "--on_time", help="Number of seconds on", type=float, default=1)
    parser.add_argument("-y", "--off_time", help="Number of seconds off", type=float, default=1)
    parser.add_argument("-z", "--default", help="Pattern 0=off, -1=on, 1..n=number of blinks", type=int, default=1)
    args = parser.parse_args()

    logging.basicConfig(filename=awsiot.LOG_FILE, level=args.log_level, format=awsiot.LOG_FORMAT)

    subscriber = awsiot.MQTT(args.endpoint, args.rootCA, args.cert, args.key)

    output = DigitalOutputDevice(args.pin)

    if args.topic is not None and len(args.topic) > 0:
        for t in args.topic:
            subscriber.subscribe('{}/#'.format(t.split('/').pop(0)), callback)
            time.sleep(2)  # pause

    # Loop forever
    try:
        while True:
            time.sleep(0.5)  # sleep needed because CPU race
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
