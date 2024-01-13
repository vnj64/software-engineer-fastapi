from fastapi.testclient import TestClient

from app.main import server

client = TestClient(server)


def test_register_user():
    data = {"username": "testuser", "password": "testpassword"}
    response = client.post("/register", data=data)
    assert response.status_code == 200
    assert response.json() == {"username": "testuser"}


def test_login_and_get_token():
    data = {"username": "testuser1", "password": "testpassword"}
    response_register = client.post("/register", data=data)
    assert response_register.status_code == 200

    response_login = client.post("/token", data=data)
    assert response_login.status_code == 200
    assert "access_token" in response_login.json()
    assert response_login.json()["token_type"] == "bearer"
