from fastapi.testclient import TestClient
from fastapi import status
from app.main import server

client = TestClient(server)


def test_register():
    data = {"username": "testuser1", "password": "testpassword"}
    response = client.post("/register", data=data)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"username": "testuser1"}
