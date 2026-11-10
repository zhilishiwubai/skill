# Scope and evidence

| Capability | v0.1.3 scope |
|---|---|
| Python source + data | Runnable and numerically checked |
| SVG editing | Text elements and curve vector paths checked, font must exist on editor machine |
| PDF | Page dimensions and embedded resources checked, including Type3 CharProcs with explicit Differences encoding; no full PDF conformance claim |
| Native Origin project | Basic local probe only; extended acceptance failed; no adapter shipped |
| Word OLE | Not tested |
| Flowcharts and mechanism diagrams | Future module |
| Photographs and CAD | Future module |
| Smoothing / statistics / unit conversion | Not implemented |

The core readback compares every exported SVG curve vertex, in order, to the CSV mapped through the axes transform with a 0.00002 pt export-rounding tolerance. It checks M/L command order, curve clipping rectangles and full reference-line geometry. Path simplification and chunking are disabled. PDF dimensions and font streams (including nested Form resources) and PNG pixel dimensions, DPI metadata and physical size are independently reopened. Text extents at export DPI and 96 DPI, legend placement, note/axis-label overlap and reference-label collisions are checked using the renderer. User-supplied and exported limits must contain all selected points. Gray PNG mode is checked. Curves have distinct line styles and minimum 3:1 contrast on white. Required-file manifests cannot omit delivery files. Missing or changed files fail; a CLI verification failure invalidates a previous stored PASS.

The checks cannot establish absence of every text collision, perceptual distinguishability of all overlapping curves, proper scientific units, correct provenance, physical boundary meaning, or journal compliance. Inspect actual PNGs. Native editor round-trip, color-vision simulation and independent reader assessments remain untested. There are no efficiency improvement estimates or blind-review results.

## R2 adaptation

The local R2 report and execution specification inform provenance, scientific logic before styling, explicit brief, conservative geometry, restrained encoding, grayscale and final-size review. This release implements the user-authorized smaller Python workflow. The report's 1000-case quotas, database, 80 templates and blind evaluation are long-term proposals, not this skill's prerequisites or completed features. Report-specific fonts do not establish universal journal requirements. Refresh official author instructions when targeting a journal.

## Optional Origin integration

Read [the Origin assessment](origin-assessment.md) for the actual local results and blocking failures. No executable adapter ships in 0.1.3. Do not repair licensing as a plotting dependency. A worksheet UI preview capped at 100 rows cannot establish that later rows were lost. Validate with full native data readback. Origin LabTalk `set -w` expects pt multiplied by 500; `set -wp` uses pt. Scope a separately tested adapter before offering native projects as a supported output.

## Selected maintained resources

Matplotlib supplies the rendering engine under its permissive license. Pillow supplies raster reading and grayscale conversion under MIT-CMU. pypdf supplies PDF inspection under BSD-3-Clause. No dependency code or proprietary fonts are vendored. Install exact tested versions from requirements-lock.txt. Official references checked 2026-11-09.

- https://matplotlib.org/stable/users/explain/text/fonts.html
- https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.savefig.html
- https://matplotlib.org/stable/users/project/license.html
- https://pillow.readthedocs.io/en/stable/about.html
- https://pypdf.readthedocs.io/en/stable/meta/license.html
- https://docs.originlab.com/labtalk/ref/set-cmd/
