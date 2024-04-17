from flask import Flask, render_template, jsonify, request, session
import requests
import time
from threading import Thread
import os
import qrcode

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.secret_key = os.urandom(16)

# Global storage for the access token
access_token_info = {
    'access_token': None,
    'token_ready': False
}

# Define your clientID and client secret
clientID = os.environ['clientID']
secretID = os.environ['secretID']
credentials = os.environ['credentials']
redirectURI = "http://0.0.0.0:10060/helperservice/v1/actions/device/callback"  # This could be different if you publicly expose this endpoint.


@app.route("/")
def main_page():
    """Main Grant page"""
    scopes = "meeting:recordings_read spark:all spark:kms cjp:config_write cjp:config cjds:admin_org_read cjds:admin_org_write"
    params = {'client_id': clientID, 'scope': scopes, 'redirectURI': redirectURI}
    devices_api = "https://webexapis.com/v1/device/authorize"
    api_response = requests.post(url=devices_api, data=params)
    response_json = api_response.json()

    # Store device code in session to use it in polling later
    session['device_code'] = response_json['device_code']

    qrcode_url = response_json['verification_uri_complete']
    verification_uri = response_json['verification_uri']
    user_code = response_json['user_code']

    # No need to print, unless for debugging. Instead, pass these to the template
    print(qrcode_url)
    qr_cde_generation(qrcode_url)

    # Start polling in a separate thread
    thread = Thread(target=poll_for_access_token, args=(session['device_code'],))
    thread.start()

    # Render the template and pass the necessary data
    return render_template("index.html", verification_url=verification_uri, user_code=user_code)


def qr_cde_generation(url):
    img = qrcode.make(url)
    img.save('./static/css/qr_code.png')


def poll_for_access_token(device_code):
    print("Inside of poll for access token")
    print(device_code)
    """Poll the token endpoint for an access token."""
    token_url = "https://webexapis.com/v1/device/token"
    headers = {'Authorization': f'Basic {credentials}', 'Accept': 'application/json', 'ContentType': 'application/x'
                                                                                                     '-www-form'
                                                                                                     '-urlencoded; '
                                                                                                     'charset=utf-8'}
    body = {
        'client_id': f'{clientID}',
        'device_code': f'{device_code}',
        'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'
    }

    # Polling every 5 seconds (adjust as needed)
    while True:
        time.sleep(2)
        token_response = requests.post(url=token_url, data=body, headers=headers)
        if token_response.status_code == 200:
            access_token = token_response.json()['access_token']
            # Store the access token in session or another secure place
            # session['access_token'] = access_token
            access_token_info['access_token'] = access_token
            access_token_info['token_ready'] = True
            print("Access token obtained")
            break
        elif token_response.json().get('error') == 'authorization_pending':
            # User has not completed the authentication yet; continue polling
            time.sleep(2)
        else:
            # Handle other errors (e.g., 'slow_down', 'expired_token')
            print("Error polling for token:", token_response.json())


# This route is just an example to show how to access the stored access token
@app.route("/granted")
def granted():
    # Check if the access token is ready and render the granted.html template
    if access_token_info['token_ready']:
        return render_template("granted.html", access_token=access_token_info['access_token'])
    else:
        # If the token isn't ready, you might want to inform the user or redirect
        return "Access token not ready yet. Please try again later."

@app.route("/access_token_ready")
def access_token_ready():
    return jsonify({'token_ready': access_token_info['token_ready']})

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=10060)
