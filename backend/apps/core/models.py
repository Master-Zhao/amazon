from django.db import models


class AppendOnlyModel(models.Model):
    """Prevent instance-level mutation and deletion after an immutable row is saved."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk is not None and not self._state.adding:
            raise TypeError(f"{self.__class__.__name__} is append-only")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError(f"{self.__class__.__name__} is append-only")
