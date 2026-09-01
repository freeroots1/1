import paho.mqtt.client as mqtt
import json
import time
import logging
from datetime import datetime

# --- 配置参数 ---
MQTT_CONF = {
    "host": "localhost",
    "port": 1883,
    "keepalive": 60,
    "username": "huishi",
    "password": "huishizn@709"
}
DEVICE_ID = "huishi001"  # 测试设备ID


# --- 配置日志 ---
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


class MqttTestSub:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.device_id = DEVICE_ID

        # 初始化MQTT
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.username_pw_set(MQTT_CONF["username"], MQTT_CONF["password"])
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect

        # 设备状态
        self.is_online = True

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info("Connected to MQTT Broker successfully")

            # 订阅任务topic
            task_topic = f"xiaozhi/{self.device_id}/task"
            self.mqtt_client.subscribe(task_topic)
            self.logger.info(f"Subscribed to task topic: {task_topic}")

            # 发布上线状态
            self.publish_status("online")
        else:
            self.logger.error(f"Failed to connect with code {rc}")

    def on_disconnect(self, client, userdata, rc):
        """MQTT断开连接回调"""
        if rc != 0:
            self.logger.warning(f"Unexpected MQTT disconnection, code: {rc}")
        else:
            self.logger.info("MQTT disconnected")

    def on_message(self, client, userdata, msg):
        """处理接收到的MQTT消息"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            self.logger.info(f"Received message - Topic: {topic}, Payload: {payload}")

            # 解析任务
            if "task" in topic:
                task_data = json.loads(payload)
                self.logger.info(f"📥 Received task: {task_data}")

                # 模拟处理任务
                self.process_task(task_data)

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode JSON: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")

    def process_task(self, task_data):
        """模拟处理任务"""
        self.logger.info("=" * 50)
        self.logger.info("Processing task:")
        self.logger.info(f"  - url_bin: {task_data.get('url_bin')}")
        self.logger.info(f"  - image_path: {task_data.get('image_path')}")
        self.logger.info(f"  - md5: {task_data.get('md5')}")
        self.logger.info(f"  - size: {task_data.get('size')} bytes")
        self.logger.info("=" * 50)

        # 模拟任务处理时间
        time.sleep(2)
        self.logger.info("✓ Task processing completed")

    def publish_status(self, status):
        """发布设备状态"""
        topic = f"device/{self.device_id}/status"
        payload = {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "device_id": self.device_id
        }
        payload_json = json.dumps(payload)

        result = self.mqtt_client.publish(topic, payload_json, qos=1, retain=True)

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            self.logger.info(f"📡 Published status: {status} to {topic}")
        else:
            self.logger.error(f"Failed to publish status: {status}")

    def run(self):
        """运行测试客户端"""
        try:
            # 连接MQTT
            self.mqtt_client.connect(MQTT_CONF["host"], MQTT_CONF["port"], MQTT_CONF["keepalive"])
            self.mqtt_client.loop_start()

            self.logger.info(f"Test device [{self.device_id}] is running...")
            self.logger.info("Press Ctrl+C to exit")

            # 定期发送心跳
            heartbeat_count = 0
            try:
                while True:
                    time.sleep(30)  # 每30秒发送一次心跳
                    heartbeat_count += 1

                    # 发送心跳状态
                    if self.is_online:
                        self.publish_status("heartbeat")
                        self.logger.debug(f"Heartbeat #{heartbeat_count} sent")

            except KeyboardInterrupt:
                self.logger.info("\nStopping test device...")

        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
        finally:
            # 发布离线状态
            self.publish_status("offline")
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.logger.info("Test device stopped")


if __name__ == "__main__":
    logger = setup_logging()

    logger.info("=" * 60)
    logger.info("Starting MQTT Test Subscriber")
    logger.info(f"Device ID: {DEVICE_ID}")
    logger.info("=" * 60)

    test_client = MqttTestSub(logger=logger)
    test_client.run()
