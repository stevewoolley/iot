#!/usr/bin/env python

import json
import awsiot
import logging
import sys
import time


def my_callback(client, user_data, message):
    try:
        msg = json.loads(message.payload)
    except ValueError:
        msg = ""
    logging.info("received {} {}".format(message.topic, msg))


if __name__ == "__main__":
    parser = awsiot.iot_arg_parser()
    args = parser.parse_args()

    logging.basicConfig(filename=awsiot.LOG_FILE, level=args.log_level, format=awsiot.LOG_FORMAT)

    subscriber = awsiot.Subscriber(args.endpoint, args.rootCA, args.cert, args.key, args.thing, args.groupCA)

    for t in args.topics:
        subscriber.subscribe(t, my_callback)
        time.sleep(2)  # pause

    # Loop forever
    try:
        while True:
            time.sleep(1)  # sleep needed because CPU race
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
