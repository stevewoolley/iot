#!/usr/bin/env python

import argparse
import json
import awsiot
import logging
from gpiozero import MotionSensor
from signal import pause

LOG_FILE = '/var/log/iot.log'

def motion():
    logging.info("motion_pub: motion detected on pin: {}".format(args.pin))
    message_json = json.dumps({'motion': True})
    for t in args.topic:
        publisher.publish(t, message_json)


def no_motion():
    logging.info("motion_sub: no motion detected on pin: {}".format(args.pin))
    message_json = json.dumps({'motion': False})
    for t in args.topic:
        publisher.publish(t, message_json)


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
    parser.add_argument("-q", "--queue_len",
                        help="The length of the queue used to store values read from the sensor. (1 = disabled)",
                        type=int, default=1)
    parser.add_argument("-x", "--sample_rate",
                        help="The number of values to read from the device (and append to the internal queue) per second",
                        type=float, default=100)
    parser.add_argument("-y", "--threshold",
                        help="When the mean of all values in the internal queue rises above this value, the sensor will be considered active by the is_active property, and all appropriate events will be fired",
                        type=float, default=0.5)
    args = parser.parse_args()

    logging.basicConfig(filename=LOG_FILE, level=args.log_level)

    publisher = awsiot.Publisher(args.endpoint, args.rootCA, args.cert, args.key)

    pir = MotionSensor(args.pin,
                       queue_len=args.queue_len,
                       sample_rate=args.sample_rate,
                       threshold=args.threshold)

    pir.when_motion = motion
    pir.when_no_motion = no_motion

    pause()
