import logging
import sys
import os # Import os for environment variables
from flask import Flask, request, redirect, url_for
# Import the GELF handler
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


# --- 2. Flask Application Setup ---
app = Flask(__name__)

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

# --- 3. Routes ---

@app.route('/', methods=['GET'])
def index():
    """Renders the main interface with buttons to generate different logs."""
    
    # Simple HTML content using inline styling (similar to Tailwind for aesthetics)
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Flask Log Generator</title>
        <style>
            body {{ font-family: sans-serif; background-color: #f4f7f6; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }}
            .container {{ background: white; padding: 2.5rem; border-radius: 12px; box-shadow: 0 10px 15px rgba(0, 0, 0, 0.1); max-width: 400px; width: 90%; text-align: center; }}
            h1 {{ color: #1e40af; margin-bottom: 1.5rem; font-size: 1.5rem; font-weight: 700; }}
            p {{ color: #4b5563; margin-bottom: 2rem; }}
            .log-button {{ display: block; width: 100%; padding: 0.75rem; margin-bottom: 1rem; border-radius: 8px; font-weight: 600; cursor: pointer; transition: background-color 0.2s; border: 1px solid transparent; }}
            .log-button:hover {{ opacity: 0.9; }}
            
            .debug {{ background-color: #3b82f6; color: white; }}
            .info {{ background-color: #10b981; color: white; }}
            .warning {{ background-color: #f59e0b; color: #1e293b; }}
            .error {{ background-color: #ef4444; color: white; }}
            .critical {{ background-color: #7f1d1d; color: white; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Log Generator Control</h1>
            <p>Click a button below to generate a log entry at the selected level.</p>
            
            <a href="{ url_for('generate_log', level='DEBUG') }" class="log-button debug">Generate DEBUG Log</a>
            <a href="{ url_for('generate_log', level='INFO') }" class="log-button info">Generate INFO Log</a>
            <a href="{ url_for('generate_log', level='WARNING') }" class="log-button warning">Generate WARNING Log</a>
            <a href="{ url_for('generate_log', level='ERROR') }" class="log-button error">Generate ERROR Log</a>
            <a href="{ url_for('generate_log', level='CRITICAL') }" class="log-button critical">Generate CRITICAL Log</a>
            
            <p style="margin-top: 2rem; font-size: 0.8rem; color: #6b7280;">
                Check your console for all logs. INFO+ logs are sent to <code>app.log</code> AND to Graylog.
            </p>
        </div>
    </body>
    </html>
    """
    return html_content

@app.route('/generate_log', methods=['GET'])
def generate_log():
    """
    Generates a log entry based on the 'level' query parameter.
    """
    
    # Get the requested log level, defaulting to INFO if not specified
    level = request.args.get('level', 'INFO').upper()
    
    # Check if the requested level is valid
    if level in LOG_LEVEL_MAP:
        # Get the appropriate logging function (e.g., logger.error or logger.info)
        log_func = LOG_LEVEL_MAP[level]
        
        # Define a message for the log entry
        message = f"User triggered a log event for level: {level} via the web interface."
        
        # Execute the logging function (this triggers all attached handlers: Console, File, Graylog)
        log_func(message)
        
        # Use an HTML response for feedback instead of redirecting
        return f"""
            <div style="text-align: center; padding: 50px;">
                <h2 style="color: #10b981;">✅ Log Event Generated!</h2>
                <p><strong>Level:</strong> {level}</p>
                <p><strong>Message:</strong> {message}</p>
                <p style="margin-top: 30px;"><a href="{url_for('index')}" style="color: #1e40af; text-decoration: none;">&larr; Back to Generator</a></p>
            </div>
        """
    else:
        # Handle invalid log levels
        logger.warning(f"Attempted to generate log with invalid level: {level}")
        return f"""
            <div style="text-align: center; padding: 50px;">
                <h2 style="color: #ef4444;">❌ Invalid Log Level</h2>
                <p>The level <strong>{level}</strong> is not supported.</p>
                <p style="margin-top: 30px;"><a href="{url_for('index')}" style="color: #1e40af; text-decoration: none;">&larr; Back to Generator</a></p>
            </div>
        """
@app.route('/skip')
@metrics.do_not_track()
def skip():
    pass  # default metrics are not collected

@app.route('/<item_type>')
@metrics.do_not_track()
@metrics.counter('invocation_by_type', 'Number of invocations by type',
                labels={'item_type': lambda: request.view_args['type']})
def by_type(item_type):
    pass  # only the counter is collected, not the default metrics

@app.route('/long-running')
@metrics.gauge('in_progress', 'Long running requests in progress')
def long_running():
    pass

@app.route('/status/<int:status>')
@metrics.do_not_track()
@metrics.summary('requests_by_status', 'Request latencies by status',
                labels={'status': lambda r: r.status_code})
@metrics.histogram('requests_by_status_and_path', 'Request latencies by status and path',
                labels={'status': lambda r: r.status_code, 'path': lambda: request.path})
def echo_status(status):
    return 'Status: %s' % status, status

# --- 4. Run the Application ---
if __name__ == '__main__':
    # Log a message when the application starts
    logger.info("Flask application starting up...")
    
    # The default Flask logging system is disabled to prevent duplicate output
    # since we are using our custom logger (logger.addHandler(stream_handler)).
    app.run(debug=True)
