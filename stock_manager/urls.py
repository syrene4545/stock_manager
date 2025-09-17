from django.urls import path
from . import views
from .views import audit_log_view
from django.contrib.auth import views as auth_views
from .views import landing_view
from .views import register_view
from .views import dashboard_view
from .views import registration_pending_view

urlpatterns = [
    path('register/', register_view, name='register'),
    path('', landing_view, name='landing'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='landing'), name='logout'),
    path('registration/pending/', registration_pending_view, name='registration_pending'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('transaction/add/', views.add_transaction, name='add_transaction'),
    path('purchase/add/', views.add_purchase, name='add_purchases'),
    path('sale/add/', views.add_sale, name='add_sales'),
    path('count/session/add/', views.add_stock_count_session, name='add_stock_count_session'),
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('inventory_summary/', views.inventory_summary, name='inventory_summary'),
    path('audit-log/', audit_log_view, name='audit_log'),
    path('sales/receipt/<str:document_number>/', views.sale_receipt, name='sale_receipt'),
    path('purchases/invoice/<str:document_number>/', views.purchase_invoice, name='purchase_invoice'),
    


]
