import os
import django
from django.core.management import call_command

# 1. PASTE YOUR RENDER EXTERNAL DATABASE URL HERE
# Go to Render Dashboard -> faircredit-db -> Connections -> External Database URL
RENDER_DB_URL = "postgresql://faircredit_user:BwpgyVSbfSbc4j0UvNdmmoC5xhKR7smN@dpg-daeljdn40ujc73fntqog-a.oregon-postgres.render.com/faircredit_enel"

if "your_render_external_url" in RENDER_DB_URL:
    print("❌ Please edit this script and paste your Render External Database URL!")
    exit(1)

# 2. Tell Django to use the production URL just for this script
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "faircredit.settings")
os.environ["DATABASE_URL"] = RENDER_DB_URL

# 3. Initialize Django
django.setup()

# 4. Upload the data
print(f"Connecting to Production Database and loading local_data.json...")
try:
    # This acts exactly like running `python manage.py loaddata`
    call_command("loaddata", "local_data.json")
    print("✅ Success! Your local data has been uploaded to production.")
except Exception as e:
    print(f"❌ Error uploading data: {e}")
