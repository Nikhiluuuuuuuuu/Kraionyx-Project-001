import logging
import redis
from prometheus_client import start_http_server, Counter

from .config import Config

MESSAGES_PROCESSED = Counter("stt_messages_processed_total", "Total STT messages processed")

def main():
    logging.info("Starting STT Engine")
    config = Config.from_env()

    # Prometheus metrics
    start_http_server(config.prometheus_port)
    logging.info(f"Prometheus metrics exposed on port {config.prometheus_port}")

    # Redis mTLS connection logic
    redis_kwargs = {}
    if config.redis_ssl:
        redis_kwargs.update({
            "ssl": True,
            "ssl_cert_reqs": "required",
            "ssl_ca_certs": config.redis_ssl_ca_certs,
            "ssl_certfile": config.redis_ssl_certfile,
            "ssl_keyfile": config.redis_ssl_keyfile,
        })
    redis_client = redis.Redis.from_url(config.redis_url, password=config.redis_password, **redis_kwargs)
    try:
        redis_client.ping()
        logging.info("Connected to Redis successfully.")
    except Exception as e:
        logging.warning(f"Failed to connect to Redis: {e}")

if __name__ == "__main__":
    main()
