from flask import Flask, render_template, jsonify
import requests
import time
from threading import Thread
import os
import qrcode

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.secret_key = os.urandom(16)

# Global storage for the access token
session = {
    'access_token': None,
    'token_ready': False,
    'device_code': None,
    'poll_interval': 0,
}

# Define your clientID and client secret
clientID = os.environ['clientID']
secretID = os.environ['secretID']
credentials = os.environ['credentials']


def qr_cde_generation(url):
    img = qrcode.make(url)
    img.save('./static/qr_code.png')


def poll_for_access_token(device_code, poll_interval):
    """Poll the token endpoint for an access token."""
    token_url = "https://webexapis.com/v1/device/token"
    headers = {'Authorization': f'Basic {credentials}'}
    body = {
        'client_id': f'{clientID}',
        'device_code': f'{device_code}',
        'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'
    }

    # Polling in seconds based on the poll_interval value
    while True:
        time.sleep(poll_interval)
        token_response = requests.post(url=token_url, data=body, headers=headers)
        if token_response.status_code == 200:
            access_token = token_response.json()['access_token']
            # Store the access token in session or another secure place
            session['access_token'] = access_token
            session['token_ready'] = True
            print(token_response.json())
            break
        else:
            # Handle other errors (e.g., 'slow_down', 'expired_token')
            print("Response Code:", token_response.status_code, token_response.json()['errors'][0]['description'])


def whoami_lookup():
    people_api_url = "https://webexapis.com/v1/people/me?callingData=true"
    headers = {'Authorization': f"Bearer {session['access_token']}"}
    people_api = requests.get(url=people_api_url, headers=headers)
    return people_api.json()


@app.route("/")
def main_page():
    """Main Grant page"""
    scopes = "meeting:recordings_read spark:all spark:kms cjp:config_write cjp:config cjds:admin_org_read cjds:admin_org_write"
    params = {'client_id': clientID, 'scope': scopes}
    devices_api = "https://webexapis.com/v1/device/authorize"
    api_response = requests.post(url=devices_api, data=params)
    response_json = api_response.json()
    print(response_json)
    # Store device code in session to use it in polling later
    session['device_code'] = response_json['device_code']
    session['poll_interval'] = response_json['interval']

    qrcode_url = response_json['verification_uri_complete']
    verification_uri = response_json['verification_uri']
    user_code = response_json['user_code']

    # No need to print, unless for debugging. Instead, pass these to the template
    qr_cde_generation(qrcode_url)

    # Start polling in a separate thread
    thread = Thread(target=poll_for_access_token, args=(session['device_code'], session['poll_interval'],))
    thread.start()

    # Render the template and pass the necessary data
    return render_template("index.html", verification_url=verification_uri, user_code=user_code)


@app.route("/granted")
def granted():
    # Check if the access token is ready and render the granted.html template
    if session['token_ready']:
        return render_template("granted.html")
    else:
        # If the token isn't ready, you might want to inform the user or redirect
        return "Access token not ready yet. Please try again later."


@app.route("/whoami")
def whoami():
    studentinfo = whoami_lookup()
    return render_template("whoami.html", me=studentinfo)


@app.route("/access_token_ready")
def access_token_ready():
    return jsonify({'token_ready': session['token_ready']})


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=10060)
