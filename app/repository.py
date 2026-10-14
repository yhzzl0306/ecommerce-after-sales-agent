from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

from .models import (
    AfterSaleApplication,
    AfterSaleStatus,
    Logistics,
    LogisticsStatus,
    Order,
    OrderStatus,
    ProductType,
)


class DomainNotFoundError(Exception):
    """请求的业务对象不存在。"""


class DomainConflictError(Exception):
    """请求与当前业务状态冲突。"""


class InMemoryRepository:
    """第一版测试仓储，后续可替换成 mall HTTP 客户端或数据库仓储。"""

    def __init__(self) -> None:
        self.orders: Dict[str, Order] = {}
        self.logistics: Dict[str, Logistics] = {}
        self.applications_by_key: Dict[str, AfterSaleApplication] = {}
        self.applications_by_id: Dict[str, AfterSaleApplication] = {}
        self._seed()

    def _seed(self) -> None:
        now = datetime.now(timezone.utc)
        self.orders = {
            "202609070001": Order(
                order_no="202609070001",
                status=OrderStatus.COMPLETED,
                pay_amount=99.90,
                product_type=ProductType.NORMAL,
                product_name="示例蓝牙耳机",
                created_at=now,
                signed_at=now,
            ),
            "202609070002": Order(
                order_no="202609070002",
                status=OrderStatus.COMPLETED,
                pay_amount=199.00,
                product_type=ProductType.SPECIAL,
                product_name="定制商品",
                created_at=now,
                signed_at=now,
            ),
            "202609070003": Order(
                order_no="202609070003",
                status=OrderStatus.PENDING_PAYMENT,
                pay_amount=49.90,
                product_type=ProductType.NORMAL,
                product_name="示例数据线",
                created_at=now,
            ),
        }
        self.logistics = {
            "202609070001": Logistics(
                order_no="202609070001",
                status=LogisticsStatus.SIGNED,
                carrier="示例物流",
                tracking_no="SF1234567890",
                signed_at=now,
            ),
            "202609070002": Logistics(
                order_no="202609070002",
                status=LogisticsStatus.SIGNED,
                carrier="示例物流",
                tracking_no="YT1234567890",
                signed_at=now,
            ),
            "202609070003": Logistics(
                order_no="202609070003",
                status=LogisticsStatus.NOT_SHIPPED,
            ),
        }

    def get_order(self, order_no: str) -> Order:
        try:
            return self.orders[order_no]
        except KeyError as exc:
            raise DomainNotFoundError(f"订单 {order_no} 不存在") from exc

    def get_logistics(self, order_no: str) -> Logistics:
        self.get_order(order_no)
        try:
            return self.logistics[order_no]
        except KeyError as exc:
            raise DomainNotFoundError(f"订单 {order_no} 暂无物流信息") from exc

    def find_application_by_key(self, key: str) -> Optional[AfterSaleApplication]:
        return self.applications_by_key.get(key)

    def find_active_application(self, order_no: str) -> Optional[AfterSaleApplication]:
        for application in self.applications_by_id.values():
            if application.order_no == order_no and application.status in {
                AfterSaleStatus.PENDING_REVIEW,
                AfterSaleStatus.APPROVED,
                AfterSaleStatus.REFUNDING,
            }:
                return application
        return None

    def save_application(self, application: AfterSaleApplication) -> AfterSaleApplication:
        self.applications_by_key[application.idempotency_key] = application
        self.applications_by_id[application.application_id] = application
        order = self.orders[application.order_no]
        self.orders[application.order_no] = order.model_copy(
            update={"after_sale_status": application.status}
        )
        return application

    def get_application(self, application_id: str) -> AfterSaleApplication:
        try:
            return self.applications_by_id[application_id]
        except KeyError as exc:
            raise DomainNotFoundError(f"售后申请 {application_id} 不存在") from exc
