"""Acquire fixed public statewide inputs outside the repository."""
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from common import REPO_ROOT
from osm.fetch import OVERPASS_URL, USER_AGENT

QUERY = ('[out:json][timeout:90][maxsize:67108864];\n'
         'area["ISO3166-2"="US-TX"]->.tx;\n'
         'nwr["power"="substation"]["name"](area.tx);\nout center tags;\n')
COUNTY_URL = 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1/query'
COUNTY_PARAMS = {'where': "STATE='48'", 'outFields': 'NAME,GEOID,STATE,COUNTY',
                 'returnGeometry': 'true', 'outSR': '4326', 'f': 'geojson'}


def main():
    target = Path(sys.argv[1]).resolve()
    if target.is_relative_to(REPO_ROOT.resolve()):
        raise ValueError('raw downloads must stay outside the repo')
    target.mkdir(parents=True, exist_ok=True)
    receipts = {}
    for key, url, body in (
        ('osm', OVERPASS_URL, urlencode({'data': QUERY}).encode()),
        ('counties', COUNTY_URL + '?' + urlencode(COUNTY_PARAMS), None),
    ):
        request = Request(url, data=body, headers={'User-Agent': USER_AGENT})
        with urlopen(request, timeout=120) as response:
            data = response.read(64 * 1024 * 1024 + 1)
        if len(data) > 64 * 1024 * 1024:
            raise ValueError('source exceeds size limit')
        parsed = json.loads(data)
        if 'error' in parsed or 'remark' in parsed or parsed.get('exceededTransferLimit'):
            raise ValueError('source response is incomplete')
        (target / f'{key}.json').write_bytes(data)
        receipts[key] = {'url': url, 'query': QUERY if key == 'osm' else COUNTY_PARAMS,
                         'retrieved_at': datetime.now(UTC).isoformat(),
                         'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
                         'user_agent': USER_AGENT}
        (target / 'acquisition.json').write_text(json.dumps(receipts, indent=2) + '\n')
        print(key, receipts[key]['sha256'], len(data))


if __name__ == '__main__':
    main()
