from django.urls import path

from . import views

app_name = "chatbot"

urlpatterns = [
    path("reply/", views.reply, name="reply"),
]
