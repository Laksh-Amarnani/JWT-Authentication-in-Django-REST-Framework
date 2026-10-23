from unittest import mock

import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework.test import APIClient

# Every test gets a fresh, empty test database.
pytestmark = pytest.mark.django_db

PASSWORD = 'Str0ng-Pass-123'


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(username='alice', password=PASSWORD)


def login(api_client):
    return api_client.post('/api/login/', {'username': 'alice', 'password': PASSWORD})


def test_register_success(api_client):
    response = api_client.post('/api/register/', {'username': 'bob', 'password': PASSWORD})

    assert response.status_code == 201
    assert response.data == {'username': 'bob'}
    assert User.objects.get(username='bob').check_password(PASSWORD)


def test_register_duplicate_username(api_client, user):
    response = api_client.post('/api/register/', {'username': 'alice', 'password': PASSWORD})

    assert response.status_code == 400
    assert 'username' in response.data


def test_login_success(api_client, user):
    response = login(api_client)

    assert response.status_code == 200
    assert 'access' in response.data
    assert 'refresh' in response.data


def test_login_wrong_password(api_client, user):
    response = api_client.post('/api/login/', {'username': 'alice', 'password': 'wrong-password'})

    assert response.status_code == 401


def test_protected_without_token(api_client):
    response = api_client.get('/api/protected/')

    assert response.status_code == 401


def test_protected_with_valid_token(api_client, user):
    cache.clear()  # otherwise the view could return cached data and never call the mock
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {login(api_client).data["access"]}')
    fake_response = mock.Mock()
    fake_response.json.return_value = {'results': [{'name': 'Fake User'}]}

    with mock.patch('api.views.requests.get', return_value=fake_response) as fake_get:
        response = api_client.get('/api/protected/')

    assert response.status_code == 200
    assert response.data == {'you': 'alice', 'users': [{'name': 'Fake User'}]}
    fake_get.assert_called_once()


def test_protected_with_tampered_token(api_client, user):
    header, payload, signature = login(api_client).data['access'].split('.')
    # Change the first character: the last one partly holds padding bits, so changing it may not change the signature.
    new_char = 'A' if signature[0] != 'A' else 'B'
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {header}.{payload}.{new_char}{signature[1:]}')

    response = api_client.get('/api/protected/')

    assert response.status_code == 401


def test_refresh(api_client, user):
    refresh = login(api_client).data['refresh']

    response = api_client.post('/api/token/refresh/', {'refresh': refresh})

    assert response.status_code == 200
    assert 'access' in response.data
