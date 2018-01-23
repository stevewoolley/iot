#!/usr/bin/env python

import json
import awsiot
import logging
from signal import pause

try:
    from gpiozero import MotionSensor
except ImportError:
    logging.error("Unable to import gpiozero")
    pass


def pub(topic, value):
    if topic is not None and len(topic) > 0:
        for t in topic:
            publisher.publish(t,
                              json.dumps({args.source: value, awsiot.MESSAGE: "{} {}".format(args.source, value)}))
    if args.thing is not None:
        publisher.publish(awsiot.iot_thing_topic(args.thing), awsiot.iot_payload(awsiot.REPORTED, {args.source: value}))


def motion():
    logging.info("{} {} {}".format(args.source, args.pin, args.high_value))
    pub(args.topic, args.high_value)


def no_motion():
    logging.info("{} {} {}".format(args.source, args.pin, args.low_value))
    if args.low_topic:
        pub(args.low_topic, args.low_value)


if __name__ == "__main__":
    parser = awsiot.iot_arg_parser()
    parser.add_argument("-p", "--pin", help="gpio pin (using BCM numbering)", type=int, required=True)
    parser.add_argument("-q", "--queue_len",
                        help="The length of the queue used to store values read from the sensor. (1 = disabled)",
                        type=int, default=1)
    parser.add_argument("-w", "--sample_rate",
                        help="The number of values to read from the device " +
                             "(and append to the internal queue) per second",
                        type=float, default=100)
    parser.add_argument("-x", "--threshold",
                        help="When the mean of all values in the internal queue rises above this value, " +
                             "the sensor will be considered active by the is_active property, " +
                             "and all appropriate events will be fired",
                        type=float, default=0.5)
    parser.add_argument("-s", "--source", help="Source", required=True)
    parser.add_argument("-y", "--high_value", help="high value", default=1)
    parser.add_argument("-z", "--low_value", help="low value", default=0)
    parser.add_argument("-o", "--low_topic", nargs='*', help="Low topic")
    args = parser.parse_args()

    logging.basicConfig(filename=awsiot.LOG_FILE, level=args.log_level, format=awsiot.LOG_FORMAT)

    publisher = awsiot.Publisher(args.endpoint, args.rootCA, args.cert, args.key, args.thing, args.groupCA)

    pir = MotionSensor(args.pin,
                       queue_len=args.queue_len,
                       sample_rate=args.sample_rate,
                       threshold=args.threshold)

    pir.when_motion = motion
    pir.when_no_motion = no_motion

    pause()
