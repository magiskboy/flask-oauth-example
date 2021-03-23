from sqlalchemy.orm import load_only, joinedload
from flask.views import MethodView
from flask import (
    request,
    Blueprint,
    abort,
)
from flask_login import (
    login_required,
    current_user,
)

from .models import (
    Post,
    User,
    Like,
    db,
)


class PostAPI(MethodView):
    def _create_like_string_from_post(self, post):
        like_string = ''
        n_likes = post.n_likes
        if n_likes:
            users = db.session.query(User).join(        #pylint:disable=E1101
                Like,
                User.id == Like.user_id
            ).filter(
                Like.post_id==post.id,
            ).limit(2).all()
            if n_likes == 1:
                like_string = users[0].name
            else:
                like_string = f'{users[0].name}, {users[1].name}'

            if n_likes > 2:
                like_string += f', and {n_likes-2} other people'

            like_string += ' liked this post.'
        return like_string

    def get(self, post_id):
        if post_id is None:
            loaded_fields = load_only('id', 'title', 'summary', 'n_likes', 'author_id',)

            author_id = request.args.get('author_id', type=int)
            if author_id is not None:
                query = db.session.query(Post).filter(      #pylint:disable=E1101
                    Post.author_id == author_id
                )
            else:
                query = db.session.query(Post)     #pylint:disable=E1101

            query = query.options(loaded_fields).order_by(Post.created_at.desc())

            page = request.args.get('page', default=0, type=int)
            per_page = min(request.args.get('per_page', default=10, type=int), 50)

            query = query.offset(page * per_page).limit(per_page)

            posts = []
            for item in query:
                posts.append({
                    'id': item.id,
                    'title': item.title,
                    'summary': item.summary,
                    'like_string': self._create_like_string_from_post(item),
                    'author_id': item.author_id,
                    'author_name': item.author.name,
                })
            return {
                'posts': posts
            }, 200


        # get a specify post
        post = Post.query.get(post_id)
        if not post:
            return {
                'message': 'Post not found',
            }, 404
        return {
            'data': {
                **post.to_dict(),
                'like_string': self._create_like_string_from_post(post),
            },
        }, 200

    @login_required
    def post(self):
        data = request.json

        if not data:
            abort(400, 'Data is empty')

        title = data.get('title')
        if not title:
            abort(400, 'Title is required')

        body = data.get('body')
        if not body:
            abort(400, 'Body is required')

        post = Post(
            title=title,
            summary=body[:200] + '...' if len(body) > 200 else body,
            body=body,
            author_id=current_user.id,
        )
        post.save()

        return {
            'message': 'Post is created',
            'data': {
                'id': post.id,
            }
        }, 201


class LikeAPI(MethodView):
    def get(self, post_id):
        query = db.session.query(User).join(        #pylint:disable=E1101
            Like,
            User.id == Like.user_id
        ).filter(
            Like.post_id == post_id
        )

        users = []
        for item in query:
            users.append({
                'id': item.id,
                'name': item.name,
            })
        return {
            'users': users,
        }


bp = Blueprint('post', __name__)

post_view = PostAPI.as_view('post_view')
bp.add_url_rule('', defaults={'post_id': None}, view_func=post_view, methods=['GET',])
bp.add_url_rule('', view_func=post_view, methods=['POST'])
bp.add_url_rule('/<int:post_id>', view_func=post_view, methods=['GET',])

like_view = LikeAPI.as_view('like_view')
bp.add_url_rule('/<int:post_id>/likes', view_func=like_view, methods=['GET',])
