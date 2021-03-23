import json
from functools import partial
from datetime import datetime

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

from .oauth2 import (
    GoogleOAuth2Client,
    FacebookOAuth2Client,
)
from .models import User


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


def handle_login(provider, userinfo, token_generator):
    user = User.query.filter(
        User.email == userinfo['email']
    ).first()
    if not user:
        abort(400, f'User {userinfo["email"]} is not exist')

    dont_link_to_facebook = user.link_to_google and (not user.link_to_facebook and provider == 'facebook')
    dont_link_to_google = user.link_to_facebook and (not user.link_to_google and provider == 'google')
    if dont_link_to_facebook or dont_link_to_google:
        abort(400, f'User {userinfo["email"]} is not linked to { provider}')

    token = token_generator({
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'iss': datetime.now().timestamp(),
        'iat': 1000 * 60 * 60 * 24,
    })

    redis.sadd('alive_token', token)

    return {
        'access_token': token,
    }


def handle_register(provider, userinfo, token_generator):
    user = User.query.filter(
        User.email == userinfo['email']
    ).first()

    if user:
        dont_link_to_facebook = user.link_to_google and (not user.link_to_facebook and provider == 'facebook')
        dont_link_to_google = user.link_to_facebook and (not user.link_to_google and provider == 'google')
        if dont_link_to_facebook or dont_link_to_google:
            # need user confirm by sending to processing link
            token = token_generator({
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'iss': datetime.now().timestamp(),
                'iat': 1000 * 60 * 5,
            })
            redis.sadd('alive_token', token)

            return {
                'message': f'Email {userinfo["email"]} was used by {user.name}. Do you link to the {provider} account',
                'data': {
                    'link': url_for('auth.link_account', access_token=token, provider=provider, _external=True),
                }
            }

        abort(400, f'User {userinfo["email"]} existed')

    new_user = User(
        email=userinfo['email'],
        name=userinfo['name'],
    )
    if provider == 'google':
        new_user.link_to_google = True
    elif provider == 'facebook':
        new_user.link_to_facebook = True
    new_user.save()
    return {'message': f'Create {userinfo["email"]} successful'}


bp = Blueprint('auth', __name__)


@bp.route('/')
def handle_auth():
    redirect_uri = url_for('auth.oauth_callback', _external=True)
    state = request.args.to_dict()
    if not validate_state(state):
        abort(400, 'Action or Provider is invalid')

    provider = state.get('provider')
    if provider == 'google':
        return redirect(GoogleOAuth2Client.get_grant_request_url(
            current_app.config['GOOGLE_CLIENT_ID'],
            redirect_uri,
            ['openid', 'email', 'profile'],
            state,
        ))

    if provider == 'facebook':
        return redirect(FacebookOAuth2Client.get_grant_request_url(
            current_app.config['FACEBOOK_CLIENT_ID'],
            redirect_uri,
            ['email'],
            state,
        ))


@bp.route('/callback')
def oauth_callback():
    state = json.loads(request.args.get('state', type=str))
    if not validate_state(state):
        abort(400, 'Action or Provider is invalid')

    provider = state['provider']
    code = request.args.get('code', type=str)
    if provider == 'google':
        userinfo = GoogleOAuth2Client.get_userinfo(
            current_app.config['GOOGLE_CLIENT_ID'],
            current_app.config['GOOGLE_CLIENT_SECRET'],
            code,
            request.url,
        )

    elif provider == 'facebook':
        userinfo = FacebookOAuth2Client.get_userinfo(
            current_app.config['FACEBOOK_CLIENT_ID'],
            current_app.config['FACEBOOK_CLIENT_SECRET'],
            code,
            request.url,
        )

    action = state.get('action')
    if action == 'login':
        handle = handle_login
    elif action == 'register':
        handle = handle_register

    token_generator = partial(jwt.encode, key=current_app.config['SECRET_KEY'],
                              algorithm='HS256')
    return handle(provider, userinfo, token_generator)


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
