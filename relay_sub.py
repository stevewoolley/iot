#!/usr/bin/env python

import json
import awsiot
import logging
import sys
import time

try:
    from gpiozero import OutputDevice
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
            output.on()
            time.sleep(args.pulse_delay)
            output.off()


def callback(client, user_data, message):
    try:
        msg = json.loads(message.payload)
    except ValueError:
        msg = None
    logging.info("received {} {}".format(message.topic, msg))
    if message.topic == args.topic:
        device(args.default)


def level_callback(client, user_data, message):
    try:
        msg = json.loads(message.payload)
    except ValueError:
        msg = None
    level = message.topic.replace(args.topic, '')
    logging.info("received {} {}".format(message.topic, msg))
    if level in awsiot.TOPIC_STATUS_ON:
        device(-1)
    elif level in awsiot.TOPIC_STATUS_OFF:
        device(0)
    elif level in awsiot.TOPIC_STATUS_PULSE:
        device(args.default)
    else:
        logging.warning('Device command ignored: {}'.format(level))


if __name__ == "__main__":
    parser = awsiot.iot_arg_parser()
    parser.add_argument("-p", "--pin", help="gpio pin (using BCM numbering)", type=int, required=True)
    parser.add_argument("-d", "--pulse_delay", help="length of pulse in seconds", type=float, default=0.5)
    parser.add_argument("-a", "--active_high",
                        help="If True, the on() method will set the GPIO to HIGH. " +
                             "If False(the default), the on() method will set the GPIO to LOW " +
                             "(the off() method always does the opposite).",
                        type=bool, default=False)
    parser.add_argument("-i", "--initial_value",
                        help="If False (the default), the device will be off initially. " +
                             "If None, the device will be left in whatever state the pin is found " +
                             "in when configured for output (warning: this can be on). " +
                             "If True, the device will be switched on initially.",
                        type=bool, default=False)
    parser.add_argument("-z", "--default", help="Pattern 0=off, 1=on, 1=pulse", type=int, default=1)
    args = parser.parse_args()

    logging.basicConfig(filename=awsiot.LOG_FILE, level=args.log_level, format=awsiot.LOG_FORMAT)

    subscriber = awsiot.Subscriber(args.endpoint, args.rootCA, args.cert, args.key, args.thing, args.groupCA)

    if args.pin is not None:
        output = OutputDevice(args.pin, args.active_high, args.initial_value)

    subscriber.subscribe(args.topic, callback)
    time.sleep(2)  # pause
    subscriber.subscribe("{}/+".format(args.topic), level_callback)
    time.sleep(2)  # pause

    # Loop forever
    try:
        while True:
            time.sleep(0.5)  # sleep needed because CPU race
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
