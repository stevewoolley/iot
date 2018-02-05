#!/usr/bin/env python

import json
import awsiot
import logging
from signal import pause
import RPi.GPIO as GPIO
import time


def pub(topic, value):
    if topic is not None and len(topic) > 0:
        for t in topic:
            publisher.publish(t,
                              json.dumps(
                                  {args.shadow_var: value, awsiot.MESSAGE: "{} {}".format(args.shadow_var, value)}))
    publisher.publish(awsiot.iot_thing_topic(args.thing), awsiot.iot_payload(awsiot.REPORTED, {args.shadow_var: value}))


def get_distance():
    # set Trigger to HIGH
    GPIO.output(GPIO_TRIGGER, True)

    # set Trigger after 0.01ms to LOW
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGGER, False)

    start_time = time.time()
    stop_time = time.time()

    # save StartTime
    while GPIO.input(GPIO_ECHO) == 0:
        start_time = time.time()

    # save time of arrival
    while GPIO.input(GPIO_ECHO) == 1:
        stop_time = time.time()

    # time difference between start and arrival
    time_lapsed = stop_time - start_time
    # multiply with the sonic speed (34300 cm/s)
    # and divide by 2, because there and back
    distance = (time_lapsed * 34300) / 2

    return distance


if __name__ == "__main__":
    parser = awsiot.iot_arg_parser()
    parser.add_argument("--trigger_pin", help="trigger gpio pin (using BCM numbering)", type=int, required=True)
    parser.add_argument("--echo_pin", help="echo gpio pin (using BCM numbering)", type=int, required=True)
    args = parser.parse_args()

    # GPIO Mode (BOARD / BCM)
    GPIO.setmode(GPIO.BCM)

    # set GPIO Pins
    GPIO_TRIGGER = args.trigger_pin
    GPIO_ECHO = args.echo_pin

    # set GPIO direction (IN / OUT)
    GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
    GPIO.setup(GPIO_ECHO, GPIO.IN)

    logging.basicConfig(filename=awsiot.LOG_FILE, level=args.log_level, format=awsiot.LOG_FORMAT)

    publisher = awsiot.Publisher(args.endpoint, args.rootCA, args.cert, args.key)
    properties = {}
    properties["distance"] = get_distance()
    publisher.publish(awsiot.iot_thing_topic(args.thing), awsiot.iot_payload(awsiot.REPORTED, properties))
    GPIO.cleanup()
