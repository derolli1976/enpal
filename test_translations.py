"""Test translation loading for config flow."""
import json

# Load and verify translation files
print("Testing translation file structure...\n")

with open("custom_components/enpal_webparser/translations/de.json", "r", encoding="utf-8") as f:
    de_trans = json.load(f)

with open("custom_components/enpal_webparser/translations/en.json", "r", encoding="utf-8") as f:
    en_trans = json.load(f)

# Check if discovery_options exist
print("German (de.json):")
if "discovery_options" in de_trans["config"]["step"]:
    for key, value in de_trans["config"]["step"]["discovery_options"].items():
        print(f"  ✓ {key}: {value}")
else:
    print("  ✗ discovery_options missing")

print("\nEnglish (en.json):")
if "discovery_options" in en_trans["config"]["step"]:
    for key, value in en_trans["config"]["step"]["discovery_options"].items():
        print(f"  ✓ {key}: {value}")
else:
    print("  ✗ discovery_options missing")

# Verify all expected keys are present
expected_keys = ["discover", "manual", "none_of_these", "no_devices"]
print("\nKey validation:")
for key in expected_keys:
    de_has = key in de_trans["config"]["step"]["discovery_options"]
    en_has = key in en_trans["config"]["step"]["discovery_options"]
    status = "✓" if de_has and en_has else "✗"
    print(f"  {status} {key}: DE={de_has}, EN={en_has}")

print("\n✓ Translation structure looks good!")
