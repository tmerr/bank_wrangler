# development script: fetch the required js libs into report/libs
wget -P libs https://cdn.datatables.net/v/dt/jq-2.2.4/dt-1.10.15/datatables.min.css
wget -P libs https://cdn.datatables.net/v/dt/jq-2.2.4/dt-1.10.15/datatables.min.js
wget -P libs https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.6.0/Chart.bundle.min.js
wget -P libs https://unpkg.com/purecss@1.0.0/build/pure-min.css

ZIPNAME=noUiSlider.10.0.0.zip
wget -P libs https://github.com/leongersen/noUiSlider/releases/download/10.0.0/"$ZIPNAME"
unzip libs/"$ZIPNAME" -d libs
rm libs/"$ZIPNAME"
