from app.persistence.models import OrderModel
from app.persistence.repositories.base import BaseRepository


class OrderRepository(BaseRepository[OrderModel]):
    model = OrderModel
