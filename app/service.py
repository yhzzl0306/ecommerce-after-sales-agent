from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .models import (
    AfterSaleApplication,
    AfterSaleApplicationCreate,
    ActiveAfterSaleLookup,
    AfterSaleStatus,
    OrderSummary,
)
from .repository import DomainConflictError, InMemoryRepository


class AfterSalesService:
    def __init__(self, repository: InMemoryRepository) -> None:
        self.repository = repository

    def get_order_summary(self, order_no: str) -> OrderSummary:
        order = self.repository.get_order(order_no)
        return OrderSummary(
            order_no=order.order_no,
            status=order.status,
            pay_amount=order.pay_amount,
            product_type=order.product_type,
            product_name=order.product_name,
            created_at=order.created_at,
            signed_at=order.signed_at,
            after_sale_status=order.after_sale_status,
        )

    def get_active_application(self, order_no: str) -> ActiveAfterSaleLookup:
        # 先校验订单是否存在，避免把未知订单误判为“没有售后”。
        self.repository.get_order(order_no)
        application = self.repository.find_active_application(order_no)
        return ActiveAfterSaleLookup(
            order_no=order_no,
            has_active_application=application is not None,
            application=application,
        )

    def create_application(self, payload: AfterSaleApplicationCreate) -> tuple[AfterSaleApplication, bool]:
        existing_by_key = self.repository.find_application_by_key(payload.idempotency_key)
        if existing_by_key:
            if existing_by_key.order_no != payload.order_no or existing_by_key.type != payload.type:
                raise DomainConflictError("幂等键已经绑定到其他售后请求")
            return existing_by_key, True

        order = self.repository.get_order(payload.order_no)
        if order.status != "COMPLETED":
            raise DomainConflictError("只有已完成订单才能提交售后申请")

        # 特殊/定制商品不能由自动化流程直接创建售后申请，
        # 必须转人工核验商品属性、质量凭证和平台特殊政策。
        if order.product_type == "SPECIAL":
            raise DomainConflictError("特殊定制商品需要转人工审核，不能自动创建售后申请")

        active = self.repository.find_active_application(payload.order_no)
        if active:
            raise DomainConflictError(f"订单已有处理中售后申请：{active.application_id}")

        application = AfterSaleApplication(
            application_id=f"AS{uuid4().hex[:12].upper()}",
            order_no=payload.order_no,
            type=payload.type,
            reason=payload.reason,
            status=AfterSaleStatus.PENDING_REVIEW,
            idempotency_key=payload.idempotency_key,
            created_at=datetime.now(timezone.utc),
        )
        return self.repository.save_application(application), False
