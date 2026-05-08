import math
import os
import re
import requests
from datetime import datetime, time as dtime
from dotenv import load_dotenv
from nicegui import app, ui

load_dotenv()

def _t(key, default):
    h, m = os.getenv(key, default).split(':')
    return dtime(int(h), int(m))

LUNCHBUS_API = f'https://data.hunter-crm.com/HunterGPS/index.php?id=Lunch_{os.getenv("BUS_NUMBER", "3")}'
COORD_PATTERN = re.compile(r'var marker = L\.marker\(\[(\d+\.\d+),\s*(\d+\.\d+)\]')
REFRESH_SECONDS = int(os.getenv('REFRESH_SECONDS', '15'))
ACTIVE_START = _t('ACTIVE_START', '12:00')
ACTIVE_END = _t('ACTIVE_END', '13:00')
HIGH_FREQ_START = _t('HIGH_FREQ_START', '12:25')

def fetch_location():
    try:
        r = requests.get(LUNCHBUS_API, timeout=10)
        r.raise_for_status()
        match = COORD_PATTERN.search(r.text)
        if match:
            return float(match.group(1)), float(match.group(2))
    except requests.exceptions.RequestException as e:
        print(f'Fetch error: {e}')
    return None

# Initial position (fallback if first fetch fails)
initial = fetch_location() or (0.0, 0.0)

with ui.element('div').classes('relative w-full h-screen'):
    m = ui.leaflet(center=initial, zoom=15).classes('w-full h-full')
    with ui.element('div').classes('absolute top-0 left-0 z-[1000] bg-white/80 rounded-br-xl px-4 py-2'):
        ui.label('🚌 Lunch Bus Tracker').classes('text-2xl font-bold')
        status = ui.label().classes('text-sm text-gray-600')
        countdown = ui.label().classes('text-sm font-semibold text-red-700')

app.add_static_files('/images', '.')

COPERNICUS = (float(os.getenv('COPERNICUS_LAT', '52.291806')), float(os.getenv('COPERNICUS_LON', '4.726361')))
ALERT_START = _t('ALERT_START', '12:15')
ALERT_END = _t('ALERT_END', '12:45')
ARRIVAL_RADIUS_M = int(os.getenv('ARRIVAL_RADIUS_M', '100'))

notified_today = False
bus_in_zone = False
_tick = 0

def haversine(lat1, lon1, lat2, lon2):
    R = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

marker = m.marker(latlng=initial)
m.marker(latlng=COPERNICUS)

async def set_icons():
    await ui.run_javascript(f'''
        const el = getElement({m.id});
        if (el && el.map) {{
            let i = 0;
            el.map.eachLayer(function(layer) {{
                if (layer instanceof L.Marker) {{
                    if (i === 0) {{
                        layer.setIcon(L.icon({{
                            iconUrl: '/images/lunchbus.png',
                            iconSize: [100, 50],
                            iconAnchor: [50, 25]
                        }}));
                        layer.on('click', function() {{
                            window.open('https://www.lunchbus.nl/product-categorie/lunch/', '_blank');
                        }});
                    }} else if (i === 1) {{
                        layer.setIcon(L.icon({{
                            iconUrl: '/images/copernicus.webp',
                            iconSize: [36, 36],
                            iconAnchor: [18, 18]
                        }}));
                    }}
                    i++;
                }}
            }});
            L.circle([{COPERNICUS[0]}, {COPERNICUS[1]}], {{
                radius: {ARRIVAL_RADIUS_M},
                color: '#c0392b',
                fillColor: '#c0392b',
                fillOpacity: 0.1,
                weight: 2
            }}).addTo(el.map);
        }}
    ''')

app.on_connect(lambda: ui.timer(0.5, set_icons, once=True))

def update_countdown():
    now = datetime.now()
    lunch = now.replace(hour=12, minute=30, second=0, microsecond=0)
    delta_s = (lunch - now).total_seconds()
    if notified_today and not bus_in_zone:
        countdown.set_text('You missed the bus! 🚌💨')
    elif ALERT_START <= now.time() <= ALERT_END:
        countdown.set_text('🍽️ Bus expected now!')
    elif 0 < delta_s <= 3600:
        countdown.set_text(f'🕐 Bus in ~{int(delta_s / 60)} min')
    else:
        countdown.set_text('')

def update():
    global notified_today, bus_in_zone, _tick
    _tick += 1
    now = datetime.now().time()

    in_active_window = ACTIVE_START <= now <= ACTIVE_END
    high_freq = in_active_window and HIGH_FREQ_START <= now <= ALERT_END and not notified_today
    if not high_freq and _tick % 2 != 0:
        update_countdown()
        return

    loc = fetch_location()
    if loc:
        marker.move(*loc)
        m.set_center(loc)
        status.set_text(f'Last update: {loc[0]:.5f}, {loc[1]:.5f}')

        now = datetime.now().time()
        if in_active_window and ALERT_START <= now <= ALERT_END:
            dist = haversine(loc[0], loc[1], *COPERNICUS)
            bus_in_zone = dist <= ARRIVAL_RADIUS_M
            if bus_in_zone and not notified_today:
                notified_today = True
                ui.run_javascript('''
                    Notification.requestPermission().then(p => {
                        if (p === 'granted') new Notification('🚌 Lunch Bus is here!', {body: 'The bus has arrived at Copernicus.'});
                    });
                    (function() {
                        const ctx = new AudioContext();
                        [[523, 0], [659, 0.3], [784, 0.6]].forEach(([freq, t]) => {
                            const osc = ctx.createOscillator();
                            const gain = ctx.createGain();
                            osc.connect(gain);
                            gain.connect(ctx.destination);
                            osc.frequency.value = freq;
                            gain.gain.setValueAtTime(0.3, ctx.currentTime + t);
                            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + t + 0.5);
                            osc.start(ctx.currentTime + t);
                            osc.stop(ctx.currentTime + t + 0.5);
                        });
                    })();
                ''')
        else:
            notified_today = False
            bus_in_zone = False
    else:
        status.set_text('Could not fetch location')

    update_countdown()

update()  # populate status immediately
ui.timer(REFRESH_SECONDS, update)

ui.add_head_html('<style>body { margin: 0; overflow: hidden; }</style>')
ui.run(port=8080, title='Lunch Bus Tracker', host='0.0.0.0')