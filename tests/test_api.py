import asyncio

import httpx

from app.main import app


def request(method: str, path: str, **kwargs) -> httpx.Response:
    async def run() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(run())


def test_health() -> None:
    response = request("GET", "/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_get_existing_order() -> None:
    response = request("GET", "/orders/202609070001")
    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"
    assert response.json()["after_sale_status"] == "NONE"


def test_get_logistics() -> None:
    response = request("GET", "/orders/202609070001/logistics")
    assert response.status_code == 200
    assert response.json()["status"] == "SIGNED"


def test_unknown_order_returns_structured_404() -> None:
    response = request("GET", "/orders/209901010001")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
    assert response.json()["request_id"]


def test_create_after_sale_and_idempotent_replay() -> None:
    payload = {
        "order_no": "202609070001",
        "type": "QUALITY_REFUND",
        "reason": "商品有质量问题",
        "idempotency_key": "202609070001-quality-test",
    }
    first = request("POST", "/after-sales/applications", json=payload)
    assert first.status_code == 201
    application_id = first.json()["application_id"]

    replay = request("POST", "/after-sales/applications", json=payload)
    assert replay.status_code == 200
    assert replay.headers["X-Idempotent-Replay"] == "true"
    assert replay.json()["application_id"] == application_id


def test_pending_payment_order_cannot_create_after_sale() -> None:
    payload = {
        "order_no": "202609070003",
        "type": "RETURN_REFUND",
        "reason": "不想要了",
        "idempotency_key": "202609070003-return-test",
    }
    response = request("POST", "/after-sales/applications", json=payload)
    assert response.status_code == 409
    assert response.json()["code"] == "BUSINESS_CONFLICT"


def test_special_product_cannot_be_auto_submitted() -> None:
    payload = {
        "order_no": "202609070002",
        "type": "QUALITY_REFUND",
        "reason": "定制商品有质量问题",
        "idempotency_key": "202609070002-quality-test",
    }
    response = request("POST", "/after-sales/applications", json=payload)
    assert response.status_code == 409
    assert response.json()["code"] == "BUSINESS_CONFLICT"
    assert "转人工审核" in response.json()["message"]

def test_active_after_sale_lookup_returns_false_when_none() -> None:
    response = request("GET", "/orders/202609070003/after-sales/active")
    assert response.status_code == 200
    assert response.json() == {
        "order_no": "202609070003",
        "has_active_application": False,
        "application": None,
    }


def test_active_after_sale_lookup_returns_existing_application() -> None:
    # 同一模块前面的幂等测试已为该订单创建 PENDING_REVIEW 申请，
    # 本用例只验证按订单查询能读取该申请，避免再次创建造成业务冲突。
    response = request("GET", "/orders/202609070001/after-sales/active")
    assert response.status_code == 200
    body = response.json()
    assert body["has_active_application"] is True
    assert body["application"]["order_no"] == "202609070001"
    assert body["application"]["status"] == "PENDING_REVIEW"