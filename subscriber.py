#!/usr/bin/env python

import json
import awsiot
import sys
import time


def my_callback(client, user_data, message):
    for topic in args.topic:
        cmd, arg = awsiot.topic_search(topic, message.topic)
        if cmd:
            print("FOUND {} {}".format(cmd, arg))


if __name__ == "__main__":
    parser = awsiot.iot_arg_parser()
    args = parser.parse_args()

    subscriber = awsiot.Subscriber(args.endpoint, args.rootCA, args.cert, args.key)

    if args.topic is not None and len(args.topic) > 0:
        for t in args.topic:
            subscriber.subscribe('{}/#'.format(t.split('/').pop(0)), my_callback)

    # Loop forever
    try:
        while True:
            time.sleep(1)  # sleep needed because CPU race
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
