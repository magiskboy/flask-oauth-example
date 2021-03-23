import json
from functools import partial
from datetime import datetime

import requests
from flask_login import (
    LoginManager,
    login_required,
    current_user,
)
from flask import (
    Blueprint,
    jsonify,
    request,
    current_app,
    redirect,
    url_for,
    abort,
)
from oauthlib.oauth2 import WebApplicationClient
import jwt

from .models import User

TOKEN_EXPIRED_TIME = 1000 * 60 * 60 * 24

login_manager = LoginManager()
redis = None

def init_app(app):
    login_manager.init_app(app)

    global redis
    if app.testing:
        from fakeredis import FakeRedis
        redis = FakeRedis()
    else:
        from redis import Redis
        redis = Redis.from_url(app.config['REDIS_URL'])


@login_manager.request_loader
def load_user_from_request(request):
    token = request.args.get('access_token', default='', type=str).strip()
    if not token:
        token = request.headers.get('authorization', '').replace('Bearer', '').strip()

    if not (token and redis.sismember('alive_token', token)):
        return None

    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms='HS256')
    except jwt.DecodeError:
        return None

    user = User.query.get(payload['id'])
    return user


def validate_state(state):
    supported_providers = ('google', 'facebook')
    supported_actions = ('login', 'register')

    if state.get('action') not in supported_actions:
        return False
    if state.get('provider') not in supported_providers:
        return False

    return True


class CallbackHandler:
    provider = None

    token_endpoint = None

    userinfo_endpoint = None

    def __init__(self, action, code, client_id, client_secret, token_gen):
        self.action = action
        self.code = code
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_gen = token_gen

    def _do_login(self):
        userinfo = self._fetch_userinfo()

        user = User.query.filter(
            User.email == userinfo['email']
        ).first()
        if not user:
            abort(400, f'User {userinfo["email"]} is not exist')

        dont_link_to_facebook = user.link_to_google and (not user.link_to_facebook and self.provider == 'facebook')
        dont_link_to_google = user.link_to_facebook and (not user.link_to_google and self.provider == 'google')
        if dont_link_to_facebook or dont_link_to_google:
            abort(400, f'User {userinfo["email"]} is not linked to {self.provider}')

        token = self.token_gen({
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'iss': datetime.now().timestamp(),
            'iat': TOKEN_EXPIRED_TIME
        })

        redis.sadd('alive_token', token)

        return {
            'access_token': token,
        }

    def _do_register(self):
        userinfo = self._fetch_userinfo()

        user = User.query.filter(
            User.email == userinfo['email']
        ).first()

        if user:
            dont_link_to_facebook = user.link_to_google and (not user.link_to_facebook and self.provider == 'facebook')
            dont_link_to_google = user.link_to_facebook and (not user.link_to_google and self.provider == 'google')
            if dont_link_to_facebook or dont_link_to_google:
                # need user confirm by sending to processing link
                token = self.token_gen({
                    'id': user.id,
                    'name': user.name,
                    'email': user.email,
                    'iss': datetime.now().timestamp(),
                    'iat': 1000 * 60 * 5,
                })
                redis.sadd('alive_token', token)

                return {
                    'message': f'Email {userinfo["email"]} was used by {user.name}. Do you link to the {self.provider} account',
                    'data': {
                        'link': url_for('auth.link_account', access_token=token, provider=self.provider, _external=True),
                    }
                }

            abort(400, f'User {userinfo["email"]} existed')

        new_user = User(
            email=userinfo['email'],
            name=userinfo['name'],
        )
        if self.provider == 'google':
            new_user.link_to_google = True
        elif self.provider == 'facebook':
            new_user.link_to_facebook = True
        new_user.save()
        return {'message': f'Create {userinfo["email"]} successful'}

    def _fetch_userinfo(self):
        client = WebApplicationClient(self.client_id)

        # get access token
        token_url, headers, body = client.prepare_token_request(
            self.token_endpoint,
            authorization_response=request.url,
            redirect_url=request.base_url,
            code=self.code,
        )

        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(self.client_id, self.client_secret),
        )
        client.parse_request_body_response(token_response.text)

        # get user information
        uri, headers, body = client.add_token(self.userinfo_endpoint)
        userinfo_response = requests.get(uri, headers=headers, data=body)
        data = userinfo_response.json()

        return data

    def handle(self, *args, **kwargs):
        action = self.action

        if action == 'login':
            result = self._do_login(*args, **kwargs)
        elif action == 'register':
            result = self._do_register(*args, **kwargs)

        return result


class GoogleCallbackHandler(CallbackHandler):
    provider = 'google'

    token_endpoint = 'https://oauth2.googleapis.com/token'

    userinfo_endpoint = 'https://openidconnect.googleapis.com/v1/userinfo'

    def _fetch_userinfo(self):
        raw_data = super()._fetch_userinfo()
        return {
            'name': raw_data.get('name'),
            'email': raw_data.get('email'),
        }


class FacebookCallbackHandler(CallbackHandler):
    provider = 'facebook'

    token_endpoint = 'https://graph.facebook.com/v10.0/oauth/access_token'

    userinfo_endpoint = 'https://graph.facebook.com/v10.0/me?fields=name,email'

    def _fetch_userinfo(self):
        raw_data = super()._fetch_userinfo()
        return {
            'name': raw_data.get('name'),
            'email': raw_data.get('email'),
        }


bp = Blueprint('auth', __name__)


@bp.route('/')
def handle_auth():
    state = request.args.to_dict()
    if not validate_state(state):
        abort(400, 'Action or Provider is invalid')

    provider = state.get('provider')
    redirect_uri = url_for('auth.oauth_callback', _external=True)
    if provider == 'google':
        CLIENT_ID = current_app.config['GOOGLE_CLIENT_ID']
        authorization_endpoint = 'https://accounts.google.com/o/oauth2/v2/auth'
        scope=["openid", "email", "profile"]

    elif provider == 'facebook':
        CLIENT_ID = current_app.config['FACEBOOK_CLIENT_ID']
        authorization_endpoint = 'https://www.facebook.com/v10.0/dialog/oauth'
        scope = ['email',]

    oauth_client = WebApplicationClient(CLIENT_ID)
    request_uri = oauth_client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=redirect_uri,
        scope=scope,
        state=json.dumps(state),
    )
    return redirect(request_uri)


@bp.route('/callback')
def oauth_callback():
    state = json.loads(request.args.get('state', type=str))
    if not validate_state(state):
        abort(400, 'Action or Provider is invalid')

    action, provider = state['action'], state['provider']
    code = request.args.get('code', type=str)
    token_generator = partial(
        jwt.encode,
        algorithm='HS256',
        key=current_app.config['SECRET_KEY'],
    )

    if provider == 'google':
        handler = GoogleCallbackHandler(
            action=action,
            code=code,
            client_id=current_app.config['GOOGLE_CLIENT_ID'],
            client_secret=current_app.config['GOOGLE_CLIENT_SECRET'],
            token_gen=token_generator,
        )

    elif provider == 'facebook':
        handler = FacebookCallbackHandler(
            action=action,
            code=code,
            client_id=current_app.config['FACEBOOK_CLIENT_ID'],
            client_secret=current_app.config['FACEBOOK_CLIENT_SECRET'],
            token_gen=token_generator,
        )

    return handler.handle()


@bp.route('/link_account')
@login_required
def link_account():
    provider = request.args.get('provider')
    if provider not in ('facebook', 'google'):
        abort(400, 'Provider was not supported')

    if provider == 'google' and current_user.link_to_google:
        abort(400, 'This account was linked to Google account')

    if provider == 'facebook' and current_user.link_to_facebook:
        abort(400, 'This access_token was linked to Facebook account')

    current_user.link_to_facebook = True
    current_app.link_to_google = True
    current_user.save()
    return {
        'message': f'This account is linked to {provider}'
    }


@bp.route('/logout')
@login_required
def logout():
    token = request.headers.get('authorization').replace('Bearer', '').strip()
    redis.srem('alive_token', token)
    return {
        'message': 'Logout successful',
    }
