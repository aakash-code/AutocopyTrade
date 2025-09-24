from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
import subprocess
import os
import json
import pandas as pd
import database
from utils import encrypt_value

app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.before_first_request
def initialize_database():
    database.init_db()

# --- Main & API Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/start', methods=['POST'])
def start_replicator():
    if os.path.exists('replicator.pid'):
        return jsonify({'status': 'error', 'message': 'Replicator is already running.'}), 400
    try:
        process = subprocess.Popen(['python', 'main.py'], stdout=open('replicator.log', 'w'), stderr=subprocess.STDOUT)
        with open('replicator.pid', 'w') as f:
            f.write(str(process.pid))
        return jsonify({'status': 'success', 'message': 'Replicator started.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/stop', methods=['POST'])
def stop_replicator():
    if not os.path.exists('replicator.pid'):
        return jsonify({'status': 'error', 'message': 'Replicator is not running.'}), 400
    try:
        with open('replicator.pid', 'r') as f:
            pid = int(f.read())
        os.kill(pid, 9)
        os.remove('replicator.pid')
        return jsonify({'status': 'success', 'message': 'Replicator stopped.'})
    except Exception as e:
        if os.path.exists('replicator.pid'):
            os.remove('replicator.pid')
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/status')
def api_status():
    if os.path.exists('replicator.pid'):
        return jsonify({'status': 'Running'})
    else:
        return jsonify({'status': 'Stopped'})

@app.route('/api/broker_status')
def broker_status():
    try:
        with open('broker_status.json', 'r') as f:
            return jsonify(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({})

# --- Account Management Routes ---
@app.route('/accounts')
def accounts():
    all_accounts = database.get_all_accounts()
    master_account = database.get_master_account()
    master_account_name = master_account['name'] if master_account else None
    return render_template('accounts.html', accounts=all_accounts, master_account_name=master_account_name)

@app.route('/add_account', methods=['POST'])
def add_account():
    account_name = request.form.get('account_name')
    broker = request.form.get('broker')
    enabled = request.form.get('enabled') == 'Y'

    config_dict = {}
    if broker == 'zerodha':
        password = request.form.get('password')
        totp_secret = request.form.get('totp_secret')
        if password: config_dict['password'] = encrypt_value(password)
        if totp_secret: config_dict['TOPTSecret'] = encrypt_value(totp_secret)
        config_dict['userid'] = request.form.get('userid')
        config_dict['APIKey'] = request.form.get('api_key')
        config_dict['APISecret'] = request.form.get('api_secret')
        config_dict['loginURL'] = f"https://kite.trade/connect/login?api_key={request.form.get('api_key')}"
        config_dict['multiplier'] = float(request.form.get('multiplier', 1.0))
    elif broker == 'dhan':
        config_dict['clientID'] = request.form.get('userid')
        config_dict['accessToken'] = request.form.get('access_token')
        config_dict['multiplier'] = float(request.form.get('multiplier', 1.0))

    if database.add_account(account_name, broker, config_dict, enabled=enabled):
        flash(f'Account "{account_name}" added successfully.', 'success')
    else:
        flash(f'Account with name "{account_name}" already exists.', 'error')
    return redirect(url_for('accounts'))

@app.route('/set_master/<account_name>', methods=['POST'])
def set_master(account_name):
    database.set_master_account(account_name)
    flash(f'"{account_name}" is now the master account.', 'success')
    return redirect(url_for('accounts'))

@app.route('/toggle_account/<account_name>', methods=['POST'])
def toggle_account(account_name):
    all_accounts = database.get_all_accounts()
    account = all_accounts.get(account_name)
    if account:
        new_status = not account['enabled']
        database.update_account_enabled(account_name, new_status)
        flash(f'Account "{account_name}" has been {"enabled" if new_status else "disabled"}.', 'success')
    else:
        flash(f'Account "{account_name}" not found.', 'error')
    return redirect(url_for('accounts'))

@app.route('/delete_account/<account_name>', methods=['POST'])
def delete_account(account_name):
    master_account = database.get_master_account()
    if master_account and master_account['name'] == account_name:
        flash('Cannot delete the master account. Please set a different master first.', 'error')
        return redirect(url_for('accounts'))
    database.delete_account(account_name)
    flash(f'Account "{account_name}" deleted.', 'success')
    return redirect(url_for('accounts'))

@app.route('/edit_account/<account_name>')
def edit_account(account_name):
    all_accounts = database.get_all_accounts()
    account = all_accounts.get(account_name)
    if not account:
        flash(f'Account "{account_name}" not found!', 'error')
        return redirect(url_for('accounts'))
    return render_template('edit_account.html', account_name=account_name, account=account)

@app.route('/update_account/<account_name>', methods=['POST'])
def update_account(account_name):
    enabled = request.form.get('enabled') == 'Y'
    all_accounts = database.get_all_accounts()
    account_data = all_accounts.get(account_name, {})
    config_dict = {k: v for k, v in account_data.items() if k not in ['broker', 'enabled', 'is_master', 'name']}
    broker = account_data.get('broker')
    if broker == 'zerodha':
        password = request.form.get('password')
        totp_secret = request.form.get('totp_secret')
        if password: config_dict['password'] = encrypt_value(password)
        if totp_secret: config_dict['TOPTSecret'] = encrypt_value(totp_secret)
        config_dict['userid'] = request.form.get('userid')
        config_dict['APIKey'] = request.form.get('api_key')
        config_dict['APISecret'] = request.form.get('api_secret')
        config_dict['loginURL'] = f"https://kite.trade/connect/login?api_key={request.form.get('api_key')}"
        config_dict['multiplier'] = float(request.form.get('multiplier', 1.0))
    elif broker == 'dhan':
        config_dict['clientID'] = request.form.get('userid')
        config_dict['accessToken'] = request.form.get('access_token')
        config_dict['multiplier'] = float(request.form.get('multiplier', 1.0))
    database.update_account(account_name, config_dict, enabled)
    flash(f'Account "{account_name}" updated successfully.', 'success')
    return redirect(url_for('accounts'))

# --- Other UI Routes ---
@app.route('/mapping')
def mapping():
    try:
        zerodha_instruments = pd.read_csv('zerodha_instruments.csv')
    except FileNotFoundError:
        zerodha_instruments = pd.DataFrame()
    try:
        dhan_instruments = pd.read_csv('dhan_instruments.csv')
    except FileNotFoundError:
        dhan_instruments = pd.DataFrame()
    try:
        with open('instrument_mappings.json', 'r') as f:
            mappings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        mappings = {}
    return render_template('mapping.html', zerodha_instruments=zerodha_instruments.head(1000), dhan_instruments=dhan_instruments.head(1000), mappings=mappings)

@app.route('/settings')
def settings():
    product_filter = database.get_setting('DONOTPROCESSPROD') or []
    product_filter_str = ", ".join(product_filter)
    return render_template('settings.html', product_filter_str=product_filter_str)

@app.route('/update_settings', methods=['POST'])
def update_settings():
    product_filter_str = request.form.get('donotprocessprod', '')
    product_filter_list = [item.strip().upper() for item in product_filter_str.split(',') if item.strip()]
    database.set_setting('DONOTPROCESSPROD', product_filter_list)
    flash('Global settings updated successfully!', 'success')
    return redirect(url_for('settings'))

@app.route('/history')
def history():
    try:
        trade_log_df = pd.read_csv('trade_log.csv')
        trade_log = trade_log_df.iloc[::-1].to_dict(orient='records')
    except FileNotFoundError:
        trade_log = []
    return render_template('history.html', trade_log=trade_log)

if __name__ == '__main__':
    app.run(debug=True, port=5001, use_reloader=False)
