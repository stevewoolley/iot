#!/usr/bin/env python

import awsiot
import logging
import sys
import time
import RPi.GPIO as GPIO
import numpy as np


def get_distance(trigger, echo, iterations=5, time_between_iterations=1, rounding_digits=2):
    results = []
    for i in range(iterations):
        GPIO.output(trigger, False)
        time.sleep(0.05)
        GPIO.output(trigger, True)
        time.sleep(0.02)
        GPIO.output(trigger, False)
        start_time = time.time()
        stop_time = time.time()
        while GPIO.input(echo) == 0:
            start_time = time.time()
        while GPIO.input(echo) == 1:
            stop_time = time.time()
        time_lapsed = stop_time - start_time
        val = (time_lapsed * 34300) / 2
        logging.info('measured distance {} cm'.format(val))
        results.append(val)
        time.sleep(time_between_iterations)
    if len(results) == 0:
        return None
    return round(np.median(results), rounding_digits)


def callback(client, user_data, message):
    logging.debug("received {} {}".format(message.topic, message))
    distance = get_distance(args.trigger_pin, args.echo_pin, args.iterations)
    logging.info('median distance {} cm'.format(distance))
    if distance:
        for topic in args.topic:
            if args.min_value <= distance <= args.max_value:
                if awsiot.topic_search(topic, message.topic):
                    mqtt.publish(awsiot.iot_thing_topic(args.thing),
                                 awsiot.iot_payload(awsiot.REPORTED, {'distance': distance}))
                else:
                    logging.warning('Unrecognized command')
            else:
                logging.warning(
                    'calculated distance ({} cm) outside range {} - {}'.format(distance, args.min_value, args.max_value))
    else:
        logging.error('unable to calculate distance')


if __name__ == "__main__":
    parser = awsiot.iot_arg_parser()
    parser.add_argument("--trigger_pin", help="trigger gpio pin (using BCM numbering)", type=int, required=True)
    parser.add_argument("--echo_pin", help="echo gpio pin (using BCM numbering)", type=int, required=True)
    parser.add_argument("--iterations", help="number of iterations to determine median value", type=int, default=5)
    parser.add_argument("--max_value", help="max distance", type=float, default=400.0)
    parser.add_argument("--min_value", help="min distance", type=float, default=2.0)
    args = parser.parse_args()

    logging.basicConfig(filename=awsiot.LOG_FILE, level=args.log_level, format=awsiot.LOG_FORMAT)

    # initialize hardware
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(args.trigger_pin, GPIO.OUT)
    GPIO.setup(args.echo_pin, GPIO.IN)

    # initialize iot
    mqtt = awsiot.MQTT(args.endpoint, args.rootCA, args.cert, args.key)

    if args.topic is not None and len(args.topic) > 0:
        for t in args.topic:
            mqtt.subscribe('{}/#'.format(t.split('/').pop(0)), callback)
            time.sleep(2)  # pause

    # Loop forever
    try:
        while True:
            time.sleep(0.5)  # sleep needed because CPU race
    except (KeyboardInterrupt, SystemExit):
        GPIO.cleanup()
        sys.exit()
