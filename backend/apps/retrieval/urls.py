from django.urls import path

from apps.retrieval.views import SemanticRetrievalAPIView

urlpatterns = [
    path('search/', SemanticRetrievalAPIView.as_view(), name='retrieval-search'),
]
