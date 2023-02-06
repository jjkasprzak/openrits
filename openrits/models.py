from django.db import models


class ItemCategory(models.Model):
    name = models.CharField(max_length=127)
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True)


class ItemCategoryProperty(models.Model):
    name = models.CharField(max_length=127)
    category = models.ForeignKey(ItemCategory, on_delete=models.CASCADE)


class Item(models.Model):
    name = models.CharField(max_length=127)
    amount = models.PositiveIntegerField()
    archived = models.BooleanField(default=False)
    category = models.ForeignKey(
        ItemCategory, on_delete=models.SET_NULL, null=True, blank=True
    )


class ItemPropertyValue(models.Model):
    value = models.TextField()
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    property = models.ForeignKey(ItemCategoryProperty, on_delete=models.CASCADE)


class Customer(models.Model):
    name = models.CharField(max_length=127)
    surname = models.CharField(max_length=127)
    email = models.EmailField()


class CustomerProperty(models.Model):
    name = models.CharField(max_length=127)


class CustomerPropertyValue(models.Model):
    value = models.TextField()
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    property = models.ForeignKey(CustomerProperty, on_delete=models.CASCADE)


class Rent(models.Model):
    created = models.DateTimeField()
    start = models.DateField()
    end = models.DateField()
    issued = models.DateTimeField(null=True, blank=True)
    returned = models.DateTimeField(null=True, blank=True)


class RentProperty(models.Model):
    name = models.CharField(max_length=127)


class RentPropertyValue(models.Model):
    value = models.TextField()
    rent = models.ForeignKey(Rent, on_delete=models.CASCADE)
    property = models.ForeignKey(RentProperty, on_delete=models.CASCADE)


class RentItems(models.Model):
    amount = models.PositiveIntegerField()
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True)
    rent = models.ForeignKey(Rent, models.ForeignKey(Rent, on_delete=models.CASCADE))
