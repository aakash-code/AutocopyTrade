from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
import subprocess
import os
import json
import pandas as pd
from utils import read_config, write_config, encrypt_value

app = Flask(__name__)
# A secret key is needed for flashing messages
app.secret_key = os.urandom(24)

# --- State Management (simple file-based) ---
STATUS_FILE = 'status.json'
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

@app.route('/api/broker_status')
def broker_status():
    """
    Returns the detailed status of each broker.
    """
    try:
        with open('broker_status.json', 'r') as f:
            return jsonify(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({})


# --- Account Management Routes ---

@app.route('/accounts')
def accounts():
    config = read_config()
    if not config:
        flash('Could not read config.json!', 'error')
        return render_template('accounts.html', master_account={}, child_accounts={})

    return render_template('accounts.html',
                           master_account=config.get('MASTER', {}),
                           child_accounts=config.get('CHILD', {}))

@app.route('/add_account', methods=['POST'])
def add_account():
    config = read_config()
    if not config:
        flash('Could not read config.json!', 'error')
        return redirect(url_for('accounts'))

    account_name = request.form['account_name']
    if account_name in config['CHILD']:
        flash(f'Account name "{account_name}" already exists!', 'error')
        return redirect(url_for('accounts'))

    # Build the new account object based on broker type
    broker_type = request.form['broker']
    new_account = {'broker': broker_type, 'enabled': request.form['enabled']}

    if broker_type == 'zerodha':
        # Encrypt password and TOTP if provided
        password = request.form['password']
        totp_secret = request.form['totp_secret']
        if password:
            new_account['password'] = encrypt_value(password)
        if totp_secret:
            new_account['TOPTSecret'] = encrypt_value(totp_secret)

        new_account['userid'] = request.form['userid']
        new_account['APIKey'] = request.form['api_key']
        new_account['APISecret'] = request.form['api_secret']
        new_account['loginURL'] = f"https://kite.trade/connect/login?api_key={request.form['api_key']}"
        new_account['multiplier'] = float(request.form['multiplier'])

    elif broker_type == 'dhan':
        new_account['clientID'] = request.form['userid']
        new_account['accessToken'] = request.form['access_token']
        new_account['multiplier'] = float(request.form['multiplier'])

    config['CHILD'][account_name] = new_account

    if write_config(config):
        flash(f'Account "{account_name}" added successfully!', 'success')
    else:
        flash('Failed to write to config.json!', 'error')

    return redirect(url_for('accounts'))

@app.route('/delete_account/<account_name>', methods=['POST'])
def delete_account(account_name):
    config = read_config()
    if not config:
        flash('Could not read config.json!', 'error')
        return redirect(url_for('accounts'))

    if account_name in config['CHILD']:
        del config['CHILD'][account_name]
        if write_config(config):
            flash(f'Account "{account_name}" deleted successfully!', 'success')
        else:
            flash('Failed to write to config.json!', 'error')
    else:
        flash(f'Account "{account_name}" not found!', 'error')

    return redirect(url_for('accounts'))

@app.route('/edit_account/<account_name>')
def edit_account(account_name):
    config = read_config()
    if not config or account_name not in config.get('CHILD', {}):
        flash(f'Account "{account_name}" not found!', 'error')
        return redirect(url_for('accounts'))

    account = config['CHILD'][account_name]
    return render_template('edit_account.html', account_name=account_name, account=account)

@app.route('/update_account/<account_name>', methods=['POST'])
def update_account(account_name):
    config = read_config()
    if not config or account_name not in config.get('CHILD', {}):
        flash(f'Account "{account_name}" not found!', 'error')
        return redirect(url_for('accounts'))

    # Update the account details
    account_data = config['CHILD'][account_name]
    broker_type = account_data['broker'] # Broker type cannot be changed

    if broker_type == 'zerodha':
        password = request.form['password']
        totp_secret = request.form['totp_secret']
        if password:
            account_data['password'] = encrypt_value(password)
        if totp_secret:
            account_data['TOPTSecret'] = encrypt_value(totp_secret)

        account_data['userid'] = request.form['userid']
        account_data['APIKey'] = request.form['api_key']
        account_data['APISecret'] = request.form['api_secret']
        account_data['loginURL'] = f"https://kite.trade/connect/login?api_key={request.form['api_key']}"

    elif broker_type == 'dhan':
        account_data['clientID'] = request.form['userid']
        account_data['accessToken'] = request.form['access_token']

    account_data['multiplier'] = float(request.form['multiplier'])
    account_data['enabled'] = request.form['enabled']

    if write_config(config):
        flash(f'Account "{account_name}" updated successfully!', 'success')
    else:
        flash('Failed to write to config.json!', 'error')

    return redirect(url_for('accounts'))


# --- Instrument Mapping Routes ---

@app.route('/mapping')
def mapping():
    # Load instrument lists
    try:
        zerodha_instruments = pd.read_csv('zerodha_instruments.csv')
    except FileNotFoundError:
        zerodha_instruments = pd.DataFrame()
        flash('zerodha_instruments.csv not found. Please run fetch_instruments.py first.', 'warning')

    try:
        dhan_instruments = pd.read_csv('dhan_instruments.csv')
    except FileNotFoundError:
        dhan_instruments = pd.DataFrame()
        flash('dhan_instruments.csv not found. Please run fetch_instruments.py first.', 'warning')

    # Load existing mappings
    try:
        with open('instrument_mappings.json', 'r') as f:
            mappings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        mappings = {}

    return render_template('mapping.html',
                           zerodha_instruments=zerodha_instruments.head(1000), # Limit for performance
                           dhan_instruments=dhan_instruments.head(1000),
                           mappings=mappings)

@app.route('/add_mapping', methods=['POST'])
def add_mapping():
    try:
        with open('instrument_mappings.json', 'r') as f:
            mappings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        mappings = {}

    source_instrument = request.form['zerodha_instrument']
    target_instrument = request.form['dhan_instrument']

    if not source_instrument or not target_instrument:
        flash('Please select one instrument from each list.', 'error')
        return redirect(url_for('mapping'))

    # For now, we only map to dhan. This could be extended.
    if source_instrument in mappings:
        mappings[source_instrument]['dhan'] = target_instrument
    else:
        mappings[source_instrument] = {'dhan': target_instrument}

    try:
        with open('instrument_mappings.json', 'w') as f:
            json.dump(mappings, f, indent=4)
        flash('Mapping saved successfully!', 'success')
    except IOError:
        flash('Failed to save mapping!', 'error')

    return redirect(url_for('mapping'))


# --- Global Settings Routes ---

@app.route('/settings')
def settings():
    config = read_config()
    if not config:
        flash('Could not read config.json!', 'error')
        return render_template('settings.html', product_filter_str="")

    product_filter = config.get('DONOTPROCESSPROD', [])
    product_filter_str = ", ".join(product_filter)
    return render_template('settings.html', product_filter_str=product_filter_str)

@app.route('/update_settings', methods=['POST'])
def update_settings():
    config = read_config()
    if not config:
        flash('Could not read config.json!', 'error')
        return redirect(url_for('settings'))

    # Update product filter
    product_filter_str = request.form.get('donotprocessprod', '')
    # Convert comma-separated string to a list of uppercase strings, stripping whitespace
    product_filter_list = [item.strip().upper() for item in product_filter_str.split(',') if item.strip()]
    config['DONOTPROCESSPROD'] = product_filter_list

    if write_config(config):
        flash('Global settings updated successfully!', 'success')
    else:
        flash('Failed to write to config.json!', 'error')

    return redirect(url_for('settings'))


# --- History Route ---

@app.route('/history')
def history():
    try:
        # Read the log file and reverse it so recent trades are on top
        trade_log_df = pd.read_csv('trade_log.csv')
        trade_log = trade_log_df.iloc[::-1].to_dict(orient='records')
    except FileNotFoundError:
        trade_log = []
        flash('trade_log.csv not found. No trades have been logged yet.', 'warning')
    except Exception as e:
        trade_log = []
        flash(f'Error reading trade log: {e}', 'error')

    return render_template('history.html', trade_log=trade_log)


if __name__ == '__main__':
    app.run(debug=True, port=5001)
