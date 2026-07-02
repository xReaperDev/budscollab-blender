# BudsCollab for Blender

Blender add-on for testing BudsCollab asset workflows from the 3D View.

## Install from a ZIP

1. Download `budscollab-blender.zip` from the public repo release.
2. Open Blender.
3. Go to `Edit > Preferences > Add-ons`.
4. Click `Install from Disk...`.
5. Select the ZIP and enable `BudsCollab for Blender`.

When this package is exported to its public repo, releases should live at:

```txt
https://github.com/xReaperDev/budscollab-blender/releases
```

For private monorepo testing, install the `integrations/blender` folder directly
from a local checkout.

## Use

Open the `BudsCollab` tab in the 3D View sidebar.

The first test shell includes login, space/room selection, validation, upload
selected, open web preview, and Unity handoff placeholders. The public product
name is BudsCollab for Blender; internally it still uses the BudsCollab bridge
protocol and shared asset contracts.
