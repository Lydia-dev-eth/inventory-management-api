from django.urls import path
from .views import   OrderCancelView, OrderDetailView, OrderView,ConfirmOrderView

urlpatterns = [
    path("", OrderView.as_view(), name="order-list-create"),
    path("<int:pk>/", OrderDetailView.as_view(), name="order-detail"),
    path("<int:pk>/cancel/", OrderCancelView.as_view(), name="order-cancel"),
    path("<int:pk>/confirm/", ConfirmOrderView.as_view(), name="order-confirm"),
]