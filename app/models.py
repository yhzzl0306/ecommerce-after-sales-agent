from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class OrderStatus(str, Enum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ProductType(str, Enum):
    NORMAL = "NORMAL"
    SPECIAL = "SPECIAL"


class AfterSaleType(str, Enum):
    QUALITY_REFUND = "QUALITY_REFUND"
    LOGISTICS_ISSUE = "LOGISTICS_ISSUE"
    RETURN_REFUND = "RETURN_REFUND"


class AfterSaleStatus(str, Enum):
    NONE = "NONE"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REFUNDING = "REFUNDING"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"


class LogisticsStatus(str, Enum):
    NOT_SHIPPED = "NOT_SHIPPED"
    IN_TRANSIT = "IN_TRANSIT"
    SIGNED = "SIGNED"


class Order(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    order_no: str = Field(pattern=r"^\d{12}$", description="12 位订单号")
    status: OrderStatus
    pay_amount: float = Field(ge=0)
    product_type: ProductType
    product_name: str
    created_at: datetime
    signed_at: Optional[datetime] = None
    after_sale_status: AfterSaleStatus = AfterSaleStatus.NONE


class Logistics(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    order_no: str
    status: LogisticsStatus
    carrier: Optional[str] = None
    tracking_no: Optional[str] = None
    signed_at: Optional[datetime] = None


class OrderSummary(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    order_no: str
    status: OrderStatus
    pay_amount: float
    product_type: ProductType
    product_name: str
    created_at: datetime
    signed_at: Optional[datetime] = None
    after_sale_status: AfterSaleStatus


class AfterSaleApplicationCreate(BaseModel):
    order_no: str = Field(pattern=r"^\d{12}$")
    type: AfterSaleType
    reason: str = Field(min_length=2, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=128)


class AfterSaleApplication(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    application_id: str
    order_no: str
    type: AfterSaleType
    reason: str
    status: AfterSaleStatus
    idempotency_key: str
    created_at: datetime


class ActiveAfterSaleLookup(BaseModel):
    """按订单查询当前是否存在处理中售后申请。"""

    order_no: str
    has_active_application: bool
    application: Optional[AfterSaleApplication] = None


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str
