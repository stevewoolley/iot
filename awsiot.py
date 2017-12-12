import os
import logging
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from AWSIoTPythonSDK.core.greengrass.discovery.providers import DiscoveryInfoProvider
from AWSIoTPythonSDK.core.protocol.connection.cores import ProgressiveBackOffCore
from AWSIoTPythonSDK.exception.AWSIoTExceptions import DiscoveryInvalidRequestException

MAX_DISCOVERY_RETRIES = 10


class Discoverer:
    def __init__(self, end_point, root_ca_path, certificate_path, private_key_path, group_ca_path):
        self._end_point = end_point
        self._root_ca_path = root_ca_path
        self._certificate_path = certificate_path
        self._private_key_path = private_key_path
        self._group_ca_path = group_ca_path
        self._cores = None
        self._discovered = False
        self._log_level = logging.WARNING

    @property
    def discovered(self):
        return self._discovered

    @property
    def cores(self):
        return self._cores

    @property
    def log_level(self):
        return self._log_level

    @log_level.setter
    def log_level(self, value):
        self._log_level = value

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
            logging.info("Discovery...")
            try:
                di = dip.discover(thing)
                ca_list = di.getAllCas()
                self._cores = di.getAllCores()
                # We only pick the first ca and core info
                group_id, ca = ca_list[0]
                logging.info("Discovered GGC: {} from Group: {}".format(self.core.coreThingArn, group_id))
                if not os.path.isfile(self._group_ca_path):
                    group_ca_file = open(self._group_ca_path, "w")
                    group_ca_file.write(ca)
                    group_ca_file.close()
                self._discovered = True
                break
            except DiscoveryInvalidRequestException as e:
                logging.error("Discovery Invalid Request: {}".format(e.message))
                break
            except BaseException as e:
                retry_count -= 1
                logging.info("Discovery Backoff...")
                backoff_core.backOff()
        if not self._discovered:
            raise RuntimeError("Discovery Failed")


class Publisher:
    def __init__(self, end_point, root_ca_path, certificate_path, private_key_path, thing_name=None, group_ca_path=None,
                 mqtt_host=None, mqtt_port=8883):
        self._end_point = end_point
        self._thing_name = thing_name
        self._private_key_path = private_key_path
        self._certificate_path = certificate_path
        self._root_ca_path = root_ca_path
        self._group_ca_path = group_ca_path
        self._connected = False
        self._log_level = logging.WARNING
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

    @property
    def log_level(self):
        return self._log_level

    @log_level.setter
    def log_level(self, value):
        self._log_level = value

    def connect(self):
        # use the presence of group_ca_path to determine if local or cloud
        if self._group_ca_path is None:
            logging.info("Trying connect to AWS IoT: {}".format(self._end_point))
            self._client.configureCredentials(self._root_ca_path, self._private_key_path, self._certificate_path)
            self._client.configureEndpoint(self._end_point, 8883)
        else:
            if self._mqtt_host is None:
                self._discoverer.discover(self._thing_name)
                # Iterate through all connection options for the greengrass core and use the first successful one
                for connectivityInfo in self._discoverer.core.connectivityInfoList:
                    current_host = connectivityInfo.host
                    current_port = connectivityInfo.port
                    logging.info("Trying to connect to core at {}:{}".format(current_host, current_port))
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
        # payload needs to be in json
        if not self.connected:
            self.connect()
        logging.info("Publishing {} to {}".format(payload, topic))
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
        self._log_level = logging.WARNING
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

    @property
    def log_level(self):
        return self._log_level

    @log_level.setter
    def log_level(self, value):
        self._log_level = value

    def connect(self):
        # use the presence of group_ca_path to determine if local or cloud
        if self._group_ca_path is None:
            logging.info("Trying connect to AWS IoT: {}".format(self._end_point))
            self._client.configureCredentials(self._root_ca_path, self._private_key_path, self._certificate_path)
            self._client.configureEndpoint(self._end_point, 8883)
        else:
            if self._mqtt_host is None:
                self._discoverer.discover(self._thing_name)
                # Iterate through all connection options for the greengrass core and use the first successful one
                for connectivityInfo in self._discoverer.core.connectivityInfoList:
                    current_host = connectivityInfo.host
                    current_port = connectivityInfo.port
                    logging.info("Trying to connect to core at {}:{}".format(current_host, current_port))
                    self._client.configureEndpoint(current_host, current_port)
                    if self._client.connect():
                        self._mqtt_host = current_host
                        self._mqtt_port = current_port
                        break
                if not self._discoverer.discovered:
                    raise RuntimeError("No hosts discovered")
            self._client.configureCredentials(self._group_ca_path, self._private_key_path, self._certificate_path)
            self._client.configureEndpoint(self._mqtt_host, self.mqtt_port)
        result = self._client.connect()
        logging.info("Connected result: {}".format(result))
        self._connected = True

    def subscribe(self, topic, callback, qos=1):
        if not self.connected:
            self.connect()
        self._client.subscribe(topic, qos, callback)
