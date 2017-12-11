import os
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
        self._coreInfo = None
        self._connected = False
        self._discovered = False
        self._client = AWSIoTMQTTClient(thing_name)
        self._caList = None
        self._coreList = None

    @property
    def end_point(self):
        return self._end_point

    @property
    def thing_name(self):
        return self._thing_name

    @property
    def private_key_path(self):
        return self._private_key_path

    @property
    def certificate_path(self):
        return self._certificate_path

    @property
    def root_ca_path(self):
        return self._root_ca_path

    @property
    def group_ca_path(self):

        return self._group_ca_path

    @property
    def connected(self):
        return self._connected

    @property
    def discovered(self):
        return self._discovered

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
                self._caList = di.getAllCas()
                self._coreList = di.getAllCores()
                # We only pick the first ca and core info
                group_id, ca = self._caList[0]
                core_info = self._coreList[0]
                print("Discovered GGC: %s from Group: %s" % (core_info.coreThingArn, group_id))
                if os.path.isfile(self._group_ca_path):
                    print("Now we persist the connectivity/identity information...")
                    group_ca_file = open(self._group_ca_path, "w")
                    group_ca_file.write(ca)
                    group_ca_file.close()
                self._discovered = True
                print("Now proceed to the connecting flow...")
                break
            except DiscoveryInvalidRequestException as e:
                print("Invalid discovery request detected!")
                print("Type: %s" % str(type(e)))
                print("Error message: %s" % e.message)
                print("Stopping...")
                break
            except BaseException as e:
                print("Error in discovery!")
                print("Type: %s" % str(type(e)))
                print("Error message: %s" % e.message)
                retry_count -= 1
                print("\n{}/{} retries left\n".format(retry_count, MAX_DISCOVERY_RETRIES))
                print("Backing off...\n")
                backoff_core.backOff()
        if not self._discovered:
            raise RuntimeError("Discovery failed after {} retries".format(MAX_DISCOVERY_RETRIES))

    def connect(self):
        # Iterate through all connection options for the core and use the first successful one
        self._client.configureCredentials(self.group_ca_path, self.private_key_path, self.certificate_path)
        for connectivityInfo in self._coreInfo.connectivityInfoList:
            current_host = connectivityInfo.host
            current_port = connectivityInfo.port
            print("Trying to connect to core at {}:{}".format(current_host, current_port))
            self._client.configureEndpoint(current_host, current_port)
            self._client.connect()
            self._connected = True

    def publish(self, topic, payload, qos=0):
        if not self.discovered:
            self.discover()
        if not self.connected:
            self.connect()
        return self._client.publish(topic, payload, qos)


class Subscriber:
    def __init__(self):
        print("init")
