#!/usr/bin/env python

import json
import awsiot
import logging
import sys
import time
import platform

try:
    import picamera
except ImportError:
    logging.error("Unable to import picamera")
    pass


def snapshot():
    try:
        filename = "{}-{}.jpg".format(args.source, awsiot.now_string())
        logging.info("snapshot: {}".format(filename))
        camera.capture(filename)
        return filename
    except Exception as e:
        logging.error("snapshot failed {}".format(e.message))
        return None


def callback(client, user_data, message):
    try:
        msg = json.loads(message.payload)
    except ValueError:
        msg = None
    logging.info("received {} {}".format(message.topic, msg))
    commands = filter(None, message.topic.replace(args.topic, '').split('/'))
    if len(commands) > 0:
        cmd = commands.pop(0)
        if cmd == 'snapshot':
            logging.info("command: {}".format(cmd))
            filename = snapshot()
            if filename is not None and args.bucket is not None:
                awsiot.mv_to_s3(filename, args.bucket)
        elif cmd == 'recording':
            logging.info("command: {}".format(cmd))
        elif cmd == 'recognize':
            logging.info("command: {}".format(cmd))
        else:
            logging.warning('Unrecognized command: {}'.format(cmd))
    else:
        logging.warning("No commands")


if __name__ == "__main__":
    parser = awsiot.iot_arg_parser()
    parser.add_argument("-x", "--width", help="camera resolution width", type=int, default=640)
    parser.add_argument("-y", "--height", help="camera resolution height", type=int, default=480)
    parser.add_argument("-z", "--rotation", help="camera rotation", type=int, default=0)
    parser.add_argument("-n", "--source", help="source name", default=platform.node().split('.')[0])
    parser.add_argument("-b", "--bucket", help="S3 bucket")
    args = parser.parse_args()

    logging.basicConfig(filename=awsiot.LOG_FILE, level=args.log_level, format=awsiot.LOG_FORMAT)

    subscriber = awsiot.Subscriber(args.endpoint, args.rootCA, args.cert, args.key, args.thing, args.groupCA)

    camera = picamera.PiCamera()
    camera.resolution = (args.width, args.height)
    camera.rotation = args.rotation

    subscriber.subscribe("{}/#".format(args.topic), callback)
    time.sleep(2)  # pause

    # Loop forever
    try:
        while True:
            time.sleep(0.5)  # sleep needed because CPU race
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
