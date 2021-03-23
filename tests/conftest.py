import pytest

from app import models, create_app


@pytest.fixture
def client(request):
    app = create_app('testing')

    with app.app_context():
        models.db.create_all()

        with app.test_client() as _client:
            if request.cls is not None:
                request.cls.client = _client
            yield _client

        models.db.drop_all()
