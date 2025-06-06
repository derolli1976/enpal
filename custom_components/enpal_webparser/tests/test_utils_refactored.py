import pytest
from custom_components.enpal_webparser.utils import parse_enpal_html_sensors

@pytest.fixture
def sample_html():
    return '''
    <html>
      <body>
        <div class="card">
          <h2>Wechselrichter</h2>
          <table>
            <tr><th>Name</th><th>Wert</th><th>Zeit</th></tr>
            <tr><td>Leistung AC</td><td>1234 W</td><td>06.06.2025 08:42</td></tr>
            <tr><td>Spannung</td><td>230 V</td><td>06.06.2025 08:43</td></tr>
          </table>
        </div>
        <div class="card">
          <h2>Batterie</h2>
          <table>
            <tr><th>Name</th><th>Wert</th><th>Zeit</th></tr>
            <tr><td>Kapazität</td><td>83 %</td><td>06.06.2025 08:40</td></tr>
          </table>
        </div>
      </body>
    </html>
    '''

def test_parse_enpal_html_sensors_returns_expected_sensors(sample_html):
    groups = ["Wechselrichter", "Batterie"]
    sensors = parse_enpal_html_sensors(sample_html, groups)

    assert len(sensors) == 3

    names = [s["name"] for s in sensors]
    assert "Wechselrichter: Leistung AC" in names
    assert "Wechselrichter: Spannung" in names
    assert "Batterie: Kapazität" in names

    for sensor in sensors:
        assert "value" in sensor
        assert "unit" in sensor
        assert "device_class" in sensor
        assert "enpal_last_update" in sensor
        assert sensor["enabled"] is True

def test_ignores_cards_not_in_groups(sample_html):
    sensors = parse_enpal_html_sensors(sample_html, groups=["Wechselrichter"])
    assert len(sensors) == 2
    for s in sensors:
        assert s["name"].startswith("Wechselrichter")

def test_handles_invalid_timestamp_gracefully():
    html = '''
    <div class="card">
      <h2>Testgruppe</h2>
      <table>
        <tr><th></th></tr>
        <tr><td>Spannung</td><td>230 V</td><td>ungültig</td></tr>
      </table>
    </div>
    '''
    sensors = parse_enpal_html_sensors(html, groups=["Testgruppe"])
    assert len(sensors) == 1
    assert sensors[0]["enpal_last_update"] == "ungültig"