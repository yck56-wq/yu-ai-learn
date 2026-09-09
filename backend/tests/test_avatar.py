from io import BytesIO
from urllib.parse import urlsplit

import pytest
from PIL import Image

from app.config import settings


def picture(format='PNG', size=(32, 32)):
    output = BytesIO()
    Image.new('RGB', size, '#4c8dff').save(output, format=format)
    return output.getvalue()


@pytest.fixture
def avatars(tmp_path, monkeypatch):
    monkeypatch.setitem(settings.__dict__, 'avatar_storage_dir', str(tmp_path))
    monkeypatch.setitem(settings.__dict__, 'public_base_url', 'https://api.example.test')
    return tmp_path


def test_avatar_and_nickname_persist_and_are_restored_on_login(client, login, avatars):
    headers, _ = login()
    response = client.post('/api/v1/user/avatar', headers=headers,
                           files={'file': ('avatar.png', picture(), 'image/png')},
                           data={'nickname': '  微信昵称  '})
    assert response.status_code == 200
    saved = response.json()['data']
    assert saved['nickname'] == '微信昵称'
    assert saved['avatar_url'].startswith('https://api.example.test/api/v1/user/avatars/')
    assert len(list(avatars.iterdir())) == 1
    image_response = client.get(urlsplit(saved['avatar_url']).path)
    assert image_response.status_code == 200
    assert image_response.headers['content-type'] == 'image/png'
    with Image.open(BytesIO(image_response.content)) as image:
        assert image.size == (32, 32)
    _, restored = login()
    assert restored['avatar_url'] == saved['avatar_url']
    assert restored['nickname'] == '微信昵称'
    assert client.get('/api/v1/user/profile', headers=headers).json()['data'] == saved


@pytest.mark.parametrize('content,status', [(b'', 422), (b'not an image', 422), (b'x' * (5 * 1024 * 1024 + 1), 413)], ids=['empty', 'invalid-image', 'oversized'])
def test_invalid_upload_keeps_existing_profile(client, login, avatars, content, status):
    headers, original = login()
    response = client.post('/api/v1/user/avatar', headers=headers,
                           files={'file': ('fake.png', content, 'image/png')}, data={'nickname': '不应保存'})
    assert response.status_code == status
    profile = client.get('/api/v1/user/profile', headers=headers).json()['data']
    assert profile['nickname'] == original['nickname']
    assert profile['avatar_url'] == original['avatar_url']
    assert list(avatars.iterdir()) == []


@pytest.mark.parametrize('nickname', ['', '  ', '字' * 101, '学习\t者'])
def test_invalid_nickname_does_not_store_avatar(client, login, avatars, nickname):
    headers, _ = login()
    response = client.post('/api/v1/user/avatar', headers=headers,
                           files={'file': ('avatar.png', picture(), 'image/png')}, data={'nickname': nickname})
    assert response.status_code == 422
    assert list(avatars.iterdir()) == []


def test_avatar_upload_requires_identity(client, avatars):
    response = client.post('/api/v1/user/avatar', files={'file': ('a.png', picture(), 'image/png')})
    assert response.status_code == 401
    assert list(avatars.iterdir()) == []


@pytest.mark.parametrize('filename', ['missing.png', 'a' * 32 + '.png', '..%5C.env', '%2e%2e%5C.env'])
def test_avatar_route_rejects_unknown_files_and_traversal(client, avatars, filename):
    assert client.get('/api/v1/user/avatars/' + filename).status_code == 404


def test_avatar_only_update_preserves_nickname_and_other_accounts(client, login, avatars):
    headers, _ = login()
    bob_headers, bob = login('bob')
    client.put('/api/v1/user/profile', headers=headers, json={'nickname': '保留昵称'})
    saved = client.post('/api/v1/user/avatar', headers=headers,
                        files={'file': ('../../wrong.txt', picture('JPEG', (1200, 800)), 'text/plain')})
    assert saved.status_code == 200
    assert saved.json()['data']['nickname'] == '保留昵称'
    image_response = client.get(urlsplit(saved.json()['data']['avatar_url']).path)
    with Image.open(BytesIO(image_response.content)) as image:
        assert image.size == (512, 341)
        assert not image.getexif()
    unchanged = client.get('/api/v1/user/profile', headers=bob_headers).json()['data']
    assert unchanged['avatar_url'] == bob['avatar_url']
