from flask import Flask, request, jsonify
from flask_cors import CORS
from kafka import KafkaProducer
import os
import json
import uuid
import logging
import sys

from graypy import GELFUDPHandler 
from prometheus_flask_exporter import PrometheusMetrics
from pydantic import BaseModel, ValidationError

# --- Graylog Configuration ---
# Read configuration from environment variables for containerization
# The host will be the Docker service name ('graylog')
GRAYLOG_HOST = os.environ.get('GRAYLOG_HOST', 'localhost') 
GRAYLOG_PORT = int(os.environ.get('GRAYLOG_PORT', 12201)) # Convert port to integer
# KAFKA_BROKER= 'http://localhost:29092'
# KAFKA_SINK_TOPIC= 'test_topic'

# --- 1. Logging Configuration ---
# 1.1. Create a custom logger object
logger = logging.getLogger('FlaskLogGenerator')
logger.setLevel(logging.DEBUG)

# 1.2. Define Log Format (for console/file, GELF handler has its own format)
formatter = logging.Formatter(
    '[%(asctime)s] - %(levelname)s - %(name)s - %(message)s', 
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 1.3. File Handler: Writes logs to 'app.log' (Level: INFO and above)
file_handler = logging.FileHandler('app.log')
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)

# 1.4. Console Handler: Writes logs to stdout (Level: DEBUG and above)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.DEBUG)
logger.addHandler(stream_handler)

# 1.5. Graylog Handler: Writes logs to Graylog (Level: INFO and above)
try:
    # Use environment variables for connection
    gelf_handler = GELFUDPHandler(GRAYLOG_HOST, GRAYLOG_PORT, localname='flask-app')
    gelf_handler.setLevel(logging.INFO) # Only send INFO, WARNING, ERROR, CRITICAL to Graylog
    logger.addHandler(gelf_handler)
    logger.info(f"Graylog GELF handler successfully configured for {GRAYLOG_HOST}:{GRAYLOG_PORT}")
except Exception as e:
    logger.error(f"Failed to configure Graylog handler: {e}. Logs will not be forwarded to Graylog.")


app = Flask(__name__)
CORS(app)
kafka_broker = os.environ.get("KAFKA_BROKER", "localhost:9092")

# Create Kafka producer
producer = KafkaProducer(
    bootstrap_servers=[kafka_broker],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

metrics = PrometheusMetrics(app)

# static information as metric
metrics.info('app_info', 'Application info', version='1.0.3')

# Map log level names to the actual logger methods
LOG_LEVEL_MAP = {
    'DEBUG': logger.debug,
    'INFO': logger.info,
    'WARNING': logger.warning,
    'ERROR': logger.error,
    'CRITICAL': logger.critical,
}

@app.route('/produce', methods=['POST'])
def send_message():
    data = request.json
    if not data:
        logger.critical("No data provided")
        return jsonify({"error": "Missing data"}), 400
    
    # Add a unique ID to the message payload
    message_payload = {"id": str(uuid.uuid4()), "content": data.get("message")}
    logger.info(f"message created: {message_payload}")
    
    # Send the message to the 'events' topic
    producer.send(os.environ.get('KAFKA_SINK_TOPIC'), message_payload)
    producer.flush()  # Ensure message is sent
    logger.info(f"message sent: {message_payload}")
    return jsonify({"message": "Message sent to Kafka", "payload": message_payload}), 200

class MessagePost(BaseModel):
    sender_id: str
    content: str
    created_at: str
    read_at: str
    is_delivered: bool
    is_read: bool
    sender_name: str
    

@app.route('/send_message',methods=["POST"])
def send_msg():
    try:
        data = request.json
        logger.info(f"Message data: {data}")
        logger.info(f"Validating Message: {data}")
        msg_data = MessagePost(**data)
        if msg_data:
            st = [f'{key}#{val}' for key,val in data.items()]
            data = "##".join(st)
            logger.info(f"Message data str: {data}")
            message_payload = {"id": str(uuid.uuid4()), "content": data}
            logger.info(f"Message created: {message_payload}")
            
            # Send the message to the 'events' topic
            producer.send(os.environ.get('KAFKA_SINK_TOPIC'), message_payload)
            producer.flush()  # Ensure message is sent
            logger.info(f"Message sent: {message_payload}")
            return jsonify({"message": "Message sent to Kafka", "payload": message_payload}), 200
        else:
            logger.critical("No data provided")
            return jsonify({"error": "Missing data"}), 400
    except ValidationError as e:
            # Handle validation errors
            logger.exception(f"Message Validation Error: {e.errors()}")
            return jsonify({"error": e.errors()}), 400
    except Exception as e:
            # Handle other potential errors
            logger.exception(f"Exception Occured: {e}")
            return jsonify({"error": str(e)}), 500
    

if __name__ == '__main__':
    logger.info("Flask producer application starting up...")
    
    # The default Flask logging system is disabled to prevent duplicate output
    # since we are using our custom logger (logger.addHandler(stream_handler)).
    app.run(debug=True, port=5004)
