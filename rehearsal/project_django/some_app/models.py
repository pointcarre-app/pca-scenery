from django.db import models

# Create your models here.


class SomeModel(models.Model): 
    some_field = models.CharField(max_length=64, default="")
