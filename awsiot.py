import os
import subprocess as sp
import logging
import json
import argparse
import datetime
import boto3
import platform
import time
from boto3.dynamodb.conditions import Key
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

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


def topic_search(topic, input):
    topics = tokenizer(topic, '/')
    for i in topics:
        if input.startswith(i):
            temp = filter(None, input.replace(i, '').split('/'))
            command = None
            if len(temp) > 0:
                command = temp.pop(0)
            arg = None
            if len(temp) > 0:
                arg = temp.pop(0)
            if command:
                sup = command
                if arg:
                    sup = '{}/{}'.format(command, arg)
                if input in tokenizer(topic, '/', sup):
                    return command, arg
            return None, None


def tokenizer(s, c, suffix=None):
    tmp_list = s.split(c)
    res = []
    while len(tmp_list) > 0:
        if suffix:
            res.append("{}{}{}".format(c.join(tmp_list), c, suffix))
        else:
            res.append("{}".format(c.join(tmp_list)))
        tmp_list.pop()
    return res


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
    t = []
    if tags is not None:
        for k, v in tags.items():
            t.append({'Key': k.strip(), 'Value': v.strip()})
        s3.meta.client.put_object_tagging(Bucket=bucket, Key=file_name, Tagging={'TagSet': t})
    rm(file_name)


def rm(file_name):
    try:
        os.remove(file_name)
    except OSError as e:
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
    parser.add_argument("-t", "--topic", nargs='*', help="MQTT topic(s)")
    parser.add_argument("-l", "--log_level", help="Log Level", default=logging.INFO)
    parser.add_argument("--thing", help="thing name", default=platform.node().split('.')[0])
    return parser


class MQTT:
    def __init__(self, end_point, root_ca_path, certificate_path, private_key_path):
        self._end_point = end_point
        self._root_ca_path = root_ca_path
        self._certificate_path = certificate_path
        self._private_key_path = private_key_path
        self._client = AWSIoTMQTTClient(None)
        self._client.configureCredentials(self._root_ca_path, self._private_key_path, self._certificate_path)
        self._client.configureEndpoint(self._end_point, 8883)
        self._client.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
        self._client.configureDrainingFrequency(2)  # Draining: 2 Hz
        self._client.configureConnectDisconnectTimeout(10)  # 10 sec
        self._client.configureMQTTOperationTimeout(5)  # 5 sec
        self._client.onOnline = self.online_callback
        self._client.onOffline = self.offline_callback
        self._connected = False

    def online_callback(self):
        logging.info("mqtt online")
        self._connected = True

    def offline_callback(self):
        logging.info("mqtt offline")
        self._connected = False

    def publish_callback(self):
        logging.info("mqtt published")

    @property
    def connected(self):
        return self._connected

    def connect(self):
        # use the presence of group_ca_path to determine if local or cloud
        if not self._connected:
            logging.debug("mqtt connect {}".format(self._end_point))
            self._client.connect()

    def publish(self, topic, payload, qos=1):
        logging.info("mqtt publish {} {}".format(topic, payload))
        self.connect()
        try:
            self._client.publishAsync(topic, payload, qos, ackCallback=self.publish_callback)
        except Exception as e:
            logging.error("mqtt publish {} {} error: {}".format(topic, payload, e.message))

    def subscribe(self, topic, callback, qos=1):
        logging.info("mqtt subscribe {}".format(topic))
        self.connect()
        try:
            self._client.subscribe(topic, qos, callback)
        except Exception as e:
            logging.error("mqtt subscribe {} error: {}".format(topic, e.message))

    def disconnect(self):
        self._connected = False
        return self._client.disconnect()
