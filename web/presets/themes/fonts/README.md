# Offline preview fonts

These SIL Open Font License subsets are shared by all 23 HTML concept previews.
They contain the sample's characters, rather than complete language coverage.
The checked-in WebP images need no fonts, downloads, rendering or installation.

The Latin fonts were obtained from the official Google Fonts stylesheet API and
Google Fonts repository. Family names remain CSS aliases for the styles named in
the upstream catalog; internal subset names are prefixed **Studio Preview**.
Each family has its corresponding `*-OFL.txt` file alongside it.

- Upstream fonts: https://github.com/google/fonts/tree/main/ofl
- Chinese fallback: Noto Sans CJK SC (regular/bold) and Noto Serif CJK SC (regular)
- Noto source: https://github.com/notofonts/noto-cjk
- Noto license and copyright: `noto-COPYRIGHT.txt`

`python scripts/subset_theme_fonts.py` can reduce existing font subsets when
sample content is removed. To add new Chinese glyphs, provide original Noto CJK
TTC files with `--noto-source /path/to/noto`; then regenerate previews. To add
Latin glyphs beyond the existing subsets, first obtain the corresponding full
font from its official source under the included license. Font tooling is only a
maintainer dependency, not needed by users to start the app.
