# OctoPrint Slicer

<img src="/docs/screenshot1.png" width="600">

## Plugin features
- [PrusaSlicer](https://www.prusa3d.com/page/prusaslicer_424/) support
- Rotate, scale, and move STL models.
- Slice multiple STLs at a time. Split 1 STL into unconnected parts.
- Circular print bed support (do you have a delta printer?).
- High-light overhang areas. Automatically orient the model for better result ("lay flat").
- Slice based on PrusaSlicer profiles you upload to OctoPrint.
- Customizable slicer settings, including Basic (layer height, bed temperature ...) and Advanced (print speed, start/end G-code ...).
- More is coming...

## Setup
### Online:
Install via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
or manually using this URL:

    https://github.com/Garr-R/OctoPrint-Slicer/archive/refs/heads/master.zip

### Offline (Bundled with PruasSlicer v2.4.2): 

1. Download the following zip file to a device with internet connection
    - https://github.com/Garr-R/OctoPrint-Slicer/archive/refs/heads/offline.zip
2. Upload it to OctoPrint using the OctoPrint Plugin Manager:
    - Open the OctoPrint Settings Menu
    - Navigate to the "Plugin Manager" tab
    - Select the  "Get More" button
    - Select the "Browse" button underneath "from an uploaded file"
    - Upload the newly downloaded "OctoPrint-Slicer-offline.zip" file
    - Select "Install"
    - Restart OctoPrint when finished

## Importing your printer's PrusaSlicer profile

[Click here for instructions on how to export and import your PrusaSlicer profiles](https://github.com/Garr-R/OctoPrint-Slicer/wiki/Exporting-and-importing-PrusaSlicer-profiles)

## Future plans

- [ ] More adjustable profile settings
- [ ] Setup wizard that helps explain extracting and importing PrusaSlicer profiles
- [ ] Update Docker container for future development support
- [ ] Support Windows OctoPrint configurations
- [ ] Make compatible with the latest version of PrusaSlicer (v2.6)
- [ ] OctoPrint slicing profile overhaul (Use Print/Filament/Printer profiles from [official vendor bundles](https://github.com/prusa3d/PrusaSlicer-settings/tree/master/live))
  
## More Photos

<img src="/docs/screenshot2.png" width="600">
<img src="/docs/screenshot3.png" width="600">
<img src="/docs/screenshot4.png" width="600">

## Thank you to [Kenneth Jiang](https://github.com/kennethjiang/), [Foosel](https://github.com/foosel), [Eyal](https://github.com/eyal0), [Joshwills](https://github.com/joshwills), and many many others for building the original plugins and the OctoPrint Mixins! 
I'm standing on the shoulders of giants and doubt I would've been able to start this project without the exsisting code and infrastructure. 
