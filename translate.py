import os
import shutil
import polib
from deep_translator import GoogleTranslator

# The newly added languages and their ISO 639-1/2 codes for google translate
new_langs = {
    "as": "as",
    "gu": "gu",
    "kn": "kn",
    "ks": "ks", # Kashmiri might not be supported well, but deep_translator/google API might handle it or fallback
    "kok": "gom", # Konkani in Google Translate is gom
    "mai": "mai",
    "ml": "ml",
    "ne": "ne",
    "or": "or",
    "pa": "pa",
    "sd": "sd",
    "ta": "ta",
    "ur": "ur",
}

# Source PO file
src_po_path = "locale/hi/LC_MESSAGES/django.po"
src_po = polib.pofile(src_po_path)

for lang_code, gt_code in new_langs.items():
    print(f"Processing {lang_code}...")
    dest_dir = f"locale/{lang_code}/LC_MESSAGES"
    os.makedirs(dest_dir, exist_ok=True)
    
    dest_po_path = os.path.join(dest_dir, "django.po")
    dest_mo_path = os.path.join(dest_dir, "django.mo")
    
    # Create new PO file based on source
    po = polib.POFile()
    po.metadata = {
        'Project-Id-Version': 'FairCreditScore',
        'MIME-Version': '1.0',
        'Content-Type': 'text/plain; charset=UTF-8',
        'Content-Transfer-Encoding': '8bit',
        'Language': lang_code
    }
    
    try:
        translator = GoogleTranslator(source='en', target=gt_code)
    except Exception as e:
        print(f"Skipping translation for {lang_code} due to init error: {e}")
        translator = None
    
    for entry in src_po:
        if entry.msgid.strip() == "":
            continue
        
        translated_text = entry.msgid
        if translator:
            try:
                translated_text = translator.translate(entry.msgid)
                if not translated_text:
                    translated_text = entry.msgid
            except Exception as e:
                # Silently fallback to msgid
                translated_text = entry.msgid
            
        new_entry = polib.POEntry(
            msgid=entry.msgid,
            msgstr=translated_text
        )
        po.append(new_entry)
    
    po.save(dest_po_path)
    po.save_as_mofile(dest_mo_path)
    print(f"Saved {lang_code}")

print("Done generating translations!")
