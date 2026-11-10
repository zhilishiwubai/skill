# Origin assessment, updated 2026-11-10

## Current author decision

The author explicitly confirmed Origin usability after reviewing the code and requested that further Origin verification stop. Status for this publication round: **AUTHOR_CONFIRMED_AVAILABLE / FURTHER_NATIVE_TESTS_WAIVED**. Do not restart, close existing processes or rerun native acceptance as part of preparing this release.

The latest connector attempt returned `ApplicationBase_LT_execute` before a project was opened; no new save/reopen/edit verification was completed. This retained execution record is separate from the author's code-review decision. It is not a claim that manual Origin use is unavailable, and the author's confirmation is not fabricated as an automated PASS.

No executable Origin adapter is included in the 0.2.1-local install package. Its shipped renderer is CSV → Python/Matplotlib → SVG/PDF/PNG. Native projects, scientific approval, license status and Word OLE remain distinct claims. Existing experimental Origin scripts stay outside this package.

## Retained historical test record

On 2026-11-10 a clean-start basic native case passed. Extended cases exposed LF→CRLF text comparison, localized font alias lookup and Type3 resource-check defects. New isolated experimental code corrects newline comparison, obtains aliases from the exact resolved font, and observes owned PID creation-time/exit instead of trusting an API return. These changes have unit/readback evidence only; a repaired native end-to-end run is not claimed.

The official minimal OriginExt Application → Exit (True) → delete proxy → gc example still left its process resident on this host. Remaining cause is unconfirmed. The user explicitly chose to retain nine recorded test processes; no further Origin instance was launched after that choice and no process was force-killed. Native release verification and scientific-notation layout remain unresolved. A real exported PDF still fails the clipping check; Type3 resource acceptance must not hide that failure.

Local Origin 10.250212 with originpro 1.1.15 / OriginExt 1.2.6 produced a basic two-curve, 41-point-per-curve project and PNG. Full worksheet values/order survived save/reopen. Later basic exports showed no Demo text or visible watermark in the inspected PNG/PDF. This is evidence about those files, not license certification or a guarantee about future exports.

Native SVG quantizes coordinates; dashed curves can contain extra dash endpoints and fragmented paths. Its raw vertex count cannot establish input point preservation. Native PDF page size rounding also differed from the requested millimetres. Experimental code preserved raw exports and explicitly normalized final SVG/PDF, but those files must not be called untouched native exports.

Extended reference-line, Chinese-text and scientific-notation cases failed before successful delivery, with `ApplicationBase_Exit` or `ApplicationBase_LT_execute` SystemError and Windows exit code 3221226505. A traced retry failed at the first Origin connection/startup call and aborted during library cleanup. Inputs remained unchanged and no successful output folder was produced. Multiple Origin processes were present; their causal relationship to the failures is unconfirmed. No process was force-killed, license repaired, registration changed, sandbox bypassed or software reinstalled by this acceptance run.

The experimental adapter, raw logs and files are retained outside the release. Pure-function tests can prove SVG mapping and PDF transformations, but cannot prove native application stability. Do not label this route accepted until a fresh external process can finish the extended cases and independently reopen their projects and exports. Reinstallation changes executable paths, COM registration, fonts or user templates and therefore requires fresh acceptance; it does not establish data changes or license repair by itself.

Scientific review still requires author confirmation of evidence level, units, uncertainty, source authorization and reference-boundary interpretation. Archived plot series must not be called machine-raw data without source evidence. Reference estimates and B1 sensitivity retain their unverified scientific status.
