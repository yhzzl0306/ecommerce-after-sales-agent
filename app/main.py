from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from .models import AfterSaleApplication, AfterSaleApplicationCreate, ErrorResponse
from .repository import DomainConflictError, DomainNotFoundError, InMemoryRepository
from .service import AfterSalesService

app = FastAPI(
    title="After-sales Tool Service",
    version="0.1.0",
    description="供 Dify 调用的电商售后查询与申请工具服务。当前使用内存测试数据。",
)
repository = InMemoryRepository()
service = AfterSalesService(repository)


def request_id(request: Request) -> str:
    return request.headers.get("X-Request-ID") or uuid4().hex


@app.exception_handler(DomainNotFoundError)
async def handle_not_found(request: Request, exc: DomainNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=ErrorResponse(code="NOT_FOUND", message=str(exc), request_id=request_id(request)).model_dump(),
    )


@app.exception_handler(DomainConflictError)
async def handle_conflict(request: Request, exc: DomainConflictError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=ErrorResponse(code="BUSINESS_CONFLICT", message=str(exc), request_id=request_id(request)).model_dump(),
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "after-sales-tool-service", "version": "0.1.0"}


@app.get("/orders/{order_no}")
def get_order(order_no: str):
    return service.get_order_summary(order_no)


@app.get("/orders/{order_no}/logistics")
def get_logistics(order_no: str):
    return repository.get_logistics(order_no)

@app.get("/orders/{order_no}/lookup")
def lookup_order(order_no: str):
    """给 Dify 使用的稳定订单查询接口。"""

    if len(order_no) != 12 or not order_no.isdigit():
        return {
            "found": False,
            "order_no": order_no,
            "error_code": "INVALID_ORDER_NO",
            "message": "订单号格式不正确，订单号应为 12 位数字",
        }

    try:
        order = service.get_order_summary(order_no)
    except DomainNotFoundError:
        return {
            "found": False,
            "order_no": order_no,
            "error_code": "NOT_FOUND",
            "message": "没有查询到该订单，请核对订单号后重试",
        }

    return {
        "found": True,
        "order_no": order.order_no,
        "status": order.status,
        "pay_amount": order.pay_amount,
        "product_type": order.product_type,
        "product_name": order.product_name,
        "created_at": order.created_at,
        "signed_at": order.signed_at,
        "after_sale_status": order.after_sale_status,
        "error_code": None,
        "message": None,
    }

@app.get("/orders/{order_no}/after-sales/active")
def get_active_after_sale(order_no: str):
    return service.get_active_application(order_no)


@app.post("/after-sales/applications", status_code=status.HTTP_201_CREATED)
def create_after_sale(payload: AfterSaleApplicationCreate):
    application, reused = service.create_application(payload)
    if reused:
        response = JSONResponse(status_code=status.HTTP_200_OK, content=application.model_dump(mode="json"))
        response.headers["X-Idempotent-Replay"] = "true"
        return response
    return application


@app.get("/after-sales/applications/{application_id}")
def get_after_sale(application_id: str) -> AfterSaleApplication:
    return repository.get_application(application_id)
