# GridBridge landing page

The landing page is integrated at `/` in the Next.js app. It uses the shared app header and the blue/orange overlapping-circle GridBridge mark. The original interactive 2D project map remains at `/map`; the main overlap explorer is at `/time`.

## Experience

The opening shows the semi before revealing the large “GridBridge” title and smaller “Every mile. Connected.” tagline. After a four-second opening, the page automatically scrolls through the text reveals and network into the content. Wheel, touch/pointer, or navigation-key input ends autoplay immediately; Pause freezes automatic scrolling and the illustration, and Play resumes it. Autoplay is disabled for restored scroll positions, anchor links, and reduced-motion preferences. Scrolling drives the truck left to reveal “Same roads.” A second leftward pass reveals “One network.” Continuing down the page transitions to an illustrative regional network, then the workflow, corridor, and product links.

The truck has separated tandem tires and the GridBridge logo on its trailer. The road/network switch and pause control are available in the hero. Reduced-motion preferences remove the long scroll sequence and automatic animation. Network lines and the truck are conceptual illustrations, not live fleet data or validated project geometry.

## Source integration

| File | Responsibility |
| --- | --- |
| `web/app/page.tsx` | Homepage metadata and landing-page entry point |
| `web/components/nav/Nav.tsx` | Shared navigation and utility-circle mark |
| `web/components/landing/LandingPage.tsx` | Headline, product sections, and existing app links |
| `web/components/landing/HeroStory.tsx` | Smoothed scroll progress and text-reveal phases |
| `web/components/landing/HeroScene.tsx` | Road/network controls, text beats, and pause state |
| `web/components/landing/road-scene.js` | Canvas truck, wheels, trailer logo, and leftward passes |
| `web/components/landing/NetworkIllustration.tsx` | Decorative network map |
| `web/components/landing/landing.module.css` | Responsive layout and reveal styling |
| `web/scripts/export-landing.cjs` | Self-contained HTML exporter |

The integrated page links to the existing overlap explorer, 2D map, national explorer, filing changes, and source coverage. Shared navigation also exposes the other existing app routes. This landing-page work does not change overlap calculations, project evidence, database configuration, or the underlying operational tools.

## Run locally

From the repository root, install dependencies as described in the main README. Then:

```sh
cd web
WATCHPACK_POLLING=1000 DATA_MODE=fixture npm run dev -- --webpack --hostname 127.0.0.1 --port 3001
```

Open `http://127.0.0.1:3001/`. This command uses the committed sample data and polling to avoid local file-watcher limits. Read-only MongoDB configuration follows the main README. Do not configure fixture mode for a production deployment.

## Export one HTML file and a ZIP

From `web/`, build first so the exporter can embed the app's fonts:

```sh
DATA_MODE=fixture npm run build -- --webpack
node scripts/export-landing.cjs /tmp/gridbridge-export
python3 -m zipfile -c /tmp/GridBridge.zip /tmp/gridbridge-export/GridBridge.html
```

The output directory is explicit and can be any writable folder. Keep generated exports outside the repository checkout. The ZIP contains `GridBridge.html`; extract it and open it in a browser.

The exported page includes its styles, font files, truck drawing, network illustration, and scroll behavior. It does not need Next.js to display the landing page. The explorer and other application pages still require the full app. Their links default to `http://127.0.0.1:3001`.

To point those links at an actual deployed app, set `GRIDBRIDGE_APP_URL` to its HTTP(S) origin when exporting. The exporter does not publish a site or verify that the supplied deployment exists. Standalone exports display a sample-data notice; exporting one does not establish live database connectivity.

The exporter renders the same React components and adapts the hero scroll effect for a standalone document. If the structure of `HeroStory.tsx`, its controls, or the CSS module naming changes, check the export as well as the app. The command fails on unresolved Next.js asset paths or a missing expected scroll adapter.

## Validation and limits

The integrated animation changes passed lint, TypeScript checks, and a production webpack build. The homepage returned HTTP 200. The existing navigation checks were updated for the restored shared header and `/map` route. The test runner discovers the desktop/mobile tests; discovery is not execution.

Visual inspection of the final leftward-pass revision was blocked by the browser tool's URL policy. Before a presentation, manually check the opening timing, both text wipes, logo readability, wheel clearance, narrow-screen layout, road/network switch, pause/resume, reduced-motion behavior, and links into the app. Repeat these checks on the exported HTML after source changes. No production deployment is claimed by these local checks.
