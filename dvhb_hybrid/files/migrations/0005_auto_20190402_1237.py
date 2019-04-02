import django.contrib.postgres.indexes

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0004_auto_20171213_0805'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='image',
            index=django.contrib.postgres.indexes.GinIndex(
                fields=['meta'], 
                name='files_image_meta_df8195_gin'
            ),
        ),
    ]
