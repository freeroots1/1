import redis
import json
import time

# Redis配置
REDIS_CONF = {"host": "localhost", "port": 6379, "db": 0}
REDIS_TASK_KEY = "xiaozhi:tasks"


def publish_test_task():
    """推送测试任务到Redis"""
    redis_client = redis.StrictRedis(**REDIS_CONF)

    task = {
        "device_id": "huishi001",
        "user_id": "test_user_001",
        "url_bin": "http://example.com/test.bin",
        "image_path": "/test/image.jpg",
        "md5": "5d41402abc4b2a76b9719d911017c592",
        "size": 1024
    }

    task_json = json.dumps(task)
    redis_client.lpush(REDIS_TASK_KEY, task_json)
    print(f"Task published to Redis: {task_json}")


if __name__ == "__main__":
    publish_test_task()