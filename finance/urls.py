from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('transactions/', views.transactions_view, name='transactions'),
    path('transactions/add/', views.add_transaction_view, name='add_transaction'),
    path('transactions/<int:pk>/edit/', views.edit_transaction_view, name='edit_transaction'),
    path('transactions/<int:pk>/delete/', views.delete_transaction_view, name='delete_transaction'),
    
    path('property/', views.property_view, name='property'),
    path('property/edit/', views.property_view, name='edit_property'),
    path('assets/add/', views.add_asset_view, name='add_asset'),
    path('assets/<int:pk>/edit/', views.edit_asset_view, name='edit_asset'),
    path('assets/<int:pk>/delete/', views.delete_asset_view, name='delete_asset'),
    
    path('liabilities/<int:pk>/edit/', views.edit_liability_view, name='edit_liability'),
    path('financial-plan/', views.financial_plan_view, name='financial_plan'),
    path('financial-plan/<int:pk>/edit/', views.edit_financial_plan_view, name='edit_financial_plan'),
    
    path('profile/', views.profile_view, name='profile'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Admin User Handling Console
    path('admin-panel/users/', views.manage_users_view, name='manage_users'),
    path('admin-panel/users/create/', views.create_user_view, name='admin_create_user'),
    path('admin-panel/users/<int:user_id>/edit/', views.edit_user_view, name='admin_edit_user'),
    path('admin-panel/users/<int:user_id>/toggle-status/', views.toggle_user_status_view, name='admin_toggle_user_status'),
    path('admin-panel/users/<int:user_id>/delete/', views.delete_user_view, name='admin_delete_user'),
    path('admin-panel/users/<int:user_id>/reset-password/', views.reset_user_password_view, name='admin_reset_user_password'),
    path('admin-panel/users/<int:user_id>/view/', views.user_detail_view, name='admin_user_detail'),
]
