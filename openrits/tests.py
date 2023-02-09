from django.test import TestCase

from .models import (
    PropertyDefinition,
    Item,
    ItemPropertyValue,
    ItemCategoryProperty,
    ItemCategory,
)
import datetime


class ItemPropertyValue_ModelTests(TestCase):
    def setUp(self):
        category = ItemCategory.objects.create(name="A")
        item = Item.objects.create(name="thing", category=category)
        for field in PropertyDefinition.SUPPORTED_FIELDS:
            prop = ItemCategoryProperty.objects.create(
                name=field.__name__, property_type=field.__name__, category=category
            )
            ItemPropertyValue.objects.create(item=item, property=prop)

    SERIALIZATION_CASES = [
        ("IntegerField", "1", 1),
        ("FloatField", "0.5", 0.5),
        ("BooleanField", "True", True),
        ("TextField", "Hello sir!", "Hello sir!"),
        (
            "DateField",
            str(datetime.date(1918, 11, 11)),
            datetime.date(1918, 11, 11),
        ),
    ]

    def test_deserialize(self):
        fields_to_check = set(t.__name__ for t in PropertyDefinition.SUPPORTED_FIELDS)
        for field, serialized, deserialized in self.SERIALIZATION_CASES:
            self.assertTrue(
                field in fields_to_check, "Supported types should be tested once"
            )
            value = ItemCategoryProperty.objects.get(
                name=field
            ).itempropertyvalue_set.first()
            value.value = serialized
            self.assertEqual(
                value.deserialize(),
                deserialized,
                "Result of deserialize should match target object",
            )
            fields_to_check.remove(field)
        self.assertTrue(
            len(fields_to_check) == 0, "Test should exhaust all supported fields"
        )

    def test_serialize(self):
        fields_to_check = set(t.__name__ for t in PropertyDefinition.SUPPORTED_FIELDS)
        for field, serialized, deserialized in self.SERIALIZATION_CASES:
            self.assertTrue(
                field in fields_to_check, "Supported types should be tested once"
            )
            value = ItemCategoryProperty.objects.get(
                name=field
            ).itempropertyvalue_set.first()
            value.serialize(deserialized)
            self.assertEqual(
                value.value,
                serialized,
                "Result of serialize should match target object",
            )
            fields_to_check.remove(field)
        self.assertTrue(
            len(fields_to_check) == 0, "Test should exhaust all supported fields"
        )
