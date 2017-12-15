#!/usr/bin/env python

import json
import awsiot
import logging
from gpiozero import Button
from signal import pause


def pub(value):
    if args.topic is not None:
        publisher.publish(args.topic,
                          json.dumps({args.source: value, awsiot.MESSAGE: "{} {}".format(args.source, value)}))
    if args.thing is not None:
        publisher.publish(awsiot.iot_thing_topic(args.thing), awsiot.iot_payload(awsiot.REPORTED, {args.source: value}))


def pressed():
    logging.info("{} {} {}".format(args.source, args.pin, args.high_value))
    pub(args.high_value)


def released():
    logging.info("{} {} {}".format(args.source, args.pin, args.low_value))
    pub(args.high_value)


if __name__ == "__main__":
    parser = awsiot.iot_arg_parser()
    parser.add_argument("-p", "--pin", help="gpio pin (using BCM numbering)", type=int, required=True)
    parser.add_argument("-u", "--pull_up",
                        help="If True (the default), the GPIO pin will be pulled high by default. " +
                             "In this case, connect the other side of the button to ground. " +
                             "If False, the GPIO pin will be pulled low by default. " +
                             "In this case, connect the other side of the button to 3V3",
                        type=bool, default=True)
    parser.add_argument("-b", "--bounce_time",
                        help="If None (the default), no software bounce compensation will be performed. " +
                             "Otherwise, this is the length of time (in seconds) " +
                             "that the component will ignore changes in state after an initial change.",
                        type=float, default=None)
    parser.add_argument("-s", "--source", help="Source", required=True)
    parser.add_argument("-y", "--high_value", help="high value", default=1)
    parser.add_argument("-z", "--low_value", help="low value", default=0)
    parser.add_argument("-o", "--low_topic", help="Low value topic (defaults to high_value if not assigned")
    args = parser.parse_args()
    # default low_topic to topic if not defined
    if args.low_topic is None:
        args.low_topic = args.topic

    logging.basicConfig(filename=awsiot.LOG_FILE, level=args.log_level, format=awsiot.LOG_FORMAT)

    publisher = awsiot.Publisher(args.endpoint, args.rootCA, args.cert, args.key, args.thing, args.groupCA)

    inp = Button(args.pin, pull_up=args.pull_up, bounce_time=args.bounce_time)

    inp.when_pressed = pressed
    inp.when_released = released

    pause()
