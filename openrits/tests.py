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
        a = ItemCategory.objects.create(name="A")
        a_1 = ItemCategory.objects.create(name="A_1", parent=a, lineage=f",{a.pk},")
        a_1_1 = ItemCategory.objects.create(
            name="A_1_1", parent=a_1, lineage=f"{a_1.lineage}{a_1.pk},"
        )
        cat_b = ItemCategory.objects.create(name="B")

        a_thing = Item.objects.create(name="a_thing", category=a)
        a_1_thing = Item.objects.create(name="a_1_thing", category=a_1)

        for cat in (a, a_1, a_1_1):
            prop_def = ItemCategoryProperty.objects.create(
                name=cat.name + "_prop", property_type="IntegerField", category=cat
            )
            ItemPropertyValue.objects.create(value="1", item=a_thing, property=prop_def)
            ItemPropertyValue.objects.create(
                value="2", item=a_1_thing, property=prop_def
            )

        b_thing = Item.objects.create(name="b_thing", category=cat_b)
        for field in PropertyDefinition.SUPPORTED_FIELDS:
            prop = ItemCategoryProperty.objects.create(
                name=field.__name__, property_type=field.__name__, category=cat_b
            )
            ItemPropertyValue.objects.create(item=b_thing, property=prop)

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

    def test_filter_relevant_for(self):
        thing1 = Item.objects.get(name="a_1_thing")

        thing1_values = ItemPropertyValue.objects.filter_relevant_for(thing1)
        result = list((v.property.name, v.value) for v in thing1_values)
        expected = [("A_prop", "2"), ("A_1_prop", "2")]

        self.assertEqual(result, expected, f"Expected {expected}, but got {result}")

    def test_filter_obsolete_for(self):
        thing1 = Item.objects.get(name="a_1_thing")

        thing1_values = ItemPropertyValue.objects.filter_obsolete_for(thing1)
        result = list((v.property.name, v.value) for v in thing1_values)
        expected = [("A_1_1_prop", "2")]

        self.assertEqual(result, expected, f"Expected {expected}, but got {result}")


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

    def test_filter_descendants(self):
        cat_a = ItemCategory.objects.get(name="A")
        descendants = ItemCategory.objects.filter_descendants(cat_a)

        names = set(d.name for d in descendants)
        expected = set(["A_1", "A_2", "A_1_1", "A_1_1_1"])

        self.assertEqual(names, expected, f"Expected {expected}, but got {names}")

    def test_filter_descendants_no_descendants(self):
        cat_b = ItemCategory.objects.get(name="B")
        descendants = ItemCategory.objects.filter_descendants(cat_b)

        names = set(d.name for d in descendants)
        expected = set()

        self.assertEqual(names, expected, f"Expected {expected}, but got {names}")

    def test_update_parent_to_other(self):
        b = ItemCategory.objects.get(name="B")
        a_1 = ItemCategory.objects.get(name="A_1")
        a_1_1 = ItemCategory.objects.get(name="A_1_1")
        a_1_2 = ItemCategory.objects.get(name="A_1_1_1")
        ItemCategory.objects.update_parent(a_1, b)

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
        ItemCategory.objects.update_parent(a_1, None)

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

    def test_update_parent_to_descendant(self):
        a_1 = ItemCategory.objects.get(name="A_1")
        a_1_1 = ItemCategory.objects.get(name="A_1_1")
        a_1_1_1 = ItemCategory.objects.get(name="A_1_1_1")
        with self.assertRaises(ValueError):
            ItemCategory.objects.update_parent(a_1, a_1_1_1)

    def test_filter_ancestors(self):
        a_1_1 = ItemCategory.objects.get(name="A_1_1")
        ancestors = ItemCategory.objects.filter_ancestors(a_1_1)

        names = list(ancestor.name for ancestor in ancestors)
        expected = ["A", "A_1"]

        self.assertEqual(names, expected, f"Expected {expected}, but got {names}")

    def test_filter_ancestors_no_ancestors(self):
        b = ItemCategory.objects.get(name="B")
        ancestors = ItemCategory.objects.filter_ancestors(b)

        names = list(ancestor.name for ancestor in ancestors)
        expected = []

        self.assertEqual(names, expected, f"Expected {expected}, but got {names}")


class ItemCategoryProperty_ModelTests(TestCase):
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
        for cat in ItemCategory.objects.all():
            ItemCategoryProperty.objects.create(
                name=cat.name + "_prop", property_type="IntegerField", category=cat
            )
        ItemCategory.objects.create(name="B")

    def test_filter_relevant_for(self):
        a_1_1 = ItemCategory.objects.get(name="A_1_1")
        properties = ItemCategoryProperty.objects.filter_relevant_for(a_1_1)

        names = list(prop.name for prop in properties)
        expected = ["A_prop", "A_1_prop", "A_1_1_prop"]

        self.assertEqual(names, expected, f"Expected {expected}, but got {names}")

    def test_filter_relevant_for_no_properties(self):
        b = ItemCategory.objects.get(name="B")
        properties = ItemCategoryProperty.objects.filter_relevant_for(b)

        names = list(prop.name for prop in properties)
        expected = []

        self.assertEqual(names, expected, f"Expected {expected}, but got {names}")
