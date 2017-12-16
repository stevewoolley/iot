#!/usr/bin/env python

import json
import awsiot
import logging
from signal import pause
import Adafruit_DHT

DHT11 = 11
DHT22 = 22
AM2302 = 22
SENSORS = [DHT11, DHT22, AM2302]


def pub(temp, humid):
    if args.topic is not None:
        publisher.publish(args.topic,
                          json.dumps({"temperature": temp, "humidity": humid,
                                      awsiot.MESSAGE: "temperature: {} humidity: {}".format(temp, humid)}))
    if args.thing is not None:
        publisher.publish(awsiot.iot_thing_topic(args.thing),
                          awsiot.iot_payload(awsiot.REPORTED, {'temperature': temp, 'humidity': humid}))


if __name__ == "__main__":
    parser = awsiot.iot_arg_parser()
    parser.add_argument("-p", "--pin", help="gpio pin (using BCM numbering)", type=int, required=True)
    parser.add_argument("-y", "--dht_type", help="DHT sensor type %s" % SENSORS, type=int, default=Adafruit_DHT.DHT22)
    args = parser.parse_args()

    logging.basicConfig(filename=awsiot.LOG_FILE, level=args.log_level, format=awsiot.LOG_FORMAT)

    publisher = awsiot.Publisher(args.endpoint, args.rootCA, args.cert, args.key, args.thing, args.groupCA)

    humidity, temperature = Adafruit_DHT.read_retry(args.dht_type, args.pin)
    if humidity is not None and temperature is not None:
        logging.info("DHT {} temperature {} humidity {}".format(args.pin, temperature, humidity))
        pub(temperature, humidity)
    else:
        logging.warn("Can't read temperature/humidity from DHT {}".format(args.pin))

    pause()
