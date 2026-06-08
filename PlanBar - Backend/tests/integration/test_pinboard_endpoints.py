import io


def test_create_thread(client, auth_headers):
    response = client.post(
        "/api/v1/pinboard/threads",
        json={"title": "Test Thread"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Thread"
    assert data["is_pinned"] is False
    assert data["message_count"] == 0
    assert "id" in data


def test_list_threads(client, auth_headers):
    client.post(
        "/api/v1/pinboard/threads",
        json={"title": "Thread 1"},
        headers=auth_headers,
    )
    client.post(
        "/api/v1/pinboard/threads",
        json={"title": "Thread 2"},
        headers=auth_headers,
    )

    response = client.get("/api/v1/pinboard/threads", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2


def test_get_thread(client, auth_headers):
    create_resp = client.post(
        "/api/v1/pinboard/threads",
        json={"title": "Single Thread"},
        headers=auth_headers,
    )
    thread_id = create_resp.json()["id"]

    response = client.get(f"/api/v1/pinboard/threads/{thread_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Single Thread"
    assert "messages" in data
    assert data["messages"] == []


def test_update_thread(client, auth_headers):
    create_resp = client.post(
        "/api/v1/pinboard/threads",
        json={"title": "Original Title"},
        headers=auth_headers,
    )
    thread_id = create_resp.json()["id"]

    response = client.put(
        f"/api/v1/pinboard/threads/{thread_id}",
        json={"title": "Updated Title"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"


def test_pin_thread(client, auth_headers):
    create_resp = client.post(
        "/api/v1/pinboard/threads",
        json={"title": "Pinnable Thread"},
        headers=auth_headers,
    )
    thread_id = create_resp.json()["id"]

    response = client.put(
        f"/api/v1/pinboard/threads/{thread_id}",
        json={"is_pinned": True},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["is_pinned"] is True


def test_delete_thread(client, auth_headers):
    create_resp = client.post(
        "/api/v1/pinboard/threads",
        json={"title": "To Delete"},
        headers=auth_headers,
    )
    thread_id = create_resp.json()["id"]

    response = client.delete(f"/api/v1/pinboard/threads/{thread_id}", headers=auth_headers)
    assert response.status_code == 204


def test_get_thread_not_found(client, auth_headers):
    response = client.get("/api/v1/pinboard/threads/99999", headers=auth_headers)
    assert response.status_code == 404


def test_update_thread_not_found(client, auth_headers):
    response = client.put(
        "/api/v1/pinboard/threads/99999",
        json={"title": "Nope"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_delete_thread_not_found(client, auth_headers):
    response = client.delete("/api/v1/pinboard/threads/99999", headers=auth_headers)
    assert response.status_code == 404


def test_create_message(client, auth_headers):
    thread_resp = client.post(
        "/api/v1/pinboard/threads",
        json={"title": "Message Thread"},
        headers=auth_headers,
    )
    thread_id = thread_resp.json()["id"]

    response = client.post(
        f"/api/v1/pinboard/threads/{thread_id}/messages",
        json={"content": "Hello World"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "Hello World"
    assert data["thread_id"] == thread_id
    assert "author_name" in data


def test_list_messages(client, auth_headers):
    thread_resp = client.post(
        "/api/v1/pinboard/threads",
        json={"title": "List Messages Thread"},
        headers=auth_headers,
    )
    thread_id = thread_resp.json()["id"]

    client.post(
        f"/api/v1/pinboard/threads/{thread_id}/messages",
        json={"content": "Message 1"},
        headers=auth_headers,
    )
    client.post(
        f"/api/v1/pinboard/threads/{thread_id}/messages",
        json={"content": "Message 2"},
        headers=auth_headers,
    )

    response = client.get(
        f"/api/v1/pinboard/threads/{thread_id}/messages",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_create_message_thread_not_found(client, auth_headers):
    response = client.post(
        "/api/v1/pinboard/threads/99999/messages",
        json={"content": "Orphan message"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_list_messages_thread_not_found(client, auth_headers):
    response = client.get(
        "/api/v1/pinboard/threads/99999/messages",
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_update_message(client, auth_headers):
    thread_resp = client.post(
        "/api/v1/pinboard/threads",
        json={"title": "Update Message Thread"},
        headers=auth_headers,
    )
    thread_id = thread_resp.json()["id"]

    msg_resp = client.post(
        f"/api/v1/pinboard/threads/{thread_id}/messages",
        json={"content": "Original Content"},
        headers=auth_headers,
    )
    message_id = msg_resp.json()["id"]

    response = client.put(
        f"/api/v1/pinboard/messages/{message_id}",
        json={"content": "Updated Content"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["content"] == "Updated Content"


def test_delete_message(client, auth_headers):
    thread_resp = client.post(
        "/api/v1/pinboard/threads",
        json={"title": "Delete Message Thread"},
        headers=auth_headers,
    )
    thread_id = thread_resp.json()["id"]

    msg_resp = client.post(
        f"/api/v1/pinboard/threads/{thread_id}/messages",
        json={"content": "Delete Me"},
        headers=auth_headers,
    )
    message_id = msg_resp.json()["id"]

    response = client.delete(
        f"/api/v1/pinboard/messages/{message_id}",
        headers=auth_headers,
    )
    assert response.status_code == 204


def test_update_message_not_found(client, auth_headers):
    response = client.put(
        "/api/v1/pinboard/messages/99999",
        json={"content": "Nope"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_delete_message_not_found(client, auth_headers):
    response = client.delete("/api/v1/pinboard/messages/99999", headers=auth_headers)
    assert response.status_code == 404


def test_upload_document(client, auth_headers):
    thread_resp = client.post(
        "/api/v1/pinboard/threads",
        json={"title": "Document Thread"},
        headers=auth_headers,
    )
    thread_id = thread_resp.json()["id"]

    msg_resp = client.post(
        f"/api/v1/pinboard/threads/{thread_id}/messages",
        json={"content": "Doc message"},
        headers=auth_headers,
    )
    message_id = msg_resp.json()["id"]

    response = client.post(
        f"/api/v1/pinboard/messages/{message_id}/documents",
        files={"file": ("test.txt", io.BytesIO(b"hello world"), "text/plain")},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["file_name"] == "test.txt"
    assert data["file_size"] == 11
    assert data["mime_type"] == "text/plain"


def test_upload_document_message_not_found(client, auth_headers):
    response = client.post(
        "/api/v1/pinboard/messages/99999/documents",
        files={"file": ("test.txt", io.BytesIO(b"data"), "text/plain")},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_download_document(client, auth_headers):
    thread_resp = client.post(
        "/api/v1/pinboard/threads",
        json={"title": "Download Thread"},
        headers=auth_headers,
    )
    thread_id = thread_resp.json()["id"]

    msg_resp = client.post(
        f"/api/v1/pinboard/threads/{thread_id}/messages",
        json={"content": "Download doc"},
        headers=auth_headers,
    )
    message_id = msg_resp.json()["id"]

    doc_resp = client.post(
        f"/api/v1/pinboard/messages/{message_id}/documents",
        files={"file": ("downloaded.txt", io.BytesIO(b"file content"), "text/plain")},
        headers=auth_headers,
    )
    document_id = doc_resp.json()["id"]

    response = client.get(
        f"/api/v1/pinboard/documents/{document_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.content == b"file content"


def test_download_document_not_found(client, auth_headers):
    response = client.get("/api/v1/pinboard/documents/99999", headers=auth_headers)
    assert response.status_code == 404


def test_delete_document(client, auth_headers):
    thread_resp = client.post(
        "/api/v1/pinboard/threads",
        json={"title": "Delete Doc Thread"},
        headers=auth_headers,
    )
    thread_id = thread_resp.json()["id"]

    msg_resp = client.post(
        f"/api/v1/pinboard/threads/{thread_id}/messages",
        json={"content": "Delete doc"},
        headers=auth_headers,
    )
    message_id = msg_resp.json()["id"]

    doc_resp = client.post(
        f"/api/v1/pinboard/messages/{message_id}/documents",
        files={"file": ("deleteme.txt", io.BytesIO(b"bye"), "text/plain")},
        headers=auth_headers,
    )
    document_id = doc_resp.json()["id"]

    response = client.delete(
        f"/api/v1/pinboard/documents/{document_id}",
        headers=auth_headers,
    )
    assert response.status_code == 204


def test_delete_document_not_found(client, auth_headers):
    response = client.delete("/api/v1/pinboard/documents/99999", headers=auth_headers)
    assert response.status_code == 404


def test_get_ws_token(client, auth_headers):
    response = client.get("/api/v1/pinboard/ws-token", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["expires_in"] == 1800


def test_pinned_threads_appear_first(client, auth_headers):
    resp_a = client.post(
        "/api/v1/pinboard/threads",
        json={"title": "Normal Thread"},
        headers=auth_headers,
    )
    thread_a_id = resp_a.json()["id"]

    resp_b = client.post(
        "/api/v1/pinboard/threads",
        json={"title": "Pinned Thread"},
        headers=auth_headers,
    )
    thread_b_id = resp_b.json()["id"]

    client.put(
        f"/api/v1/pinboard/threads/{thread_b_id}",
        json={"is_pinned": True},
        headers=auth_headers,
    )

    response = client.get("/api/v1/pinboard/threads", headers=auth_headers)
    data = response.json()
    pinned_indices = [i for i, t in enumerate(data) if t["is_pinned"]]
    unpinned_indices = [i for i, t in enumerate(data) if not t["is_pinned"]]
    if pinned_indices and unpinned_indices:
        assert max(pinned_indices) < min(unpinned_indices)
