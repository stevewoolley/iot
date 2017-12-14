import os
import logging
import json
import argparse
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from AWSIoTPythonSDK.core.greengrass.discovery.providers import DiscoveryInfoProvider
from AWSIoTPythonSDK.core.protocol.connection.cores import ProgressiveBackOffCore
from AWSIoTPythonSDK.exception.AWSIoTExceptions import DiscoveryInvalidRequestException

MAX_DISCOVERY_RETRIES = 10
LOG_FILE = '/var/log/iot.log'
STATE = 'state'
REPORTED = 'reported'
DESIRED = 'desired'
THING_SHADOW = "$aws/things/{}/shadow/update"
DATE_FORMAT = '%Y/%m/%d %-I:%M %p %Z'
LOG_FORMAT = '%(asctime)s %(filename)-15s %(funcName)-15s %(levelname)-8s %(message)s'
LOG_FILE = '/var/log/iot.log'
DATE_FORMAT = '%Y/%m/%d %-I:%M %p %Z'
MESSAGE = 'message'
TOPIC_STATUS_ON = ['/1', '/on']
TOPIC_STATUS_OFF = ['/0', '/off']
TOPIC_STATUS_TOGGLE = ['/toggle']
TOPIC_STATUS_PULSE = ['/blink', '/pulse']


def iot_thing_topic(thing):
    return THING_SHADOW.format(thing)


def iot_payload(target, doc):
    return json.dumps({STATE: {target: doc}})


def iot_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--endpoint", required=True, help="Your AWS IoT custom endpoint")
    parser.add_argument("-r", "--rootCA", required=True, help="Root CA file path")
    parser.add_argument("-c", "--cert", required=True, help="Certificate file path")
    parser.add_argument("-k", "--key", required=True, help="Private key file path")
    parser.add_argument("-n", "--thing", help="Targeted thing name")
    parser.add_argument("-g", "--groupCA", default=None, help="Group CA file path")
    parser.add_argument("-m", "--mqttHost", default=None, help="Targeted mqtt host")
    parser.add_argument("-t", "--topic", help="MQTT topic(s)")
    parser.add_argument("-l", "--log_level", help="Log Level", default=logging.INFO)
    return parser


class Discoverer:
    def __init__(self, end_point, root_ca_path, certificate_path, private_key_path, group_ca_path):
        self._end_point = end_point
        self._root_ca_path = root_ca_path
        self._certificate_path = certificate_path
        self._private_key_path = private_key_path
        self._group_ca_path = group_ca_path
        self._cores = None
        self._discovered = False

    @property
    def discovered(self):
        return self._discovered

    @property
    def cores(self):
        return self._cores

    @property
    def core(self):
        if self._cores is None:
            return None
        if len(self._cores) > 0:
            return self._cores[0]
        else:
            return None

    def discover(self, thing):
        backoff_core = ProgressiveBackOffCore()
        dip = DiscoveryInfoProvider()
        dip.configureEndpoint(self._end_point)
        dip.configureCredentials(self._root_ca_path, self._certificate_path, self._private_key_path)
        dip.configureTimeout(10)  # 10 sec
        retry_count = MAX_DISCOVERY_RETRIES
        while retry_count != 0:
            logging.info("discovering")
            try:
                di = dip.discover(thing)
                ca_list = di.getAllCas()
                self._cores = di.getAllCores()
                # We only pick the first ca and core info
                group_id, ca = ca_list[0]
                logging.info("discovered {} from gg group: {}".format(self.core.coreThingArn, group_id))
                if not os.path.isfile(self._group_ca_path):
                    group_ca_file = open(self._group_ca_path, "w")
                    group_ca_file.write(ca)
                    group_ca_file.close()
                self._discovered = True
                break
            except DiscoveryInvalidRequestException as e:
                logging.error("discovery invalid request: {}".format(e.message))
                break
            except BaseException as e:
                retry_count -= 1
                logging.info("discovery backoff...")
                backoff_core.backOff()
        if not self._discovered:
            raise RuntimeError("discovery failed")


class Publisher:
    def __init__(self, end_point, root_ca_path, certificate_path, private_key_path, thing_name=None, group_ca_path=None,
                 mqtt_host=None, mqtt_port=8883):
        self._end_point = end_point
        self._root_ca_path = root_ca_path
        self._certificate_path = certificate_path
        self._private_key_path = private_key_path
        self._thing_name = thing_name
        self._group_ca_path = group_ca_path
        self._connected = False
        self._client = AWSIoTMQTTClient(None)
        self._mqtt_host = mqtt_host
        self._mqtt_port = mqtt_port
        self._discoverer = Discoverer(self._end_point, self._root_ca_path, self._certificate_path,
                                      self._private_key_path, self._group_ca_path)

    @property
    def connected(self):
        return self._connected

    @property
    def mqtt_host(self):
        return self._mqtt_host

    @property
    def mqtt_port(self):
        return self._mqtt_port

    def connect(self):
        # use the presence of group_ca_path to determine if local or cloud
        logging.info("publisher connect {}".format(self._end_point))
        if self._group_ca_path is None:
            self._client.configureCredentials(self._root_ca_path, self._private_key_path, self._certificate_path)
            self._client.configureEndpoint(self._end_point, 8883)
        else:
            if self._mqtt_host is None:
                self._discoverer.discover(self._thing_name)
                # Iterate through all connection options for the greengrass core and use the first successful one
                for connectivityInfo in self._discoverer.core.connectivityInfoList:
                    current_host = connectivityInfo.host
                    current_port = connectivityInfo.port
                    self._client.configureEndpoint(current_host, current_port)
                    if self._client.connect():
                        self._mqtt_host = current_host
                        self._mqtt_port = current_port
                        break
                if not self._discoverer.discovered:
                    raise RuntimeError("No hosts discovered")
            self._client.configureCredentials(self._group_ca_path, self._private_key_path, self._certificate_path)
            self._client.configureEndpoint(self._mqtt_host, self.mqtt_port)
        self._client.connect()
        self._connected = True

    def publish(self, topic, payload, qos=1):
        logging.info("publish {} {}".format(topic, payload))
        # payload needs to be in json
        if not self.connected:
            self.connect()
        self._client.publish(topic, payload, qos)


class Subscriber:
    def __init__(self, end_point, root_ca_path, certificate_path, private_key_path,
                 thing_name=None, group_ca_path=None, mqtt_host=None, mqtt_port=8883):
        self._end_point = end_point
        self._root_ca_path = root_ca_path
        self._certificate_path = certificate_path
        self._private_key_path = private_key_path
        self._thing_name = thing_name
        self._group_ca_path = group_ca_path
        self._connected = False
        self._client = AWSIoTMQTTClient(None)
        self._mqtt_host = mqtt_host
        self._mqtt_port = mqtt_port
        self._discoverer = Discoverer(self._end_point, self._root_ca_path, self._certificate_path,
                                      self._private_key_path, self._group_ca_path)

    @property
    def connected(self):
        return self._connected

    @property
    def mqtt_host(self):
        return self._mqtt_host

    @property
    def mqtt_port(self):
        return self._mqtt_port

    def connect(self):
        # use the presence of group_ca_path to determine if local or cloud
        logging.info("subscriber connect {}".format(self._end_point))
        if self._group_ca_path is None:
            self._client.configureCredentials(self._root_ca_path, self._private_key_path, self._certificate_path)
            self._client.configureEndpoint(self._end_point, 8883)
        else:
            if self._mqtt_host is None:
                self._discoverer.discover(self._thing_name)
                # Iterate through all connection options for the greengrass core and use the first successful one
                for connectivityInfo in self._discoverer.core.connectivityInfoList:
                    current_host = connectivityInfo.host
                    current_port = connectivityInfo.port
                    self._client.configureEndpoint(current_host, current_port)
                    if self._client.connect():
                        self._mqtt_host = current_host
                        self._mqtt_port = current_port
                        break
                if not self._discoverer.discovered:
                    raise RuntimeError("No hosts discovered")
            self._client.configureCredentials(self._group_ca_path, self._private_key_path, self._certificate_path)
            self._client.configureEndpoint(self._mqtt_host, self.mqtt_port)
        self._client.connect()
        self._connected = True

    def subscribe(self, topic, callback, qos=1):
        logging.info("subscribe {}".format(topic))
        if not self.connected:
            self.connect()
        self._client.subscribe(topic, qos, callback)
