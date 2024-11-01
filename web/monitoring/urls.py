"""monitoring URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from dashboard.views import IndexView, DashboardViewOracle, DashboardViewCouchbase, DashboardViewCassandra

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", IndexView.as_view()),
    path('ajax/get-oracle-status/', DashboardViewOracle.get_data, name='get-oracle-status'),
    path('ajax/get-couchbase-status/', DashboardViewCouchbase.get_data, name='get-couchbase-status'),
    path('ajax/get-cassandra-status/', DashboardViewCassandra.get_data, name='get-cassandra-status')
]
