from django.db import models
from django.core.validators import RegexValidator
from django.db.models.functions import Substr, StrIndex, Concat
from django.db.models import Value as V


class PropertyDefinition(models.Model):
    SUPPORTED_FIELDS = (
        models.IntegerField,
        models.FloatField,
        models.BooleanField,
        models.TextField,
        models.DateField,
    )

    name = models.CharField(max_length=127)
    property_type = models.CharField(
        max_length=63,
        choices=list((t.__name__, t.__name__) for t in SUPPORTED_FIELDS),
    )

    class Meta:
        abstract = True


class PropertyValue(models.Model):
    TYPE_DICT = {t.__name__: t for t in PropertyDefinition.SUPPORTED_FIELDS}

    value = models.TextField(default="")

    def getPropertyType(self) -> str:
        """
        Subclasses should override this and return
        their respective property type as str.
        """
        raise NotImplementedError()

    def deserialize(self) -> any:
        """
        Deserializes value using type returned by getProperty
        """
        property_type = self.getPropertyType()
        return PropertyValue.TYPE_DICT[property_type]().to_python(self.value)

    def serialize(self, object: any):
        """
        Serializes object and writes it to the value
        """
        self.value = str(object)

    class Meta:
        abstract = True


class ItemCategory(models.Model):
    name = models.CharField(max_length=127)
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True)
    lineage = models.TextField(
        editable=False,
        default=",",
        validators=[
            RegexValidator(regex=r"^,(?:\d+,)*\Z", message="Incorrect lineage format")
        ],
    )

    def get_descendants(self):
        return ItemCategory.objects.filter(lineage__contains=f",{self.pk},")

    def get_ancestors(self):
        qs = ItemCategory.objects.none()
        if self.lineage != ",":
            for cat_id in self.lineage[1:-1].split(","):
                qs = qs.union(ItemCategory.objects.filter(pk=int(cat_id)))
        return qs

    def get_properties(self):
        qs = ItemCategoryProperty.objects.none()
        for ancestor in self.get_ancestors():
            qs = qs.union(ancestor.itemcategoryproperty_set.all())
        qs = qs.union(self.itemcategoryproperty_set.all())
        return qs

    def update_parent(self, new_parent):
        new_lineage = ","
        new_parent_id = None
        if new_parent is not None:
            new_lineage = new_parent.lineage + f"{new_parent.pk},"
            new_parent_id = new_parent.pk
        ItemCategory.objects.filter(pk=self.pk).update(
            parent=new_parent_id, lineage=new_lineage
        )
        descendantsLineage = new_lineage + f"{self.pk},"
        searchStr = f",{self.pk},"
        self.get_descendants().update(
            lineage=Concat(
                V(descendantsLineage),
                Substr("lineage", StrIndex("lineage", V(searchStr)) + len(searchStr)),
            )
        )


class ItemCategoryProperty(PropertyDefinition):
    category = models.ForeignKey(ItemCategory, on_delete=models.CASCADE)


class Item(models.Model):
    name = models.CharField(max_length=127)
    amount = models.PositiveIntegerField(default=0)
    archived = models.BooleanField(default=False)
    category = models.ForeignKey(
        ItemCategory, on_delete=models.SET_NULL, null=True, blank=True
    )


class ItemPropertyValue(PropertyValue):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    property = models.ForeignKey(ItemCategoryProperty, on_delete=models.CASCADE)

    def getPropertyType(self) -> str:
        return self.property.property_type


class Customer(models.Model):
    name = models.CharField(max_length=127)
    surname = models.CharField(max_length=127)
    email = models.EmailField()


class CustomerProperty(PropertyDefinition):
    pass


class CustomerPropertyValue(PropertyValue):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    property = models.ForeignKey(CustomerProperty, on_delete=models.CASCADE)

    def getPropertyType(self) -> str:
        return self.property.property_type


class Rent(models.Model):
    created = models.DateTimeField()
    start = models.DateField()
    end = models.DateField()
    issued = models.DateTimeField(null=True, blank=True)
    returned = models.DateTimeField(null=True, blank=True)


class RentProperty(PropertyDefinition):
    pass


class RentPropertyValue(PropertyValue):
    rent = models.ForeignKey(Rent, on_delete=models.CASCADE)
    property = models.ForeignKey(RentProperty, on_delete=models.CASCADE)

    def getPropertyType(self) -> str:
        return self.property.property_type


class RentItems(models.Model):
    amount = models.PositiveIntegerField()
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True)
    rent = models.ForeignKey(Rent, on_delete=models.CASCADE)
