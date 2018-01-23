import logging
import time
import json
import uuid

# Setup logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

SAMPLE_APPLIANCES = {
    "endpoints":
        [
            {
                "endpointId": "demo_id",
                "manufacturerName": "Smart Device Company",
                "friendlyName": "Bedroom Outlet",
                "description": "Smart Device Switch",
                "displayCategories": ["SWITCH"],
                "cookie": {
                    "key1": "arbitrary key/value pairs for skill to reference this endpoint.",
                    "key2": "There can be multiple entries",
                    "key3": "but they should only be used for reference purposes.",
                    "key4": "This is not a suitable place to maintain current endpoint state."
                },
                "capabilities":
                    [
                        {
                            "type": "AlexaInterface",
                            "interface": "Alexa",
                            "version": "3"
                        },
                        {
                            "interface": "Alexa.PowerController",
                            "version": "3",
                            "type": "AlexaInterface",
                            "properties": {
                                "supported": [{
                                    "name": "powerState"
                                }],
                                "retrievable": True
                            }
                        }
                    ]
            }
        ]
}


def lambda_handler(request, context):
    try:
        logger.info("Directive:")
        logger.info(json.dumps(request, indent=4, sort_keys=True))

        if request["directive"]["header"]["name"] == "Discover":
            response = handle_discovery(request)
        else:
            response = handle_non_discovery(request)
        return response
    except ValueError as error:
        logger.error(error)
        raise


def get_utc_timestamp(seconds=None):
    return time.strftime("%Y-%m-%dT%H:%M:%S.00Z", time.gmtime(seconds))


def get_uuid():
    return str(uuid.uuid4())


def handle_discovery(request):
    endpoints = []
    response = {
        "event": {
            "header": {
                "namespace": "Alexa.Discovery",
                "name": "Discover.Response",
                "payloadVersion": "3",
                "messageId": get_uuid()
            },
            "payload": SAMPLE_APPLIANCES
        }
    }
    return response


def handle_non_discovery(request):
    request_namespace = request["directive"]["header"]["namespace"]
    request_name = request["directive"]["header"]["name"]

    if request_namespace == "Alexa.PowerController":
        if request_name == "TurnOn":
            value = "ON"
        else:
            value = "OFF"
        response = {
            "context": {
                "properties": [
                    {
                        "namespace": "Alexa.PowerController",
                        "name": "powerState",
                        "value": value,
                        "timeOfSample": get_utc_timestamp(),
                        "uncertaintyInMilliseconds": 500
                    }
                ]
            },
            "event": {
                "header": {
                    "namespace": "Alexa",
                    "name": "Response",
                    "payloadVersion": "3",
                    "messageId": get_uuid(),
                    "correlationToken": request["directive"]["header"]["correlationToken"]
                },
                "endpoint": {
                    "scope": {
                        "type": "BearerToken",
                        "token": "access-token-from-Amazon"
                    },
                    "endpointId": request["directive"]["endpoint"]["endpointId"]
                },
                "payload": {}
            }
        }
        return response
    elif request_namespace == "Alexa.Authorization":
        if request_name == "AcceptGrant":
            response = {
                "event": {
                    "header": {
                        "namespace": "Alexa.Authorization",
                        "name": "AcceptGrant.Response",
                        "payloadVersion": "3",
                        "messageId": "5f8a426e-01e4-4cc9-8b79-65f8bd0fd8a4"
                    },
                    "payload": {}
                }
            }
            return response
