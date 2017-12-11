import os
import logging
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from AWSIoTPythonSDK.core.greengrass.discovery.providers import DiscoveryInfoProvider
from AWSIoTPythonSDK.core.protocol.connection.cores import ProgressiveBackOffCore
from AWSIoTPythonSDK.exception.AWSIoTExceptions import DiscoveryInvalidRequestException

MAX_DISCOVERY_RETRIES = 10


class Publisher:
    def __init__(self, end_point, thing_name, private_key_path, certificate_path, root_ca_path, group_ca_path):
        self._thing_name = thing_name
        self._end_point = end_point
        self._private_key_path = private_key_path
        self._certificate_path = certificate_path
        self._root_ca_path = root_ca_path
        self._group_ca_path = group_ca_path
        self._certificate_authority = None
        self._ca = None
        self._core_info = None
        self._connected = False
        self._discovered = False
        self._log_level = logging.WARNING
        self._client = AWSIoTMQTTClient(thing_name)

    @property
    def end_point(self):
        return self._end_point

    @property
    def thing_name(self):
        return self._thing_name

    @property
    def connected(self):
        return self._connected

    @property
    def discovered(self):
        return self._discovered

    @property
    def log_level(self):
        return self._log_level

    @log_level.setter
    def log_level(self, value):
        self._log_level = value

    def discover(self):
        backoff_core = ProgressiveBackOffCore()
        dip = DiscoveryInfoProvider()
        dip.configureEndpoint(self._end_point)
        dip.configureCredentials(self._root_ca_path, self._certificate_path, self._private_key_path)
        dip.configureTimeout(10)  # 10 sec
        retry_count = MAX_DISCOVERY_RETRIES
        while retry_count != 0:
            try:
                di = dip.discover(self._thing_name)
                ca_list = di.getAllCas()
                core_list = di.getAllCores()
                # We only pick the first ca and core info
                group_id, ca = ca_list[0]
                self._core_info = core_list[0]
                logging.info("Discovered GGC: {} from Group: {}".format(self._core_info.coreThingArn, group_id))
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

    def connect(self):
        # Iterate through all connection options for the greengrass core and use the first successful one
        self._client.configureCredentials(self._group_ca_path, self._private_key_path, self._certificate_path)
        for connectivityInfo in self._core_info.connectivityInfoList:
            current_host = connectivityInfo.host
            current_port = connectivityInfo.port
            logging.info("Trying to connect to core at {}:{}".format(current_host, current_port))
            self._client.configureEndpoint(current_host, current_port)
            self._client.connect()
            self._connected = True
            break

    def publish(self, topic, payload, qos=0):
        if not self.discovered:
            self.discover()
        if not self.connected:
            self.connect()
        return self._client.publish(topic, payload, qos)


class Subscriber:
    def __init__(self):
        print("init")
