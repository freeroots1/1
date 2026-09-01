import redis
import paho.mqtt.client as mqtt
import json
import time
import logging
from datetime import datetime

# --- 配置参数 ---
REDIS_CONF = {"host": "localhost", "port": 6379, "db": 0}
MQTT_CONF = {
    "host": "localhost",
    "port": 1883,
    "keepalive": 60,
    "username": "huishi",
    "password": "huishizn@709"
}
REDIS_TASK_KEY = "xiaozhi:tasks"  # 全局任务队列键名
REDIS_STATUS_KEY_PREFIX = "status"  # 设备状态Redis键前缀


# --- 配置日志 ---
def setup_logging():
    """配置日志格式和输出"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(),  # 输出到控制台
        ]
    )
    return logging.getLogger(__name__)


class XiaozhiMqttGateway:
    def __init__(self, logger=None):
        # 初始化日志
        self.logger = logger or logging.getLogger(__name__)

        # 初始化 Redis
        self.redis_client = redis.StrictRedis(**REDIS_CONF)
        self.logger.info(f"Redis connected: {REDIS_CONF['host']}:{REDIS_CONF['port']}")

        # 初始化 MQTT
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.username_pw_set(MQTT_CONF["username"], MQTT_CONF["password"])
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message  # 添加消息回调
        self.mqtt_client.on_publish = self.on_publish
        self.mqtt_client.on_disconnect = self.on_disconnect

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info(f"Connected to MQTT Broker successfully")

            # 订阅所有设备的status主题
            status_topic = "device/+/status"
            self.mqtt_client.subscribe(status_topic)
            self.logger.info(f"Subscribed to: {status_topic}")
        else:
            self.logger.error(f"Failed to connect to MQTT Broker with result code {rc}")

    def on_message(self, client, userdata, msg):
        """处理接收到的MQTT消息"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')

            # 解析topic: device/{device_id}/status
            topic_parts = topic.split('/')
            if len(topic_parts) >= 3 and topic_parts[2] == 'status':
                device_id = topic_parts[1]

                # 解析状态数据
                status_data = json.loads(payload)
                status = status_data.get("status")
                timestamp = status_data.get("timestamp", datetime.now().isoformat())

                # 存储到Redis
                redis_key = f"{REDIS_STATUS_KEY_PREFIX}:{device_id}"
                redis_value = json.dumps({
                    "status": status,
                    "timestamp": timestamp,
                    "last_update": datetime.now().isoformat()
                })

                self.redis_client.set(redis_key, redis_value)
                self.logger.info(f"📡 Device status updated - device_id: {device_id}, status: {status}, timestamp: {timestamp}")

            else:
                self.logger.warning(f"Received message from unknown topic format: {topic}")

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode JSON from {msg.topic}: {e}, payload: {msg.payload[:200]}")
        except Exception as e:
            self.logger.error(f"Error processing message from {msg.topic}: {e}", exc_info=True)

    def on_publish(self, client, userdata, mid):
        """MQTT消息发布确认回调"""
        self.logger.debug(f"Message published, message id: {mid}")

    def on_disconnect(self, client, userdata, rc):
        """MQTT断开连接回调"""
        if rc != 0:
            self.logger.warning(f"Unexpected MQTT disconnection, code: {rc}")
        else:
            self.logger.info("MQTT disconnected")

    def publish_task(self, device_id, task_data):
        """发布任务到指定设备"""
        # 构建推送给ESP32的极简Payload
        payload = {
            "url_bin": task_data.get("url_bin"),
            "image_path": task_data.get("image_path"),
            "md5": task_data.get("md5", ""),
            "size": task_data.get("size", 0)
        }

        # 发布MQTT消息
        topic = f"xiaozhi/{device_id}/task"
        payload_json = json.dumps(payload)

        # 发布并记录耗时
        publish_start = time.time()
        result = self.mqtt_client.publish(topic, payload_json, qos=1)
        publish_time = (time.time() - publish_start) * 1000

        # 记录详细日志
        self.logger.info(
            f"Publishing task - Topic: {topic} | Publish time: {publish_time:.2f}ms\n"
            f"Payload {json.dumps(payload, indent=4, ensure_ascii=False)}"
        )

        # 检查发布结果
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            self.logger.info(f"✓ Task pushed to {topic} successfully")
            return True
        else:
            self.logger.error(f"✗ Failed to publish to {topic}, error code: {result.rc}")
            return False

    def get_device_status(self, device_id):
        """从Redis获取设备状态"""
        redis_key = f"{REDIS_STATUS_KEY_PREFIX}:{device_id}"
        status_data = self.redis_client.get(redis_key)
        if status_data:
            return json.loads(status_data)
        return None

    def run(self):
        # 连接MQTT
        try:
            self.mqtt_client.connect(MQTT_CONF["host"], MQTT_CONF["port"], MQTT_CONF["keepalive"])
            self.mqtt_client.loop_start()
            self.logger.info(f"MQTT connecting to {MQTT_CONF['host']}:{MQTT_CONF['port']}")
        except Exception as e:
            self.logger.error(f"Failed to connect MQTT: {e}")
            return

        self.logger.info("Gateway is listening for Redis tasks and MQTT status messages...")
        self.logger.info(f"Redis task key: {REDIS_TASK_KEY}")
        self.logger.info(f"Redis status key prefix: {REDIS_STATUS_KEY_PREFIX}")

        task_count = 0
        try:
            while True:
                # 阻塞式监听Redis队列
                self.logger.debug("Waiting for tasks from Redis...")
                task_raw = self.redis_client.brpop(REDIS_TASK_KEY, timeout=0)

                if task_raw:
                    task_count += 1
                    try:
                        task_data = json.loads(task_raw[1].decode('utf-8'))
                        device_id = task_data.get("device_id")
                        account_id = task_data.get("account_id")

                        if not device_id:
                            self.logger.warning(f"Task missing device_id, skipping: {task_data}")
                            continue

                        # 推送任务
                        success = self.publish_task(device_id, task_data)

                        if success:
                            self.logger.info(f"[Task #{task_count}] Succeed | account_id: {account_id} | device_id: {device_id}\n")
                        else:
                            self.logger.error(f"[Task #{task_count}] Failed \n")

                    except json.JSONDecodeError as e:
                        self.logger.error(f"Failed to decode JSON: {e}, raw data: {task_raw[1][:200]}")
                    except KeyError as e:
                        self.logger.error(f"Missing required field in task data: {e}")
                    except Exception as e:
                        self.logger.error(f"Unexpected error processing task: {e}", exc_info=True)

        except KeyboardInterrupt:
            self.logger.info(f"Gateway stopping... Total tasks processed: {task_count}")
        except Exception as e:
            self.logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
        finally:
            self.logger.info("Cleaning up...")
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.logger.info("Gateway stopped")


if __name__ == "__main__":
    # 设置日志
    logger = setup_logging()

    logger.info("=" * 60)
    logger.info("Starting Xiaozhi MQTT Gateway")
    logger.info("=" * 60)

    gateway = XiaozhiMqttGateway(logger=logger)
    gateway.run()
