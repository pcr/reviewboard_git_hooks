from django.db import models

class SSH(models.Model):
    name = models.CharField(max_length=30)
    ssh_rsa = models.CharField(max_length=1000)
    def __str__(self):
        return self.name
