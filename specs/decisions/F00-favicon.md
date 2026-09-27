# F00 decision: favicon from the nav mark

The app shipped create-next-app's default `web/app/favicon.ico`. It is replaced with the product's own mark, the two
overlapping service-area circles from `components/nav/Nav.tsx`, on the app background (`#06080d`) so it reads on
light and dark tab strips alike.

- `web/app/icon.svg` is the source; Next's file convention emits the `<link>` tags, so the frozen `layout.tsx` is
  untouched. Strokes are heavier than the nav's so the mark survives 16 px.
- `favicon.ico` (32 px, one PNG entry) and `apple-icon.png` (180 px) are rendered from that SVG with the `sharp`
  already installed under Next, for clients that ask for `/favicon.ico` directly and for iOS home screens.
- The SVG uses literal colours, not CSS variables: a favicon is rendered outside the page and cannot see them.
