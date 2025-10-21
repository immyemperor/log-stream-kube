from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from kafka import KafkaConsumer
from sqlalchemy import create_engine, Column, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import UUID
import threading
import os
import json
import uuid
import time
import logging
import sys
import multiprocessing

# --- Database Setup ---
db_user = os.environ.get("POSTGRES_USER")
db_password = os.environ.get("POSTGRES_PASSWORD")
db_host = os.environ.get("POSTGRES_HOST")
db_name = os.environ.get("POSTGRES_DB")
from graypy import GELFUDPHandler 
from prometheus_flask_exporter import PrometheusMetrics

# --- Graylog Configuration ---
# Read configuration from environment variables for containerization
# The host will be the Docker service name ('graylog')
GRAYLOG_HOST = os.environ.get('GRAYLOG_HOST', 'localhost') 
GRAYLOG_PORT = int(os.environ.get('GRAYLOG_PORT', 12201)) # Convert port to integer

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


# Wait for the database to be ready
def wait_for_db():
    print("Waiting for database...")
    while True:
        try:
            engine = create_engine(f'postgresql://{db_user}:{db_password}@{db_host}/{db_name}')
            engine.connect()
            print("Database is ready!")
            return engine
        except Exception as e:
            print(f"Database connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)

# engine = wait_for_db()
# Session = sessionmaker(bind=engine)
# Base = declarative_base()

# class Message(Base):
#     __tablename__ = 'messages'
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     content = Column(Text, nullable=False)
    
#     def encode(obj):
#         if isinstance(obj,Message):
#             return {"id": obj.id, "message": obj.content}
#         raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

# # Drop all tables defined in Base.metadata
# Base.metadata.drop_all(engine) 
# print("All tables dropped.")

# --- Kafka Consumer Logic ---
kafka_broker = os.environ.get("KAFKA_BROKER", "localhost:9092")



# consumer_process = multiprocessing.Process(target=kafka_broker, args=('one',))
# consumer_process.start()
# consumer_process.join()
# print("Kafka consumer process running")



# --- Flask App ---
app = Flask(__name__)
metrics = PrometheusMetrics(app)
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_password}@{db_host}/{db_name}' # Or your specific database URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<Message {self.id} {self.content}>'
    def to_json(self):
        return {"id": self.id, "message":self.content}

def kafka_listener(app):
    with app.app_context():
        consumer = KafkaConsumer(
            os.environ.get('KAFKA_SOURCE_TOPIC'),
            bootstrap_servers=[kafka_broker],
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='my-consumer-group',
            value_deserializer=lambda v: json.loads(v.decode('utf-8'))
        )
        # This should print when the thread starts executing the function
        logger.info("🥳 Kafka consumer is running...")
        
        for message in consumer:
            try:
                data = message.value
                logger.info(f"Received message: {data}")
                
                # Start database transaction
                new_message = Message(id=uuid.UUID(data['id']), content=data['content'])
                db.session.add(new_message)
                
                try:
                    # Commit the transaction to the database
                    db.session.commit()
                    logger.info("Message stored in database.")
                except Exception as db_error:
                    # Rollback the session if the commit fails
                    db.session.rollback()
                    logger.error(f"Database error during commit: {db_error}")

            except Exception as e:
                # This catches issues with deserialization, data access (e.g., data['id']), etc.
                logger.error(f"❌ Error processing message: {e} - Message offset: {message.offset}")

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

def fetch_data_generator():
        all_messages = Message.query.all()
        logger.debug(f"all messages: {all_messages}")
        for msg in all_messages:
            # Process the row if needed (e.g., convert to JSON)
            yield msg # Example: yield each row as a string followed by a newline

logger.info("Setting up kafka consumer thread.")
listener_thread = threading.Thread(target=kafka_listener, args=(app,))
listener_thread.daemon = False
logger.info("Kafka consumer thread setup completed.")
logger.info("Kafka consumer starting up...")
listener_thread.start()
logger.info("Kafka consumer thread joinig.")
listener_thread.join()
logger.info("Kafka consumer started successfully.")

@app.route('/')
def index():
    msg = fetch_data_generator()
    return {'msg': list(msg)}

if __name__ == '__main__':
    # Start the Kafka listener in a separate thread
    with app.app_context():
        logger.info("Dropping all tables...")
        db.drop_all()
        logger.info("Recreating all tables...")
        db.create_all()
        logger.info("Database recreated successfully.")
        logger.info("Message table created successfully.")
    logger.info("Flask consumer application starting up...")
    # The default Flask logging system is disabled to prevent duplicate output
    # since we are using our custom logger (logger.addHandler(stream_handler)).
    app.run(debug=True)
    logger.info("Flask application started successfully.")
