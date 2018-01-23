#!/usr/bin/env python

import json
import awsiot
import logging
import sys
import time
import xmlrpclib
import supervisor.xmlrpc


def callback(client, user_data, message):
    try:
        msg = json.loads(message.payload)
    except ValueError:
        msg = None
    logging.debug("received {} {}".format(message.topic, msg))
    for x in args.topic:
        if message.topic.startswith(x):
            commands = filter(None, message.topic.replace(x, '').split('/'))
            if len(commands) > 0:
                cmd = commands.pop(0)
                if cmd == 'getAllProcessInfo':
                    logging.debug("command: {}".format(cmd))
                    results = proxy.supervisor.getAllProcessInfo()
                    logging.info("getAllProcessInfo {}".format(results))
                    if args.thing:
                        supervised = []
                        for s in results:
                            supervised.append('{} ({})'.format(s['name'], s['statename']))
                        publisher = awsiot.Publisher(args.endpoint, args.rootCA, args.cert, args.key, args.thing,
                                                     args.groupCA)
                        publisher.publish(awsiot.iot_thing_topic(args.thing),
                                          awsiot.iot_payload(awsiot.REPORTED, {'supervised': ', '.join(supervised)}))
                elif cmd == 'startProcess':
                    logging.debug("command: {}".format(cmd))
                    cmd = commands.pop(0)
                    results = proxy.supervisor.startProcess(cmd)
                elif cmd == 'stopProcess':
                    logging.debug("command: {}".format(cmd))
                    results = proxy.supervisor.stopProcess(cmd)
                else:
                    logging.warning('Unrecognized command: {}'.format(cmd))
            else:
                logging.warning("No commands: {}".format(message.topic))


if __name__ == "__main__":
    parser = awsiot.iot_arg_parser()
    parser.add_argument("--socket_path", help="socket path", default='/var/run/supervisor.sock')
    args = parser.parse_args()

    logging.basicConfig(filename=awsiot.LOG_FILE, level=args.log_level, format=awsiot.LOG_FORMAT)

    subscriber = awsiot.Subscriber(args.endpoint, args.rootCA, args.cert, args.key, args.thing, args.groupCA)

    proxy = xmlrpclib.ServerProxy(
        'http://127.0.0.1', transport=supervisor.xmlrpc.SupervisorTransport(
            None, None, serverurl='unix://{}'.format(args.socket_path)))

    if args.topic is not None and len(args.topic) > 0:
        for t in args.topic:
            subscriber.subscribe("{}/#".format(t), callback)
            time.sleep(2)  # pause

    # Loop forever
    try:
        while True:
            time.sleep(0.5)  # sleep needed because CPU race
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
