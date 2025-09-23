from flask import Flask, render_template, jsonify, request
import json
import subprocess
import os

app = Flask(__name__)

# --- State Management (simple file-based) ---
STATUS_FILE = 'status.json'
CONFIG_FILE = 'config.json'
PID_FILE = 'replicator.pid'

def get_status():
    if not os.path.exists(STATUS_FILE):
        return {'status': 'Stopped', 'message': 'Replicator has not been run yet.'}
    try:
        with open(STATUS_FILE, 'r') as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError):
        return {'status': 'Unknown', 'message': 'Could not read status file.'}

def set_status(status, message):
    with open(STATUS_FILE, 'w') as f:
        json.dump({'status': status, 'message': message}, f)

# --- Routes ---
@app.route('/')
def index():
    """
    Renders the main dashboard page.
    """
    return render_template('index.html', status=get_status())

@app.route('/api/start', methods=['POST'])
def start_replicator():
    """
    Starts the main.py script as a background process.
    """
    if os.path.exists(PID_FILE):
        return jsonify({'status': 'error', 'message': 'Replicator is already running.'}), 400

    try:
        # Run main.py in the background
        process = subprocess.Popen(['python', 'main.py'],
                                   stdout=open('replicator.log', 'w'),
                                   stderr=subprocess.STDOUT)

        with open(PID_FILE, 'w') as f:
            f.write(str(process.pid))

        set_status('Running', f'Replicator started with PID {process.pid}.')
        return jsonify({'status': 'success', 'message': 'Replicator started.'})
    except Exception as e:
        set_status('Error', f'Failed to start replicator: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/stop', methods=['POST'])
def stop_replicator():
    """
    Stops the background replicator process.
    """
    if not os.path.exists(PID_FILE):
        return jsonify({'status': 'error', 'message': 'Replicator is not running.'}), 400

    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read())

        # This will kill the process. A more graceful shutdown would be better.
        os.kill(pid, 9) # SIGKILL

        os.remove(PID_FILE)
        set_status('Stopped', f'Replicator with PID {pid} has been stopped.')
        return jsonify({'status': 'success', 'message': 'Replicator stopped.'})
    except Exception as e:
        set_status('Error', f'Failed to stop replicator: {e}')
        # If the process is already dead, we might get an error. Clean up anyway.
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/status')
def api_status():
    """
    Returns the current status of the replicator.
    """
    return jsonify(get_status())


if __name__ == '__main__':
    app.run(debug=True, port=5001)
