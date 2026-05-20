from fastapi.testclient import TestClient


def test_create_department_and_get_tree(client: TestClient) -> None:
    r = client.post("/departments/", json={"name": " HQ "})
    assert r.status_code == 201
    root_id = r.json()["id"]

    r = client.post("/departments/", json={"name": "Engineering", "parent_id": root_id})
    assert r.status_code == 201
    eng_id = r.json()["id"]

    r = client.post(
        f"/departments/{eng_id}/employees/",
        json={"full_name": "Jane Doe", "position": "Engineer"},
    )
    assert r.status_code == 201

    r = client.get(f"/departments/{root_id}", params={"depth": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["department"]["name"] == "HQ"
    assert len(body["children"]) == 1
    assert body["children"][0]["department"]["name"] == "Engineering"
    assert len(body["children"][0]["employees"]) == 1
    assert body["children"][0]["employees"][0]["full_name"] == "Jane Doe"


def test_duplicate_department_name_conflict(client: TestClient) -> None:
    client.post("/departments/", json={"name": "A"})
    r = client.post("/departments/", json={"name": "a"})
    assert r.status_code == 409


def test_move_department_cycle_conflict(client: TestClient) -> None:
    a = client.post("/departments/", json={"name": "A"}).json()["id"]
    b = client.post("/departments/", json={"name": "B", "parent_id": a}).json()["id"]
    c = client.post("/departments/", json={"name": "C", "parent_id": b}).json()["id"]
    r = client.patch(f"/departments/{a}", json={"parent_id": c})
    assert r.status_code == 409


def test_delete_reassign_moves_employees_and_children(client: TestClient) -> None:
    root = client.post("/departments/", json={"name": "Root"}).json()["id"]
    to_keep = client.post("/departments/", json={"name": "Keep", "parent_id": root}).json()[
        "id"
    ]
    to_del = client.post("/departments/", json={"name": "Remove", "parent_id": root}).json()[
        "id"
    ]
    child = client.post("/departments/", json={"name": "Child", "parent_id": to_del}).json()[
        "id"
    ]
    client.post(
        f"/departments/{to_del}/employees/",
        json={"full_name": "Worker", "position": "Staff"},
    )

    r = client.delete(
        f"/departments/{to_del}",
        params={"mode": "reassign", "reassign_to_department_id": to_keep},
    )
    assert r.status_code == 204

    r = client.get(f"/departments/{to_keep}", params={"depth": 1})
    assert r.status_code == 200
    assert any(c["department"]["id"] == child for c in r.json()["children"])
    assert len(r.json()["employees"]) == 1
