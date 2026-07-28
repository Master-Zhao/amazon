from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("recommendations", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="recommendation",
            name="action_type",
            field=models.CharField(
                choices=[
                    ("UPDATE_CAMPAIGN_BUDGET", "Update Campaign budget"),
                    ("ENABLE_CAMPAIGN", "Enable Campaign"),
                    ("PAUSE_CAMPAIGN", "Pause Campaign"),
                    ("SET_CAMPAIGN_STATE", "Pause or enable Campaign"),
                    ("UPDATE_KEYWORD_BID", "Update Keyword bid"),
                    ("ENABLE_KEYWORD", "Enable Keyword"),
                    ("PAUSE_KEYWORD", "Pause Keyword"),
                    ("SET_KEYWORD_STATE", "Pause or enable Keyword"),
                    ("UPDATE_TARGET_BID", "Update Target bid"),
                    ("ENABLE_TARGET", "Enable Target"),
                    ("PAUSE_TARGET", "Pause Target"),
                    ("UPDATE_PRODUCT_TARGET_BID", "Update Product Target bid"),
                    (
                        "SET_PRODUCT_TARGET_STATE",
                        "Pause or enable Product Target",
                    ),
                    ("ADD_KEYWORD", "Add Keyword"),
                    ("CREATE_KEYWORD", "Create Keyword (legacy)"),
                    ("ADD_NEGATIVE_KEYWORD", "Add Negative Keyword"),
                    (
                        "CREATE_NEGATIVE_KEYWORD",
                        "Create Negative Keyword (legacy)",
                    ),
                ],
                max_length=64,
            ),
        ),
        migrations.AlterField(
            model_name="recommendationrevision",
            name="action_type",
            field=models.CharField(
                choices=[
                    ("UPDATE_CAMPAIGN_BUDGET", "Update Campaign budget"),
                    ("ENABLE_CAMPAIGN", "Enable Campaign"),
                    ("PAUSE_CAMPAIGN", "Pause Campaign"),
                    ("SET_CAMPAIGN_STATE", "Pause or enable Campaign"),
                    ("UPDATE_KEYWORD_BID", "Update Keyword bid"),
                    ("ENABLE_KEYWORD", "Enable Keyword"),
                    ("PAUSE_KEYWORD", "Pause Keyword"),
                    ("SET_KEYWORD_STATE", "Pause or enable Keyword"),
                    ("UPDATE_TARGET_BID", "Update Target bid"),
                    ("ENABLE_TARGET", "Enable Target"),
                    ("PAUSE_TARGET", "Pause Target"),
                    ("UPDATE_PRODUCT_TARGET_BID", "Update Product Target bid"),
                    (
                        "SET_PRODUCT_TARGET_STATE",
                        "Pause or enable Product Target",
                    ),
                    ("ADD_KEYWORD", "Add Keyword"),
                    ("CREATE_KEYWORD", "Create Keyword (legacy)"),
                    ("ADD_NEGATIVE_KEYWORD", "Add Negative Keyword"),
                    (
                        "CREATE_NEGATIVE_KEYWORD",
                        "Create Negative Keyword (legacy)",
                    ),
                ],
                max_length=64,
            ),
        ),
    ]
