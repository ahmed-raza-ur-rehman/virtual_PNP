#!/bin/bash
# Run full RTL-to-GDSII via OpenLane
export PDK_ROOT=${PDK_ROOT:-$HOME/pdk}
openlane synthesis/openlane/config.json
echo "GDS output in runs/"
