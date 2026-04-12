# Viewers — TEMPORARY HOME

These viewers (`urdf/`, `usd/`) currently live inside the `fusion` plugin because the `fusion` plugin is the only fuzzydroid plugin that exists today.

**They will move** to dedicated `urdf` and `usd` (or `isaacsim`) plugins when those plugins ship. Do not build features that assume the viewers are Fusion-specific — they're not. They read URDF / USD files from disk and are independent of Fusion 360.

## urdf-loaders bundled JS

`urdf/viewer/assets/URDFLoader-*.js` is a compiled bundle from [gkjohnson/urdf-loaders](https://github.com/gkjohnson/urdf-loaders) (Apache-2.0). The minified build may have stripped the original copyright header — if so, see `NOTICES.md` at the repo root for attribution.
