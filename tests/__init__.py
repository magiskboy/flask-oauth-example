from unittest import TestCase
import pytest


@pytest.mark.usefixtures('client')
class APITestCase(TestCase):
    client = None

    def call_api(self, url, method='GET', params=None, data=None):
        ...
