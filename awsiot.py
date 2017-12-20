import os
import subprocess as sp
import logging
import json
import argparse
import datetime
import boto3
from boto3.dynamodb.conditions import Key
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from AWSIoTPythonSDK.core.greengrass.discovery.providers import DiscoveryInfoProvider
from AWSIoTPythonSDK.core.protocol.connection.cores import ProgressiveBackOffCore
from AWSIoTPythonSDK.exception.AWSIoTExceptions import DiscoveryInvalidRequestException

MAX_DISCOVERY_RETRIES = 10
LOG_FILE = '/var/log/iot.log'
STATE = 'state'
REPORTED = 'reported'
DESIRED = 'desired'
MESSAGE = 'message'
THING_SHADOW = "$aws/things/{}/shadow/update"
LOG_FORMAT = '%(asctime)s %(filename)-15s %(funcName)-15s %(levelname)-8s %(message)s'
DATE_FORMAT = '%Y/%m/%d %-I:%M %p %Z'
FILE_DATE_FORMAT = '%Y-%m-%d-%H-%M-%S'
TOPIC_STATUS_ON = ['1', 'on']
TOPIC_STATUS_OFF = ['0', 'off']
TOPIC_STATUS_TOGGLE = ['toggle']
TOPIC_STATUS_PULSE = ['blink', 'pulse']


def file_timestamp_string(timestamp=datetime.datetime.now()):
    return timestamp.strftime(FILE_DATE_FORMAT)


def timestamp_string(timestamp=datetime.datetime.now()):
    return timestamp.strftime(DATE_FORMAT)


def os_execute(s):
    """Returns string result of os call"""
    try:
        result = sp.check_output(s.split()).rstrip('\n')
        return result
    except Exception as ex:
        return None


def os_execute_shell(s):
    """Returns string result of os call"""
    try:
        result = sp.check_output([s], shell=True).rstrip('\n')
        return result
    except Exception as ex:
        return None


def tagify(arr, field):
    o = []
    for i in arr:
        if field in i:
            o.append(i[field])
    return '+'.join(o)


def int_val(s):
    try:
        return int(s)
    except ValueError:
        return None


def float_val(s):
    try:
        return float(s)
    except ValueError:
        return None


def convert_celsius_to_fahrenheit(c):
    return 9.0 / 5.0 * c + 32


def camel_case(s):
    s = s.title().replace(' ', '').replace('\t', '').replace('\n', '')
    return s[0].lower() + s[1:]


def is_locked(filepath):
    """Checks if a file is locked by opening it in append mode.
    If no exception thrown, then the file is not locked.
    """
    locked = None
    if os.path.exists(filepath):
        try:
            os.rename(filepath, filepath)
            locked = False
        except OSError as ex:
            locked = True
            logging.warning("file locked {} {}".format(filepath, ex.message))
    return locked


def s3_tag(file_name, bucket, tags=None, s3=None):
    if s3 is None:
        s3 = boto3.resource('s3')
    t = s3.meta.client.get_object_tagging(Bucket=bucket, Key=file_name)['TagSet']
    if tags is not None:
        for k, v in tags.items():
            t.append({'Key': k.strip(), 'Value': v.strip()})
        s3.meta.client.put_object_tagging(Bucket=bucket, Key=file_name, Tagging={'TagSet': t})


def mv_to_s3(file_name, bucket, tags=None):
    s3 = boto3.resource('s3')
    s3.meta.client.upload_file(file_name, bucket, file_name)
    # if collection is not None:
    #     client = boto3.client('rekognition')
    #     result = client.detect_labels(Image={'S3Object': {'Bucket': bucket, 'Name': file_name}},
    #                                   MinConfidence=confidence)
    #     if "Labels" in result:
    #         tags['recognize'] = tagify(result['Labels'], 'Name')
    #         if 'People' in tags['recognize'].split('+') or 'Person' in tags['recognize'].split('+'):
    #             try:
    #                 result = client.search_faces_by_image(Image={"S3Object": {"Bucket": bucket, "Name": file_name, }},
    #                                                       CollectionId=collection)
    #                 table = boto3.resource('dynamodb').Table('faces')
    #                 hits = {}
    #                 for i in result['FaceMatches']:
    #                     record = table.query(KeyConditionExpression=Key('id').eq(i['Face']['FaceId']))['Items']
    #                     if len(record) > 0:
    #                         if record[0]['name'] in hits:
    #                             hits[record[0]['name']] += 1
    #                         else:
    #                             hits[record[0]['name']] = 1
    #                 if len(hits) > 0:
    #                     tags['identities'] = '+'.join(hits)
    #             except Exception as e:
    #                 logging.warning("identify error: {}".format(e.message))
    t = []
    if tags is not None:
        for k, v in tags.items():
            t.append({'Key': k.strip(), 'Value': v.strip()})
        s3.meta.client.put_object_tagging(Bucket=bucket, Key=file_name, Tagging={'TagSet': t})
    rm(file_name)


def rm(file_name):
    try:
        os.remove(file_name)
    except OSError, e:
        logging.error("Failed to remove {}: {}".format(e.filename, e.strerror))


def recognize(file_name, bucket, confidence=75):
    has_person = False
    client = boto3.client('rekognition')
    result = client.detect_labels(Image={'S3Object': {'Bucket': bucket, 'Name': file_name}}, MinConfidence=confidence)
    if "Labels" in result:
        x = tagify(result['Labels'], 'Name')
        s3_tag(file_name, bucket, {'recognize': x})
        if 'People' in x.split('+') or 'Person' in x.split('+'):
            has_person = True
    return has_person


def identify(collection, file_name, bucket):
    client = boto3.client('rekognition')
    try:
        result = client.search_faces_by_image(Image={"S3Object": {"Bucket": bucket, "Name": file_name, }},
                                              CollectionId=collection)
        table = boto3.resource('dynamodb').Table('faces')
        hits = {}
        for i in result['FaceMatches']:
            record = table.query(KeyConditionExpression=Key('id').eq(i['Face']['FaceId']))['Items']
            if len(record) > 0:
                if record[0]['name'] in hits:
                    hits[record[0]['name']] += 1
                else:
                    hits[record[0]['name']] = 1
        if len(hits) > 0:
            s3_tag(file_name, bucket, {'identities': '+'.join(hits)})
    except Exception as e:
        logging.warning("identify error: {}".format(e.message))


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
                logging.debug("discovery backoff...")
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
        logging.debug("publisher connect {}".format(self._end_point))
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
        logging.debug("subscriber connect {}".format(self._end_point))
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
