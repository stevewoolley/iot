#!/usr/bin/env python

import awsiot
import logging
import sys
import time
from gpiozero import OutputDevice


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
    logging.debug("received {} {}".format(message.topic, message))
    for topic in args.topic:
        cmd, arg = awsiot.topic_search(topic, message.topic)
        if cmd in awsiot.TOPIC_STATUS_PULSE:
            logging.debug("command: {}".format(cmd))
            device(1)
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
    args = parser.parse_args()

    logging.basicConfig(filename=awsiot.LOG_FILE, level=args.log_level, format=awsiot.LOG_FORMAT)

    subscriber = awsiot.Subscriber(args.endpoint, args.rootCA, args.cert, args.key)

    output = OutputDevice(args.pin, args.active_high, args.initial_value)

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
