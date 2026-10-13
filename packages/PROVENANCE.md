# UI foundation provenance

`dew-ui/` and `styles/` are a tracked-file snapshot of the existing BME frontend design foundation, imported at the project owner's request to retain the existing frontend scheme.

- Source project: `BME_platform_frontend`
- Source commit: `4bf2cb14cabc85b4d09daa3e144453f2624c9d4e`
- Source paths: `packages/dew-ui/`, `packages/styles/`
- Imported: 2026-10-13
- Method: copy Git-tracked files only, preserving source headers and notices; no credentials, dependencies, build output or application stores copied.

This repository builds without the source checkout. Changes to these packages are local to Workbench until explicitly synchronized; do not silently follow files in an adjacent directory. A future shared package release may replace this snapshot once a versioned distribution exists.

No new open-source licensing grant is made by this snapshot. Preserve the original ownership and any third-party notices already present in copied assets.

The collaboration migration additionally imports packages/editor and work views/services from the same source frontend commit, and backend work-domain services/models from BME_platform_flask commit 10f03de7b944bf29e12c4d82b418a03f3df14e91. Training models/authentication/storage are replaced by explicit workbench adapters; no training passwords are copied.
