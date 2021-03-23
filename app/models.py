import sqlalchemy as sa
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import UserMixin


db = SQLAlchemy()


class BaseModel:
    id = sa.Column(sa.Integer(), primary_key=True, autoincrement=True)
    created_at = sa.Column(sa.TIMESTAMP(), default=sa.func.now())
    updated_at = sa.Column(sa.TIMESTAMP(), onupdate=sa.func.now())

    def save(self):
        db.session.add(self)    #pylint:disable=E1101
        db.session.commit()     #pylint:disable=E1101
        return self

    def to_dict(self):
        raise NotImplementedError


class User(BaseModel, UserMixin, db.Model):
    __tablename__ = 'users'

    name = sa.Column(sa.String(50), nullable=False)
    email = sa.Column(sa.String(320), unique=True, nullable=False)
    link_to_facebook = sa.Column(sa.Boolean(), default=False)
    link_to_google = sa.Column(sa.Boolean(), default=False)
    occupation = sa.Column(sa.String(30))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'occupation': self.occupation,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


class Post(BaseModel, db.Model):
    __tablename__ = 'posts'

    title = sa.Column(sa.String(100), nullable=False)
    summary = sa.Column(sa.String(200), nullable=False)
    body = sa.Column(sa.String(1500), nullable=False)
    author_id = sa.Column(sa.Integer(), sa.ForeignKey('users.id'), nullable=False)
    author = sa.orm.relationship(User, backref='posts')
    n_likes = sa.Column(sa.Integer(), default=0, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'body': self.body,
            'author': self.author.to_dict(),
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


class Like(BaseModel, db.Model):
    __tablename__ = 'likes'

    user_id = sa.Column(sa.Integer(), sa.ForeignKey('users.id'), nullable=False)
    user = sa.orm.relationship(User, backref='likes')
    post_id = sa.Column(sa.Integer(), sa.ForeignKey('posts.id'), nullable=False)
    post = sa.orm.relationship(Post, backref='likes')


def init_app(app):
    db.init_app(app)
    Migrate(app, db)
