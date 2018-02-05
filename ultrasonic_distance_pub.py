#!/usr/bin/env python

import json
import awsiot
import logging
import RPi.GPIO as GPIO
import time
import sys


def pub(dist):
    if args.topic is not None and len(args.topic) > 0:
        for t in args.topic:
            publisher.publish(t,
                              json.dumps({"distance": dist, awsiot.MESSAGE: "distance: {}".format(dist)}))
    publisher.publish(awsiot.iot_thing_topic(args.thing),
                      awsiot.iot_payload(awsiot.REPORTED, {'distance': dist}))


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
    parser.add_argument("--pct_change", help="change must be greater than this value to signal", type=int, default=10)

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

    # Loop forever
    try:
        last_distance = 0
        while True:
            distance = get_distance()
            if 2 <= distance <= 450:
                if last_distance == 0 or (float(abs(last_distance - distance)) / float(last_distance)) * 100.0 > args.pct_change:
                    logging.info("distance: {}".format(distance))
                    pub(distance)
            last_distance = distance
            time.sleep(0.5)  # sleep needed because CPU race
    except (KeyboardInterrupt, SystemExit):
        GPIO.cleanup()
        sys.exit()
