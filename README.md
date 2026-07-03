# BudsCollab for Blender

Blender add-on for connecting to BudsCollab spaces from the 3D View and preparing selected meshes as GLB assets.

## Install from a ZIP

1. Download `budscollab-blender-v0.1.2.zip` from the public repo release.
2. Open Blender.
3. Go to `Edit > Preferences > Add-ons`.
4. Click `Install from Disk...`.
5. Select the ZIP and enable `BudsCollab for Blender`.

Use the latest release:

```txt
https://github.com/xReaperDev/budscollab-blender/releases
```

## Use

Open the `BudsCollab` tab in the 3D View sidebar.

1. Click `Open BudsCollab Login` if you need to sign in.
2. Create a read-only MCP token from the BudsCollab MCP connect guide, then paste it into `Access Token`.
3. Click `Connect and Load Spaces`.
4. Pick a fetched space and room from the dropdowns.
5. Use `Open Selected Room` to open that room in BudsCollab.
6. Select mesh objects, run `Check Selected Asset`, then `Export Selected GLB`.

This package is intentionally Blender-only. Cross-app handoff and inbound import are not shown in this add-on until those flows have real endpoints.
