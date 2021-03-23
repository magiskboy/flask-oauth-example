from datetime import datetime

from flask import current_app
import jwt

from tests import APITestCase
from app import auth
from app.models import (
    db,
    User,
    Post,
    Like,
)


class GetPostAPITestCase(APITestCase):
    def setUp(self):
        with current_app.test_request_context():
            self.user = User(email='test@email.com', name='Test').save()

            self.posts = [
                Post(title='Post 1', body='Body 1', summary='Body 1', author_id=self.user.id).save(),
                Post(title='Post 2', body='Body 2', summary='Body 2', author_id=self.user.id).save(),
                Post(title='Post 3', body='Body 3', summary='Body 3', author_id=self.user.id).save(),
            ]

    def test_get_list_post(self):
        resp = self.client.get('/posts')

        assert resp.status_code == 200
        for json, post in zip(
            sorted(resp.json['posts'], key=lambda x: x['id']),
            sorted(self.posts, key=lambda x: x.id)
        ):
            assert json['title'] == post.title


    def test_get_specify_post(self):
        post = self.posts[1]

        resp = self.client.get(f'/posts/{post.id}')
        assert resp.status_code == 200
        assert resp.json['data']['title'] == post.title

    def test_get_list_post_with_author_filter(self):
        with current_app.test_request_context():
            user1 = User(email='test1@email.com', name='Test 1').save()

            posts1 = [
                Post(title='Post 4', body='Body 4', summary='Body 4', author_id=user1.id).save(),
                Post(title='Post 5', body='Body 5', summary='Body 5', author_id=user1.id).save(),
                Post(title='Post 6', body='Body 6', summary='Body 6', author_id=user1.id).save(),
            ]

        resp = self.client.get(f'/posts?author_id={user1.id}')
        assert resp.status_code == 200
        for json, post in zip(
            sorted(resp.json['posts'], key=lambda x: x['id']),
            sorted(posts1, key=lambda x: x.id)
        ):
            assert json['title'] == post.title
            assert json['author_id'] == user1.id


class CreatePostAPITestCase(APITestCase):
    def setUp(self):
        with current_app.test_request_context():
            self.user = User(email='test@email.com', name='Test').save()
            token = jwt.encode({
                'id': self.user.id,
                'name': self.user.name,
                'email': self.user.email,
                'iss': datetime.now().timestamp(),
                'iat': auth.TOKEN_EXPIRED_TIME,
            }, key=current_app.config['SECRET_KEY'], algorithm='HS256')

            self.access_token = token
            auth.redis.sadd('alive_token', token)

    def test_create_post_with_access_token(self):
        payload = {
            'title': 'New post',
            'body': 'Test create new post',
        }
        resp = self.client.post('/posts', json=payload,
                                headers={'authorization': f'Bearer {self.access_token}'})

        assert resp.status_code == 201, self.access_token
        post = Post.query.get(resp.json['data']['id'])
        assert post.title == payload['title']
        assert post.body == payload['body']
        assert post.author_id == self.user.id


class GetLikeTestCase(APITestCase):
    def setUp(self):
        with current_app.test_request_context():
            self.users = [
                User(email='user1@email.com', name='User 1').save(),
                User(email='user2@email.com', name='User 2').save(),
                User(email='user3@email.com', name='User 3').save(),
            ]

            self.post = Post(title='Post 1',body='Body 4',
                             summary='Body 4', n_likes=3,
                             author_id=self.users[0].id).save()

            self.likes = [
                Like(user_id=self.users[0].id, post_id=self.post.id).save(),
                Like(user_id=self.users[1].id, post_id=self.post.id).save(),
                Like(user_id=self.users[2].id, post_id=self.post.id).save(),
            ]

    def test_get_list_liked_user(self):
        resp = self.client.get(f'/posts/{self.post.id}/likes')

        assert resp.status_code == 200
        assert sorted([x['name'] for x in resp.json['users']]) == sorted([x.name for x in self.users])

    def test_get_like_string(self):
        resp = self.client.get(f'/posts/{self.post.id}')

        assert resp.status_code == 200
        assert resp.json['data']['like_string'] == 'User 1, User 2, and 1 other people liked this post.'
