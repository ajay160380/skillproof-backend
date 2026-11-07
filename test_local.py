import requests

BASE_URL = "http://127.0.0.1:8080/api"

if __name__ == '__main__':
    # Login as test_bot_9992
    res = requests.post(f"{BASE_URL}/auth/register/", json={
        "username": "test_bot_local",
        "email": "test_bot_local@example.com",
        "password": "Password123!",
        "full_name": "Test Bot Local",
        "role": "candidate"
    })
    if res.status_code == 400:
        res = requests.post(f"{BASE_URL}/auth/login/", json={
            "email": "test_bot_local@example.com",
            "password": "Password123!"
        })

    token = res.json().get('access')
    headers = {"Authorization": f"Bearer {token}"}
    print(token)

    print("Uploading image...")
    files = {'avatar_url': ('test.png', b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82', 'image/png')}
    res = requests.patch(f"{BASE_URL}/auth/me/", headers=headers, files=files)
    print("Upload Response:", res.status_code)

