# Self-hosted fonts

These woff2 files are vendored so the panel renders crisp Persian and English
text offline and in regions where font CDNs (Google Fonts) are blocked. No
external font request is ever made.

| File | Family | Weight | Subset | License |
| --- | --- | --- | --- | --- |
| `inter-400/500/600/700.woff2` | [Inter](https://github.com/rsms/inter) | 400/500/600/700 | Latin | SIL OFL 1.1 |
| `vazirmatn-400/500/700.woff2` | [Vazirmatn](https://github.com/rastikerdar/vazirmatn) | 400/500/700 | Arabic (covers Persian) | SIL OFL 1.1 |

Inter carries Latin; Vazirmatn carries Persian/Arabic and is reached through the
`--font` stack fallback (Inter lacks those glyphs). `@font-face` blocks live at
the top of `../app.css`; the files are precached in `../sw.js`.

Source: downloaded from the Fontsource CDN (`cdn.jsdelivr.net/fontsource/fonts/`),
which repackages the upstream OFL fonts. To refresh, re-download the same
`<family>@latest/<subset>-<weight>-normal.woff2` files.
