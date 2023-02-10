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
                field in fields_to_check,
                f"Field {field} not supported or already tested",
            )
            value = ItemCategoryProperty.objects.get(
                name=field
            ).itempropertyvalue_set.first()
            value.value = serialized
            result = value.deserialize()
            self.assertEqual(
                result,
                deserialized,
                f"{field} deserialize - expected {deserialized}, but got {result}",
            )
            fields_to_check.remove(field)
        self.assertEqual(
            len(fields_to_check),
            0,
            f"Some of supported fields were omitted {fields_to_check}",
        )

    def test_serialize(self):
        fields_to_check = set(t.__name__ for t in PropertyDefinition.SUPPORTED_FIELDS)
        for field, serialized, deserialized in self.SERIALIZATION_CASES:
            self.assertTrue(
                field in fields_to_check,
                f"Field {field} not supported or already tested",
            )
            value = ItemCategoryProperty.objects.get(
                name=field
            ).itempropertyvalue_set.first()
            value.serialize(deserialized)
            self.assertEqual(
                value.value,
                serialized,
                f"{field} serialize - expected {serialized}, but got {value.value}",
            )
            fields_to_check.remove(field)
        self.assertEqual(
            len(fields_to_check),
            0,
            f"Some of supported fields were omitted {fields_to_check}",
        )


class ItemCategory_ModelTests(TestCase):
    def setUp(self):
        cat_a = ItemCategory.objects.create(name="A")
        cat_a_1 = ItemCategory.objects.create(
            name="A_1", parent=cat_a, lineage=f",{cat_a.pk},"
        )
        cat_a_1_1 = ItemCategory.objects.create(
            name="A_1_1", parent=cat_a_1, lineage=f"{cat_a_1.lineage}{cat_a_1.pk},"
        )
        ItemCategory.objects.create(
            name="A_1_1_1",
            parent=cat_a_1_1,
            lineage=f"{cat_a_1_1.lineage}{cat_a_1_1.pk},",
        )
        ItemCategory.objects.create(name="A_2", parent=cat_a, lineage=f",{cat_a.pk},")
        ItemCategory.objects.create(name="B")

    def test_get_descendants(self):
        descendants = ItemCategory.objects.get(name="A").get_descendants()

        names = set(name for (name,) in descendants.values_list("name"))
        expected = {"A_1", "A_2", "A_1_1", "A_1_1_1"}

        self.assertTrue(
            names == expected, f"Expected {expected}, but got {descendants}"
        )

    def test_update_parent_to_other(self):
        b = ItemCategory.objects.get(name="B")
        a_1 = ItemCategory.objects.get(name="A_1")
        a_1_1 = ItemCategory.objects.get(name="A_1_1")
        a_1_2 = ItemCategory.objects.get(name="A_1_1_1")
        a_1.update_parent(b)

        expected_parent = b.pk
        expected_lineage = f",{b.pk},"
        for cat in (a_1, a_1_1, a_1_2):
            cat.refresh_from_db()
            self.assertEqual(
                cat.parent_id, expected_parent, f"Incorrect parent of {cat.name}"
            )
            self.assertEqual(
                cat.lineage, expected_lineage, f"Incorrect lineage of {cat.name}"
            )
            expected_parent = cat.pk
            expected_lineage += f"{cat.pk},"

    def test_update_parent_to_null(self):
        a_1 = ItemCategory.objects.get(name="A_1")
        a_1_1 = ItemCategory.objects.get(name="A_1_1")
        a_1_1_1 = ItemCategory.objects.get(name="A_1_1_1")
        a_1.update_parent(None)

        expected_parent = None
        expected_lineage = f","
        for cat in (a_1, a_1_1, a_1_1_1):
            cat.refresh_from_db()
            self.assertEqual(
                cat.parent_id, expected_parent, f"Incorrect parent of {cat.name}"
            )
            self.assertEqual(
                cat.lineage, expected_lineage, f"Incorrect lineage of {cat.name}"
            )
            expected_parent = cat.pk
            expected_lineage += f"{cat.pk},"
