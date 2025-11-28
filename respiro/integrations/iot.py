"""AWS IoT Core integration."""
from typing import Dict, Any, Optional
import json
import boto3
from botocore.exceptions import ClientError
from respiro.config.settings import get_settings
from respiro.utils.logging import get_logger

logger = get_logger(__name__)

class IoTClient:
    def __init__(self):
        settings = get_settings()
        self.endpoint = settings.iot.endpoint
        self.thing_name = settings.iot.thing_name
        self.iot_data_client = boto3.client('iot-data', endpoint_url=f"https://{self.endpoint}")
        self.iot_client = boto3.client('iot', region_name=settings.aws.region)
    
    def publish_command(self, device_id: str, command: Dict[str, Any]) -> bool:
        """Publish command to IoT device."""
        try:
            topic = f"devices/{device_id}/commands"
            response = self.iot_data_client.publish(
                topic=topic,
                qos=1,
                payload=json.dumps(command)
            )
            logger.info(f"Published command to {topic}")
            return True
        except ClientError as e:
            logger.error(f"Failed to publish command: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error publishing command: {e}")
            return False
    
    def get_device_shadow(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device shadow state."""
        try:
            response = self.iot_data_client.get_thing_shadow(
                thingName=device_id
            )
            payload = json.loads(response['payload'].read())
            return payload.get('state', {})
        except ClientError as e:
            logger.error(f"Failed to get device shadow: {e}")
            return {"desired": {}, "reported": {}}
        except Exception as e:
            logger.error(f"Unexpected error getting shadow: {e}")
            return {"desired": {}, "reported": {}}
