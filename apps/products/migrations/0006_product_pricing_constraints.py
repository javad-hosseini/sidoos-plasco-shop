from django.db import migrations, models
import django.db.models.expressions


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0005_alter_product_slug"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="product",
            constraint=models.CheckConstraint(
                check=models.Q(on_sale_price__isnull=True) | models.Q(on_sale_price__lte=django.db.models.expressions.F("price")),
                name="product_sale_price_lte_price",
            ),
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.CheckConstraint(
                check=models.Q(call_for_price=False)
                | (models.Q(price=0) & models.Q(on_sale_price__isnull=True)),
                name="product_call_for_price_invariants",
            ),
        ),
    ]
