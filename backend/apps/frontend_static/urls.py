from django.urls import path, re_path

from apps.frontend_static.views import serve_frontend_page, serve_frontend_public_asset

urlpatterns = [
    path('', serve_frontend_page, {'path': ''}, name='frontend-home'),
    path('login', serve_frontend_page, {'path': 'login'}, name='frontend-login'),
    path('dashboard', serve_frontend_page, {'path': 'dashboard'}, name='frontend-dashboard'),
    path(
        'dashboard/employee-space',
        serve_frontend_page,
        {'path': 'dashboard/employee-space'},
        name='frontend-employee-space',
    ),
    re_path(
        r'^(?P<asset_path>(?!api/|admin/|_next/).+\.(?:ico|svg|png|jpg|jpeg|webp|txt|json))$',
        serve_frontend_public_asset,
        name='frontend-public-asset',
    ),
]
