from django.db import models
from django.core.validators import RegexValidator
from django.db.models.functions import Substr, StrIndex, Concat, Chr
from django.db.models.query import QuerySet
from django.db.models import Value as V, F
import datetime


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
        Deserializes value using type returned by getProperty.
        """
        property_type = self.getPropertyType()
        return PropertyValue.TYPE_DICT[property_type]().to_python(self.value)

    def serialize(self, object: any):
        """
        Serializes object and writes it to the value.
        """
        self.value = str(object)

    class Meta:
        abstract = True


class ItemCategory(models.Model):
    name = models.CharField(max_length=127)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True)
    lineage = models.TextField(
        editable=False,
        default=",",
        validators=[
            RegexValidator(regex=r"^,(?:\d+,)*\Z", message="Incorrect lineage format")
        ],
    )

    class Manager(models.Manager):
        def filter_descendants(
            self, category: "ItemCategory"
        ) -> "QuerySet[ItemCategory]":
            """
            Return all subcategories for given category.
            """
            return self.filter(lineage__contains=f",{category.pk},")

        def filter_ancestors(
            self, category: "ItemCategory"
        ) -> "QuerySet[ItemCategory]":
            """
            Return all supercategories for given category.
            """
            return self.alias(
                chrpk=Concat(V(","), F("id"), V(","), output_field=models.CharField()),
                ancestors=V(category.lineage),
            ).filter(ancestors__contains=F("chrpk"))

        def update_parent(
            self, category: "ItemCategory", new_parent: "ItemCategory"
        ) -> None:
            """
            Update parent category and adjust
            all subcategories accordingly.
            """
            new_lineage = ","
            new_parent_id = None
            if new_parent is not None:
                new_lineage = new_parent.lineage + f"{new_parent.pk},"
                new_parent_id = new_parent.pk
                check_qs = self.filter_descendants(category).filter(pk=new_parent_id)
                if check_qs:
                    raise ValueError("New category parent must not be its descendant.")
            self.filter(pk=category.pk).update(
                parent=new_parent_id, lineage=new_lineage
            )
            descendantsLineage = new_lineage + f"{category.pk},"
            searchStr = f",{category.pk},"
            self.filter_descendants(category).update(
                lineage=Concat(
                    V(descendantsLineage),
                    Substr(
                        F("lineage"),
                        StrIndex(F("lineage"), V(searchStr)) + len(searchStr),
                    ),
                )
            )

    objects = Manager()


class ItemCategoryProperty(PropertyDefinition):
    category = models.ForeignKey(ItemCategory, on_delete=models.CASCADE)

    class Manager(models.Manager):
        def filter_relevant_for(
            self, category: ItemCategory
        ) -> "QuerySet[ItemCategoryProperty]":
            """
            Return ItemCategoryProperties for given category and all supercategories.
            """
            return self.alias(
                chrpk=Concat(
                    V(","), "category_id", V(","), output_field=models.CharField()
                ),
                categories=Concat(
                    V(category.lineage),
                    V(category.pk),
                    V(","),
                    output_field=models.CharField(),
                ),
            ).filter(categories__contains=F("chrpk"))

    objects = Manager()


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

    class Manager(models.Manager):
        def filter_relevant_for(self, item: Item) -> "QuerySet[ItemPropertyValue]":
            """
            Return values for given item and its property definitions.
            """
            defined_properties = ItemCategoryProperty.objects.filter_relevant_for(
                item.category
            ).only("id")
            return self.filter(item=item).filter(property__in=defined_properties)

        def filter_obsolete_for(self, item: Item) -> "QuerySet[ItemPropertyValue]":
            """
            Return values for given item that are not related to
            any of item current property definitions.
            """
            defined_properties = ItemCategoryProperty.objects.filter_relevant_for(
                item.category
            ).only("id")
            return self.filter(item=item).exclude(property__in=defined_properties)

    objects = Manager()

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
