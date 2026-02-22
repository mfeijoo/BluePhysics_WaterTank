    import QtQuick 2.7
    import QtQuick.Controls 2.3
    import QtQuick.Layouts 1.3
    import QtCharts 2.2
    import QtQuick.Controls.Material 2.0 
    import QtQuick.Dialogs 1.0

    Item {
        id: measureview
        anchors.fill: parent
        visible: false
        property var colors : [Material.color(Material.LightBlue), Material.color(Material.LightGreen),Material.color(Material.Red), Material.color(Material.Grey),Material.color(Material.Orange), Material.color(Material.Teal),Material.color(Material.Lime), Material.color(Material.Cyan)]
        property var fullintegralsnow: []
        property bool dataanalyzed: false
        property int numberofchannels: 8
        property real maxy: 1
        property string fileselected: 'none'
        property var listallshots: []
        property real maxypulses: 1
        property real maxynopulses: 1
        property real cartridgeincomboboxindex: 2

        Dialog {
            id: dialogerror
            visible: false
            width: 300
            height: 150
            x: (parent.width - width) / 2
            y: (parent.height - height) / 2
            standardButtons: Dialog.Ok
            title: 'General Error'
            onAccepted: {visible = false}
        }

        ToolBar {
            id: measuretoolbar
            anchors.top: parent.top
            width: parent.width
            height: 50

            RowLayout {
                anchors.fill: parent
                ToolButton{
                    icon.source: "icons/menu.png"
                    onClicked: navigationdrawer.open()
                }

                Label {
                    text: "MEASURE"
                    font.pixelSize: 20
                    font.bold: true
                }

                ToolButton {

                    id: startbutton
                    icon.source: "icons/play.png"
                    objectName: "startbutton"
                    onClicked: {
                        dataanalyzed = false
                        xaxis.min = 0
                        xaxis.max =60
                        yaxis.min = 0
                        yaxis.max = 1
                        yaxis.titleText = "cumulative voltage every 300 ms (V)"
                        tempxaxis.min = 0
                        tempxaxis.max = 60
                        psxaxis.min = 0
                        psxaxis.max = 60
                        allshotsch0text.text = '--'
                        allshotsch1text.text = '--'
                        singleshotch0text.text = '--'
                        singleshotch1text.text = '--'
                        allshotsch2text.text = '--'
                        allshotsch3text.text = '--'
                        singleshotch2text.text = '--'
                        singleshotch3text.text = '--'
                        allshotsch4text.text = '--'
                        allshotsch5text.text = '--'
                        singleshotch4text.text = '--'
                        singleshotch5text.text = '--'
                        allshotsch6text.text = '--'
                        allshotsch7text.text = '--'
                        singleshotch6text.text = '--'
                        singleshotch7text.text = '--'
                        singleshotpulsestext.text = '--'
                        allshotspulsestext.text = '--'
                        regulatebutton.enabled = false
                        darkcurrentbutton.enabled = false
                        drawsettingsbutton.enabled = false
                        autodetect.enabled = false
                        chartchs.removeAllSeries()
                        ma.partialintegralscalculated = false
                        calcshotsbutton.enabled = false
                        deletelimits.enabled = false
                        ma.starttimes = []
                        ma.finishtimes = []

                        for (var i = 0; i < numberofchannels; i++){
                            chartchs.createSeries(ChartView.SeriesTypeLine, 'ch' + i, xaxis, yaxis)
                            chartchs.series('ch'+i).color = colors[i]
                            chartchs.series('ch'+i).useOpenGL = true
                        }
                        chartchs.createSeries(ChartView.SeriesTypeLine, 'chargedose', xaxis, yaxis)
                        chartchs.series('chargedose').color = Material.color(Material.Pink)
                        chartchs.series('chargedose').useOpenGL = true
                        chartchs.series('chargedose').visible = chargedoseplotcheckbox.checked
                        
                        chartchs.createSeries(ChartView.SeriesTypeScatter, 'pulse', xaxis, yaxis)
                        chartchs.series('pulse').color = Material.color(Material.DeepOrange)
                        chartchs.series('pulse').useOpenGL = true
                        chartchs.series('pulse').markerSize = 5
                        chartchs.series('pulse').markerShape = ScatterSeries.MarkerShapeCircle
                        chartchs.series('pulse').z = 2
                    }
                    //check if the box is connectd and the cartridge is connected
                    //comment if emulator
                    Component.onCompleted: {myseries.checkacqucartridge()}
                }

                ToolButton {
                    icon.source: "icons/stop.png"
                    objectName: "stopbutton"
                    onClicked: {
                        regulatebutton.enabled = true
                        darkcurrentbutton.enabled = true
                        drawsettingsbutton.enabled = true
                        yaxis.titleText = "<p>cumulative charge every 800 &mu;s (nC)</p>"
                    }
                }

                Text {
                    text: '   Cut Off: '
                    color: 'lightgrey'
                }

                ComboBox {
                        id: cutoff
                        model: [0.5, 10, 20, 40, 100, 150]
                        currentIndex: 3
                        onCurrentIndexChanged: myseries.cutoffchange(currentIndex)
                    }

                ToolButton {
                   id: autodetect
                    text: 'autodetect'
                    enabled: false
                    onClicked: {
                        if (ma.starttimes.length > 0){
                            for (var k = 0; k < ma.starttimes.length; k++){
                                if (ma.starttimes[k] !== -1) {
                                    chartchs.removeSeries(chartchs.series('start' + k))
                                    ma.starttimes[k] = -1
                                }
                            }
                        }
                        if (ma.finishtimes.length > 0){
                            for (var l = 0; l < ma.finishtimes.length; l++){
                                if (ma.finishtimes[l] !== -1){
                                    chartchs.removeSeries(chartchs.series('finish' + l))
                                    ma.finishtimes[l] = -1
                                }
                            }
                        }
                        myseries.autodetect()
                    }
                }

                ToolButton {
                    id: deletelimits
                    text: 'delete limits'
                    enabled: false
                    onClicked: {
                        if (ma.starttimes.length > 0){
                            for (var k = 0; k < ma.starttimes.length; k++){
                                if (ma.starttimes[k] !== -1) {
                                    chartchs.removeSeries(chartchs.series('start' + k))
                                    ma.starttimes[k] = -1
                                }
                            }
                        }
                        if (ma.finishtimes.length > 0){
                            for (var l = 0; l < ma.finishtimes.length; l++){
                                if (ma.finishtimes[l] !== -1){
                                    chartchs.removeSeries(chartchs.series('finish' + l))
                                    ma.finishtimes[l] = -1
                                }
                            }
                        }
                        console.log('starttimes after deleting: ' + ma.starttimes)
                    }
                }

                ToolButton {
                    id: calcshotsbutton
                    text: 'Calc. Shots'
                    enabled: false
                    onClicked: {
                        console.log('start times: ' + ma.starttimes)
                        console.log('finishtimes: ' + ma.finishtimes)
                        myseries.calcshots(ma.starttimes, ma.finishtimes)

                    }
                }

                CheckBox {
                    id: pulsescheck
                    text: 'Pulses'
                    enabled: true
                    onClicked: {
                        myseries.pulsescheck(pulsescheck.checked)
                        yaxis.titleText = checked ? "<p>cumulative charge every 750 &mu;s (nC)</p>" : "cumulative charge every 300 ms (nC)"
                        if (true) {
                            //console.log('pulses checked')
                            yaxis.max = checked ? maxypulses : maxynopulses
                            for (var k=0; k < numberofchannels; k++){
                                myseries.updateserieanalyze(chartchs.series('ch' + k), 'ch' + k + 'c', checked)
                            }
                            if (checked) {
                                myseries.updateserieanalyze(chartchs.series('pulse'), 'pulsetoplot', checked)
                            }
                        }
                    }
                }

                ToolButton {
                    icon.source: "icons/settings.png"
                    onClicked: settingsdrawer.open()
                }
            }
        }

        Drawer {
            id: settingsdrawer
            edge: Qt.BottomEdge
            height: 100
            width: parent.width

            RowLayout {
                anchors.centerIn: parent
                GridLayout{
                    columns: 4
                    CheckBox {
                        text: 'ch0'
                        checked: true
                        onClicked: {
                            chartchs.series('ch0').visible = checked
                        }
                    }
                    CheckBox {
                        text: 'ch1'
                        checked: true
                        onClicked: {
                            chartchs.series('ch1').visible = checked
                        }
                    }
                    CheckBox {
                        text: 'ch2'
                        checked: true
                        onClicked: {
                            chartchs.series('ch2').visible = checked
                        }
                    }
                    CheckBox {
                        text: 'ch3'
                        checked: true
                        onClicked: {
                            chartchs.series('ch3').visible = checked
                        }
                    }
                    CheckBox {
                        text: 'ch4'
                        checked: true
                        onClicked: {
                            chartchs.series('ch4').visible = checked
                        }
                    }
                    CheckBox {
                        text: 'ch5'
                        checked: true
                        onClicked: {
                            chartchs.series('ch5').visible = checked
                        }
                    }
                    CheckBox {
                        text: 'ch6'
                        checked: true
                        onClicked: {
                            chartchs.series('ch6').visible = checked
                        }
                    }
                    CheckBox {
                        text: 'ch7'
                        checked: true
                        onClicked: {
                            chartchs.series('ch7').visible = checked
                        }
                    }
                }
                CheckBox {
                    id: chargedoseplotcheckbox
                    text: 'chargedose'
                    checked: false

                    onClicked: {
                        chartchs.series('chargedose').visible = checked
                    }
                }
                GridLayout {
                    columns: 2
                    RadioButton {
                        id: charge
                        text: 'charge'
                        autoExclusive: true
                        checked: true
                        onClicked: {
                            myseries.chargecheck(checked)
                            if (dataanalyzed) {
                                if (settingsview.cartridgeincomboboxindex == 0) {
                                    ch0box.title = 'CH0'
                                    allshotsch0text.text = fullintegralsnow[0]
                                    ch0units.text = 'nC'
                                    allshotsch1text.text = fullintegralsnow[1]
                                    ch1box.title = 'CH1'
                                    ch1units.text = 'nC'
                                }
                                if (settingsview.cartridgeincomboboxindex == 1){
                                    allshotsch0text.text = fullintegralsnow[0]
                                    ch0box.title = 'ch0'
                                    allshotsch1text.text = fullintegralsnow[1]
                                    ch1box.title = 'ch1'
                                    allshotsch2text.text = fullintegralsnow[2]
                                    ch2box.title = 'ch2'
                                    allshotsch3text.text = fullintegralsnow[3]
                                    ch3box.title = 'ch3'
                                    allshotsch4text.text = fullintegralsnow[4]
                                    ch4box.title = 'ch4'
                                    allshotsch5text.text = fullintegralsnow[5]
                                    ch5box.title = 'ch5'
                                    allshotsch6text.text = fullintegralsnow[6]
                                    ch6box.title = 'ch6'
                                    allshotsch7text.text = fullintegralsnow[7]
                                    ch7box.title = 'ch7'
                                    ch0units.text = 'nC'
                                    ch1units.text = 'nC'
                                    ch2units.text = 'nC'
                                    ch3units.text = 'nC'
                                    ch4units.text = 'nC'
                                    ch5units.text = 'nC'
                                    ch6units.text = 'nC'
                                    ch7units.text = 'nC'

                                }
                                if (settingsview.cartridgeincomboboxindex == 2) {
                                    allshotsch0text.text = fullintegralsnow[0]
                                    ch0box.title = 'ch0'
                                    allshotsch1text.text = fullintegralsnow[1]
                                    ch1box.title = 'ch1'
                                    allshotsch2text.text = fullintegralsnow[2]
                                    ch2box.title = 'ch2'
                                    allshotsch3text.text = fullintegralsnow[3]
                                    ch3box.title = 'ch3'
                                    allshotsch4text.text = fullintegralsnow[4]
                                    ch4box.title = 'ch4'
                                    allshotsch5text.text = fullintegralsnow[5]
                                    ch5box.title = 'ch5'
                                    allshotsch6text.text = fullintegralsnow[6]
                                    ch6box.title = 'ch6'
                                    allshotsch7text.text = fullintegralsnow[7]
                                    ch7box.title = 'ch7'
                                    ch0units.text = 'nC'
                                    ch1units.text = 'nC'
                                    ch2units.text = 'nC'
                                    ch3units.text = 'nC'
                                    ch4units.text = 'nC'
                                    ch5units.text = 'nC'
                                    ch6units.text = 'nC'
                                    ch7units.text = 'nC'
                                }
                            }
                        }
                    }

                    RadioButton {
                        id: chargepropdose
                        text: '~chdose'
                        autoExclusive: true
                        onClicked: {
                            myseries.chargedosecheck(checked)
                            if (dataanalyzed) {
                                if (settingsview.cartridgeincomboboxindex == 0){
                                    ch0box.title = 'SENSOR 0'
                                    allshotsch1text.text = '--'
                                    ch1box.title = '--'
                                    ch1units.text = '--'
                                    allshotsch0text.text = fullintegralsnow[2]
                                    ch0units.text = 'nC'
                                }
                                if (settingsview.cartridgeincomboboxindex == 1) {
                                    allshotsch0text.text = fullintegralsnow[8]
                                    ch0box.title = 'SENSOR 0'
                                    allshotsch1text.text = '--' 
                                    ch1box.title = '--'
                                    allshotsch2text.text = fullintegralsnow[9]
                                    ch2box.title = 'SENSOR 1'
                                    allshotsch3text.text = '--'
                                    ch3box.title = '--'
                                    allshotsch4text.text = fullintegralsnow[10]
                                    ch4box.title = 'SENSOR 2'
                                    allshotsch5text.text = '--'
                                    ch5box.title = '--'
                                    allshotsch6text.text = fullintegralsnow[11]
                                    ch6box.title = 'SENSOR 3'
                                    allshotsch7text.text = '--'
                                    ch7box.title = '--'
                                    ch0units.text = 'nC'
                                    ch1units.text = '--'
                                    ch2units.text = 'nC'
                                    ch3units.text = '--'
                                    ch4units.text = 'nC'
                                    ch5units.text = '--'
                                    ch6units.text = 'nC'
                                    ch7units.text = '--'

                                }
                                if (settingsview.cartridgeincomboboxindex == 2){
                                    ch0box.title = 'SENSOR 0'
                                    allshotsch1text.text = '--'
                                    ch1box.title = '--'
                                    ch1units.text = '--'
                                    ch2box.title = 'SENSOR 1'
                                    ch3box.title = 'SENSOR 2'
                                    ch4box.title = 'SENSOR 3'
                                    ch5box.title = 'SENSOR 4'
                                    ch6box.title = 'SENSOR 5'
                                    ch7box.title = 'SENSOR 6'
                                    allshotsch0text.text = fullintegralsnow[8]
                                    ch0units.text = 'nC'
                                    allshotsch2text.text = fullintegralsnow[9]
                                    ch2units.text = 'nC'
                                    allshotsch3text.text = fullintegralsnow[10]
                                    ch3units.text = 'nC'
                                    allshotsch4text.text = fullintegralsnow[11]
                                    ch4units.text = 'nC'
                                    allshotsch5text.text = fullintegralsnow[12]
                                    ch5units.text = 'nC'
                                    allshotsch6text.text = fullintegralsnow[13]
                                    ch6units.text = 'nC'
                                    allshotsch7text.text = fullintegralsnow[14]
                                    ch7units.text = 'nC'
                                }
                            }
                        }
                }

                RadioButton {
                    id: dose
                    text: 'dose'
                    autoExclusive: true
                    onClicked: {
                        myseries.dosecheck(checked)
                        if (dataanalyzed) {
                            if (settingsview.cartridgeincomboboxindex == 0) {
                                if (centigrays.checked) {
                                    ch0box.title = 'SENSOR 0'
                                    allshotsch1text.text = '--'
                                    ch1box.title = '--'
                                    ch1units.text = '--'
                                    allshotsch0text.text = fullintegralsnow[3]
                                    ch0units.text = 'cGy'
                                }
                                if (grays.checked) {
                                    ch0box.title = 'SENSOR 0'
                                    allshotsch1text.text = '--'
                                    ch1box.title = '--'
                                    ch1units.text = '--'
                                    allshotsch0text.text = fullintegralsnow[4]
                                    ch0units.text = 'Gy'
                                }
                            }
                            if (settingsview.cartridgeincomboboxindex == 1) {

                                if (centigrays.checked) {
                                    allshotsch0text.text = fullintegralsnow[12]
                                    ch0box.title = 'SENSOR 0'
                                    allshotsch1text.text = '--' 
                                    ch1box.title = '--'
                                    allshotsch2text.text = fullintegralsnow[13]
                                    ch2box.title = 'SENSOR 1'
                                    allshotsch3text.text = '--'
                                    ch3box.title = '--'
                                    allshotsch4text.text = fullintegralsnow[14]
                                    ch4box.title = 'SENSOR 2'
                                    allshotsch5text.text = '--'
                                    ch5box.title = '--'
                                    allshotsch6text.text = fullintegralsnow[15]
                                    ch6box.title = 'SENSOR 3'
                                    allshotsch7text.text = '--'
                                    ch7box.title = '--'
                                    ch0units.text = 'cGy'
                                    ch1units.text = '--'
                                    ch2units.text = 'cGy'
                                    ch3units.text = '--'
                                    ch4units.text = 'cGy'
                                    ch5units.text = '--'
                                    ch6units.text = 'cGy'
                                    ch7units.text = '--'
                                }
                                if (grays.checked) {
                                    allshotsch0text.text = fullintegralsnow[16]
                                    ch0box.title = 'SENSOR 0'
                                    allshotsch1text.text = '--' 
                                    ch1box.title = '--'
                                    allshotsch2text.text = fullintegralsnow[17]
                                    ch2box.title = 'SENSOR 1'
                                    allshotsch3text.text = '--'
                                    ch3box.title = '--'
                                    allshotsch4text.text = fullintegralsnow[18]
                                    ch4box.title = 'SENSOR 2'
                                    allshotsch5text.text = '--'
                                    ch5box.title = '--'
                                    allshotsch6text.text = fullintegralsnow[19]
                                    ch6box.title = 'SENSOR 3'
                                    allshotsch7text.text = '--'
                                    ch7box.title = '--'
                                    ch0units.text = 'Gy'
                                    ch1units.text = '--'
                                    ch2units.text = 'Gy'
                                    ch3units.text = '--'
                                    ch4units.text = 'Gy'
                                    ch5units.text = '--'
                                    ch6units.text = 'Gy'
                                    ch7units.text = '--'

                                }
                            }
                            if (settingsview.cartridgeincomboboxindex == 2){

                                if (centigrays.checked) {
                                    ch0box.title = 'SENSOR 0'
                                    allshotsch1text.text = '--'
                                    ch1box.title = '--'
                                    ch1units.text = '--'
                                    ch2box.title = 'SENSOR 1'
                                    ch3box.title = 'SENSOR 2'
                                    ch4box.title = 'SENSOR 3'
                                    ch5box.title = 'SENSOR 4'
                                    ch6box.title = 'SENSOR 5'
                                    ch7box.title = 'SENSOR 6'
                                    allshotsch0text.text = fullintegralsnow[15]
                                    ch0units.text = 'cGy'
                                    allshotsch2text.text = fullintegralsnow[16]
                                    ch2units.text = 'cGy'
                                    allshotsch3text.text = fullintegralsnow[17]
                                    ch3units.text = 'cGy'
                                    allshotsch4text.text = fullintegralsnow[18]
                                    ch4units.text = 'cGy'
                                    allshotsch5text.text = fullintegralsnow[19]
                                    ch5units.text = 'cGy'
                                    allshotsch6text.text = fullintegralsnow[20]
                                    ch6units.text = 'cGy'
                                    allshotsch7text.text = fullintegralsnow[21]
                                    ch7units.text = 'cGy'
                                }
                                if (grays.checked) {
                                    ch0box.title = 'SENSOR 0'
                                    allshotsch1text.text = '--'
                                    ch1box.title = '--'
                                    ch1units.text = '--'
                                    ch2box.title = 'SENSOR 1'
                                    ch3box.title = 'SENSOR 2'
                                    ch4box.title = 'SENSOR 3'
                                    ch5box.title = 'SENSOR 4'
                                    ch6box.title = 'SENSOR 5'
                                    ch7box.title = 'SENSOR 6'
                                    allshotsch0text.text = fullintegralsnow[22]
                                    ch0units.text = 'Gy'
                                    allshotsch2text.text = fullintegralsnow[23]
                                    ch2units.text = 'Gy'
                                    allshotsch3text.text = fullintegralsnow[24]
                                    ch3units.text = 'Gy'
                                    allshotsch4text.text = fullintegralsnow[25]
                                    ch4units.text = 'Gy'
                                    allshotsch5text.text = fullintegralsnow[26]
                                    ch5units.text = 'Gy'
                                    allshotsch6text.text = fullintegralsnow[27]
                                    ch6units.text = 'Gy'
                                    allshotsch7text.text = fullintegralsnow[28]
                                    ch7units.text = 'Gy'
                                }
                            }

                        }
                    }
                }
            }

            ColumnLayout {
                RadioButton {
                    id: grays
                    text: 'Gy'
                    autoExclusive: true
                    onClicked:{
                        myseries.grayscheck(checked)
                        allshotssensorunits.text = dose.checked ? 'Gy' : 'nC'
                        allshotscerenkovunits.text = dose.checked ? '--' : 'nC'
                        singleshotensorunits.text = dose.checked ? 'Gy' : 'nC'
                        singleshotcerenkovunits.text = dose.checked ? '--' : 'nC'
                    }
                }

                RadioButton {
                    id: centigrays
                    text: 'cGy'
                    autoExclusive: true
                    checked: true
                    onClicked: {
                        myseries.centygrayscheck(checked)
                        allshotssensorunits.text = dose.checked ? 'cGy' : 'nC'
                        allshotscerenkovunits.text = dose.checked ? '--' : 'nC'
                        singleshotensorunits.text = dose.checked ? 'cGy' : 'nC'
                        singleshotcerenkovunits.text = dose.checked ? '--' : 'nC'
                    }
                }
            }

            RowLayout{

                RadioButton {
                    id: noneradiobutton
                    text: "none"
                    autoExclusive: true
                    checked: true
                }

                RadioButton {
                    id: tempradiobutton
                    text: "temp"
                    autoExclusive: true
                }
                RadioButton {
                    id: psradiobutton
                    text: "PS"
                    autoExclusive: true
                }
                RadioButton {
                    id: minus15vradiobutton
                    text: "-15V"
                    autoExclusive: true
                }
                RadioButton {
                    id: v15radiobutton
                    text: "15V"
                    autoExclusive: true
                }
                RadioButton {
                    id: v5radiobutton
                    text: "5V"
                    autoExclusive: true
                }
             }
        }
    }

    Item {
        id: resultsholder
        anchors.top: measuretoolbar.bottom
        anchors.right: parent.right
        width: 250
        anchors.bottom: parent.bottom

        Column {
            anchors.fill: parent
            GroupBox {
                id: coordbox
                height: 100
                width: parent.width - 10
                title: 'CURSOR COORDINATES'

                Text {
                    id: coordxtext
                    anchors.top: parent.top
                    anchors.topMargin: 2
                    anchors.left: parent.left
                    anchors.rightMargin: 5
                    text: 'x: '
                    color: Material.color(Material.Yellow)
                    font.bold: true
                    font.pixelSize: 20
                }
                Text {
                    id: coordytext
                    anchors.top: coordxtext.bottom
                    anchors.topMargin: 2
                    anchors.left: parent.left
                    anchors.rightMargin: 5
                    text: 'y: '
                    color: Material.color(Material.Yellow)
                    font.bold: true
                    font.pixelSize: 20
                }
            }

            ComboBox{
                id: sensorselect
                height: 50
                width: parent.width - 10
                model: ['Single Shots', 'All Shots']
            }

            GroupBox {
                id: ch0box
                height: 90
                width: parent.width - 10
                title: 'CH0'

                Text {
                    id: singleshotch0text
                    visible: sensorselect.currentIndex == 0 ? true: false
                    anchors.right: ch0units.left
                    anchors.rightMargin: 10
                    color: colors[0]
                    font.pixelSize: 40
                    font.bold: true
                    text: '--'
                }

                Text {
                    id: allshotsch0text
                    visible: sensorselect.currentIndex == 1 ? true: false
                    anchors.right: ch0units.left
                    anchors.rightMargin: 5
                    color: colors[0]
                    font.pixelSize: 40
                    font.bold: true
                    text: '--'
                }

                Text {
                    id: ch0units
                    anchors.right: parent.right
                    anchors.bottom: singleshotch0text.bottom
                    anchors.bottomMargin: 5
                    color: colors[0]
                    font.pixelSize: 20
                    font.bold: true
                    text: '--'
                }
            }
            GroupBox {
                id: ch1box
                height: 90
                width: parent.width - 10
                title: 'CH1'


                Text {
                    id: singleshotch1text
                    visible: sensorselect.currentIndex == 0 ? true: false
                    anchors.right: ch1units.left
                    anchors.rightMargin: 10
                    color: colors[1]
                    font.pixelSize: 40
                    font.bold: true
                    text: '--'
                }

                Text {
                    id: allshotsch1text
                    visible: sensorselect.currentIndex == 1 ? true: false
                    anchors.right: ch1units.left
                    anchors.rightMargin: 5
                    color: colors[1]
                    font.pixelSize: 40
                    font.bold: true
                    text: '--'
                }

                Text {
                    id: ch1units
                    anchors.right: parent.right
                    anchors.bottom: singleshotch1text.bottom
                    anchors.bottomMargin: 5
                    color: colors[1]
                    font.pixelSize: 20
                    font.bold: true
                    text: '--'
                }
            }
            GroupBox {
                id: ch2box
                height: 90
                width: parent.width - 10
                title: 'CH2'


                Text {
                    id: singleshotch2text
                    visible: sensorselect.currentIndex == 0 ? true: false
                    anchors.right: ch2units.left
                    anchors.rightMargin: 10
                    color: colors[2]
                    font.pixelSize: 40
                    font.bold: true
                    text: '--'
                }

                Text {
                    id: allshotsch2text
                    visible: sensorselect.currentIndex == 1 ? true: false
                    anchors.right: ch2units.left
                    anchors.rightMargin: 5
                    color: colors[2]
                    font.pixelSize: 40
                    font.bold: true
                    text: '--'
                }

                Text {
                    id: ch2units
                    anchors.right: parent.right
                    anchors.bottom: singleshotch2text.bottom
                    anchors.bottomMargin: 5
                    color: colors[2]
                    font.pixelSize: 20
                    font.bold: true
                    text: '--'
                }
            }
            GroupBox {
                id: ch3box
                height: 90
                width: parent.width - 10
                title: 'CH3'


                Text {
                    id: singleshotch3text
                    visible: sensorselect.currentIndex == 0 ? true: false
                    anchors.right: ch3units.left
                    anchors.rightMargin: 10
                    color: colors[3]
                    font.pixelSize: 40
                    font.bold: true
                    text: '--'
                }

                Text {
                    id: allshotsch3text
                    visible: sensorselect.currentIndex == 1 ? true: false
                    anchors.right: ch3units.left
                    anchors.rightMargin: 5
                    color: colors[3]
                    font.pixelSize: 40
                    font.bold: true
                    text: '--'
                }

                Text {
                    id: ch3units
                    anchors.right: parent.right
                    anchors.bottom: singleshotch3text.bottom
                    anchors.bottomMargin: 5
                    color: colors[3]
                    font.pixelSize: 20
                    font.bold: true
                    text: '--'
                }
            }
            GroupBox {
                id: ch4box
                height: 90
                width: parent.width - 10
                title: 'CH4'


                Text {
                    id: singleshotch4text
                    visible: sensorselect.currentIndex == 0 ? true: false
                    anchors.right: ch4units.left
                    anchors.rightMargin: 10
                    color: colors[4]
                    font.pixelSize: 40
                    font.bold: true
                    text: '--'
                }

                Text {
                    id: allshotsch4text
                    visible: sensorselect.currentIndex == 1 ? true: false
                    anchors.right: ch4units.left
                    anchors.rightMargin: 5
                    color: colors[4]
                    font.pixelSize: 40
                    font.bold: true
                    text: '--'
                }

                Text {
                    id: ch4units
                    anchors.right: parent.right
                    anchors.bottom: singleshotch4text.bottom
                    anchors.bottomMargin: 5
                    color: colors[4]
                    font.pixelSize: 20
                    font.bold: true
                    text: '--'
                }
            }
            GroupBox {
                id: ch5box
                height: 90
                width: parent.width - 10
                title: 'CH5'


                Text {
                    id: singleshotch5text
                    visible: sensorselect.currentIndex == 0 ? true: false
                    anchors.right: ch5units.left
                    anchors.rightMargin: 10
                    color: colors[5]
                    font.pixelSize: 40
                    font.bold: true
                    text: '--'
                }

                Text {
                    id: allshotsch5text
                    visible: sensorselect.currentIndex == 1 ? true: false
                    anchors.right: ch5units.left
                    anchors.rightMargin: 5
                    color: colors[5]
                    font.pixelSize: 40
                    font.bold: true
                    text: '--'
                }

                Text {
                    id: ch5units
                    anchors.right: parent.right
                    anchors.bottom: singleshotch5text.bottom
                    anchors.bottomMargin: 5
                    color: colors[5]
                    font.pixelSize: 20
                    font.bold: true
                    text: '--'
                }
            }
            GroupBox {
                id: ch6box
                height: 90
                width: parent.width - 10
                title: 'CH6'


                Text {
                    id: singleshotch6text
                    visible: sensorselect.currentIndex == 0 ? true: false
                    anchors.right: ch6units.left
                    anchors.rightMargin: 10
                    color: colors[6]
                    font.pixelSize: 40
                    font.bold: true
                    text: '--'
                }

                Text {
                    id: allshotsch6text
                    visible: sensorselect.currentIndex == 1 ? true: false
                    anchors.right: ch6units.left
                    anchors.rightMargin: 5
                    color: colors[6]
                    font.pixelSize: 40
                    font.bold: true
                    text: '--'
                }

                Text {
                    id: ch6units
                    anchors.right: parent.right
                    anchors.bottom: singleshotch6text.bottom
                    anchors.bottomMargin: 5
                    color: colors[6]
                    font.pixelSize: 20
                    font.bold: true
                    text: '--'
                }
            }
            GroupBox {
                id: ch7box
                height: 90
                width: parent.width - 10
                title: 'CH7'

                Text {
                    id: singleshotch7text
                    visible: sensorselect.currentIndex == 0 ? true: false
                    anchors.right: ch7units.left
                    anchors.rightMargin: 10
                    color: colors[7]
                    font.pixelSize: 40
                    font.bold: true
                    text: '--'
                }

                Text {
                    id: allshotsch7text
                    visible: sensorselect.currentIndex == 1 ? true: false
                    anchors.right: ch7units.left
                    anchors.rightMargin: 5
                    color: colors[7]
                    font.pixelSize: 40
                    font.bold: true
                    text: '--'
                }

                Text {
                    id: ch7units
                    anchors.right: parent.right
                    anchors.bottom: singleshotch7text.bottom
                    anchors.bottomMargin: 5
                    color: colors[7]
                    font.pixelSize: 20
                    font.bold: true
                    text: '--'
                }
            }
            GroupBox {
                id: pulsesbox
                height: 90
                width: parent.width - 10
                title: 'PULSES'

                Text {
                    id: singleshotpulsestext
                    visible: sensorselect.currentIndex == 0 ? true: false
                    anchors.right: parent.right
                    anchors.rightMargin: 10
                    color: Material.color(Material.DeepOrange) 
                    font.pixelSize: 40
                    font.bold: true
                    text: '--'
                }

                Text {
                    id: allshotspulsestext
                    visible: sensorselect.currentIndex == 1 ? true: false
                    anchors.right: parent.right
                    anchors.rightMargin: 10
                    color: Material.color(Material.DeepOrange) 
                    font.pixelSize: 40
                    font.bold: true
                    text: '--'
                }
            }
        }
    }

    ChartView {
        id: chartchs
        theme: ChartView.ChartThemeDark
        anchors.left: parent.left
        anchors.right: resultsholder.left
        anchors.top: measuretoolbar.bottom
        anchors.bottom: chartpowersholder.top
        legend.visible: false

        ValueAxis {
            id: yaxis
            min: 0
            max: 1
            titleText: "<p>cumulative voltage every 300 ms (V)</p>"
        }

        ValueAxis {
            id: xaxis
            min: 0
            max: 60
            titleText: "time (s)"
        }

        Rectangle {
            id: zoomarea
            color: 'transparent'
            border.color: 'red'
            border.width: 1
            visible: false
        }

        MouseArea {
            id: ma
            anchors.fill: parent
            acceptedButtons: { Qt.RightButton | Qt.LeftButton | Qt.MiddleButton}
            property real xstart
            property real ystart
            property var starttimes: []
            property var finishtimes: []
            property var sortedstarttimes: []
            property var sortedfinishtimes: []
            property var partialintegrals: []
            property int lineserieshovered: -1
            hoverEnabled: true
            property bool activezoom: false
            property bool partialintegralscalculated: false
            property bool maxlineflag: false

            onPressAndHold: {
                if (mouse.button & Qt.MiddleButton){
                    xstart = mouseX
                    ystart = mouseY
                }
            }

            onPositionChanged: {
                var p = Qt.point(mouseX, mouseY)
                var cp = chartchs.mapToValue(p, chartchs.series('ch0'))

                if (partialintegralscalculated) {

                    for (var i = 0; i < sortedstarttimes.length; i++) {

                        if (cp.x > sortedstarttimes[i] & cp.x < sortedfinishtimes[i]) {
                            
                            if (settingsview.cartridgeincomboboxindex ==0) {
                                singleshotpulsestext.text = partialintegrals[i][5]
                                if (charge.checked) {
                                    singleshotch0text.text = partialintegrals[i][0]
                                    ch0box.title = 'ch0'
                                    singleshotch1text.text = partialintegrals[i][1]
                                    ch1box.title = 'ch1'
                                    ch0units.text = 'nC'
                                    ch1units.text = 'nC'
                                }
                                if (chargepropdose.checked) {
                                    ch0box.title = 'SENSOR 0'
                                    ch1box.title = '--'
                                    singleshotch0text.text = partialintegrals[i][2]
                                    singleshotch1text.text = '--'
                                    ch0units.text = 'nC'
                                    ch1units.text = '--'
                                }
                                if (dose.checked & centigrays.checked) {
                                    ch0box.title = 'SENSOR 0'
                                    singleshotch1text.text = '--'
                                    ch1box.title = '--'
                                    ch1units.text = '--'
                                    singleshotch0text.text = partialintegrals[i][3]
                                    ch0units.text = 'cGy'
                                    ch1units.text = '--'
                                }
                                if (dose.checked & grays.checked) {
                                    ch0box.title = 'SENSOR 0'
                                    singleshotch1text.text = '--'
                                    ch1box.title = '--'
                                    ch1units.text = '--'
                                    singleshotch0text.text = partialintegrals[i][4]
                                    ch0units.text = 'Gy'
                                }
                            }
                            if (settingsview.cartridgeincomboboxindex == 1) {
                                singleshotpulsestext.text = partialintegrals[i][20]
                                if (charge.checked) {
                                    singleshotch0text.text = partialintegrals[i][0]
                                    ch0box.title = 'ch0'
                                    singleshotch1text.text = partialintegrals[i][1]
                                    ch1box.title = 'ch1'
                                    singleshotch2text.text = partialintegrals[i][2]
                                    ch2box.title = 'ch2'
                                    singleshotch3text.text = partialintegrals[i][3]
                                    ch3box.title = 'ch3'
                                    singleshotch4text.text = partialintegrals[i][4]
                                    ch4box.title = 'ch4'
                                    singleshotch5text.text = partialintegrals[i][5]
                                    ch5box.title = 'ch5'
                                    singleshotch6text.text = partialintegrals[i][6]
                                    ch6box.title = 'ch6'
                                    singleshotch7text.text = partialintegrals[i][7]
                                    ch7box.title = 'ch7'
                                    ch0units.text = 'nC'
                                    ch1units.text = 'nC'
                                    ch2units.text = 'nC'
                                    ch3units.text = 'nC'
                                    ch4units.text = 'nC'
                                    ch5units.text = 'nC'
                                    ch6units.text = 'nC'
                                    ch7units.text = 'nC'

                                }
                                if (chargepropdose.checked) {
                                    ch0box.title = 'SENSOR 0'
                                    ch1box.title = '--'
                                    ch2box.title = 'SENSOR 1'
                                    ch3box.title = '--'
                                    ch4box.title = 'SENSOR 2'
                                    ch5box.title = '--'
                                    ch6box.title = 'SENSOR 3'
                                    ch7box.title = '--'
                                    singleshotch0text.text = partialintegrals[i][8]
                                    ch0units.text = 'nC'
                                    singleshotch2text.text = partialintegrals[i][9]
                                    ch2units.text = 'nC'
                                    singleshotch4text.text = partialintegrals[i][10]
                                    ch4units.text = 'nC'
                                    singleshotch6text.text = partialintegrals[i][11]
                                    ch6units.text = 'nC'
                                    singleshotch1text.text = '--'
                                    ch1units.text = '--'
                                    singleshotch3text.text = '--'
                                    ch3units.text = '--'
                                    singleshotch5text.text = '--' 
                                    ch5units.text = '--'
                                    singleshotch7text.text = '--'
                                    ch7units.text = '--'
                                }
                                if (dose.checked & centigrays.checked) {
                                    ch0box.title = 'SENSOR 0'
                                    ch1box.title = '--'
                                    ch2box.title = 'SENSOR 1'
                                    ch3box.title = '--'
                                    ch4box.title = 'SENSOR 2'
                                    ch5box.title = '--'
                                    ch6box.title = 'SENSOR 3'
                                    ch7box.title = '--'
                                    singleshotch0text.text = partialintegrals[i][12]
                                    ch0units.text = 'cGy'
                                    singleshotch2text.text = partialintegrals[i][13]
                                    ch2units.text = 'cGy'
                                    singleshotch4text.text = partialintegrals[i][14]
                                    ch4units.text = 'cGy'
                                    singleshotch6text.text = partialintegrals[i][15]
                                    ch6units.text = 'cGy'
                                    singleshotch1text.text = '--'
                                    ch1units.text = '--'
                                    singleshotch3text.text = '--'
                                    ch3units.text = '--'
                                    singleshotch5text.text = '--' 
                                    ch5units.text = '--'
                                    singleshotch7text.text = '--'
                                    ch7units.text = '--'
                                }
                                if (dose.checked & grays.checked) {
                                    ch0box.title = 'SENSOR 0'
                                    ch1box.title = '--'
                                    ch2box.title = 'SENSOR 1'
                                    ch3box.title = '--'
                                    ch4box.title = 'SENSOR 2'
                                    ch5box.title = '--'
                                    ch6box.title = 'SENSOR 3'
                                    ch7box.title = '--'
                                    singleshotch0text.text = partialintegrals[i][16]
                                    ch0units.text = 'Gy'
                                    singleshotch2text.text = partialintegrals[i][17]
                                    ch2units.text = 'Gy'
                                    singleshotch4text.text = partialintegrals[i][18]
                                    ch4units.text = 'Gy'
                                    singleshotch6text.text = partialintegrals[i][19]
                                    ch6units.text = 'Gy'
                                    singleshotch1text.text = '--'
                                    ch1units.text = '--'
                                    singleshotch3text.text = '--'
                                    ch3units.text = '--'
                                    singleshotch5text.text = '--' 
                                    ch5units.text = '--'
                                    singleshotch7text.text = '--'
                                    ch7units.text = '--'
                                }
                            }
                            if (settingsview.cartridgeincomboboxindex == 2) {
                                singleshotpulsestext.text = partialintegrals[i][29]
                                if (charge.checked) {
                                    singleshotch0text.text = partialintegrals[i][0]
                                    ch0box.title = 'ch0'
                                    singleshotch1text.text = partialintegrals[i][1]
                                    ch1box.title = 'ch1'
                                    singleshotch2text.text = partialintegrals[i][2]
                                    ch2box.title = 'ch2'
                                    singleshotch3text.text = partialintegrals[i][3]
                                    ch3box.title = 'ch3'
                                    singleshotch4text.text = partialintegrals[i][4]
                                    ch4box.title = 'ch4'
                                    singleshotch5text.text = partialintegrals[i][5]
                                    ch5box.title = 'ch5'
                                    singleshotch6text.text = partialintegrals[i][6]
                                    ch6box.title = 'ch6'
                                    singleshotch7text.text = partialintegrals[i][7]
                                    ch7box.title = 'ch7'
                                    ch0units.text = 'nC'
                                    ch1units.text = 'nC'
                                    ch2units.text = 'nC'
                                    ch3units.text = 'nC'
                                    ch4units.text = 'nC'
                                    ch5units.text = 'nC'
                                    ch6units.text = 'nC'
                                    ch7units.text = 'nC'

                                }
                                if (chargepropdose.checked) {
                                    ch0box.title = 'SENSOR 0'
                                    singleshotch1text.text = '--'
                                    ch1box.title = '--'
                                    ch1units.text = '--'
                                    ch2box.title = 'SENSOR 1'
                                    ch3box.title = 'SENSOR 2'
                                    ch4box.title = 'SENSOR 3'
                                    ch5box.title = 'SENSOR 4'
                                    ch6box.title = 'SENSOR 5'
                                    ch7box.title = 'SENSOR 6'
                                    singleshotch0text.text = partialintegrals[i][8]
                                    ch0units.text = 'nC'
                                    singleshotch2text.text = partialintegrals[i][9]
                                    ch2units.text = 'nC'
                                    singleshotch3text.text = partialintegrals[i][10]
                                    ch3units.text = 'nC'
                                    singleshotch4text.text = partialintegrals[i][11]
                                    ch4units.text = 'nC'
                                    singleshotch5text.text = partialintegrals[i][12]
                                    ch5units.text = 'nC'
                                    singleshotch6text.text = partialintegrals[i][13]
                                    ch6units.text = 'nC'
                                    singleshotch7text.text = partialintegrals[i][14]
                                    ch7units.text = 'nC'
                                }
                                if (dose.checked & centigrays.checked) {
                                    ch0box.title = 'SENSOR 0'
                                    singleshotch1text.text = '--'
                                    ch1box.title = '--'
                                    ch1units.text = '--'
                                    ch2box.title = 'SENSOR 1'
                                    ch3box.title = 'SENSOR 2'
                                    ch4box.title = 'SENSOR 3'
                                    ch5box.title = 'SENSOR 4'
                                    ch6box.title = 'SENSOR 5'
                                    ch7box.title = 'SENSOR 6'
                                    singleshotch0text.text = partialintegrals[i][15]
                                    ch0units.text = 'cGy'
                                    singleshotch2text.text = partialintegrals[i][16]
                                    ch2units.text = 'cGy'
                                    singleshotch3text.text = partialintegrals[i][17]
                                    ch3units.text = 'cGy'
                                    singleshotch4text.text = partialintegrals[i][18]
                                    ch4units.text = 'cGy'
                                    singleshotch5text.text = partialintegrals[i][19]
                                    ch5units.text = 'cGy'
                                    singleshotch6text.text = partialintegrals[i][20]
                                    ch6units.text = 'cGy'
                                    singleshotch7text.text = partialintegrals[i][21]
                                    ch7units.text = 'cGy'
                                }
                                if (dose.checked & grays.checked) {
                                    ch0box.title = 'SENSOR 0'
                                    singleshotch1text.text = '--'
                                    ch1box.title = '--'
                                    ch1units.text = '--'
                                    ch2box.title = 'SENSOR 1'
                                    ch3box.title = 'SENSOR 2'
                                    ch4box.title = 'SENSOR 3'
                                    ch5box.title = 'SENSOR 4'
                                    ch6box.title = 'SENSOR 5'
                                    ch7box.title = 'SENSOR 6'
                                    singleshotch0text.text = partialintegrals[i][22]
                                    ch0units.text = 'Gy'
                                    singleshotch2text.text = partialintegrals[i][23]
                                    ch2units.text = 'Gy'
                                    singleshotch3text.text = partialintegrals[i][24]
                                    ch3units.text = 'Gy'
                                    singleshotch4text.text = partialintegrals[i][25]
                                    ch4units.text = 'Gy'
                                    singleshotch5text.text = partialintegrals[i][26]
                                    ch5units.text = 'Gy'
                                    singleshotch6text.text = partialintegrals[i][27]
                                    ch6units.text = 'Gy'
                                    singleshotch7text.text = partialintegrals[i][28]
                                    ch7units.text = 'Gy'
                                }
                            }
                        }
                     }
                }
                
                coordxtext.text = 'x: ' + cp.x.toFixed(4)
                coordytext.text = 'y: ' + cp.y.toFixed(4)


                if (xstart) {
                    zoomarea.visible = true
                    zoomarea.x = xstart
                    zoomarea.y = ystart
                    zoomarea.width = Math.abs(mouseX - xstart)
                    zoomarea.height = Math.abs(mouseY - ystart)
                }

            }

            onReleased: {
                var xfinish = mouseX
                var yfinish = mouseY
                if (xstart) {
                    var r = Qt.rect(xstart, ystart, Math.abs(xfinish - xstart), Math.abs(yfinish - ystart))
                    chartchs.zoomIn(r)
                    tempxaxis.min = xaxis.min
                    tempxaxis.max = xaxis.max
                    psxaxis.min = xaxis.min
                    psxaxis.max = xaxis.max
                    minus15vxaxis.min = xaxis.min
                    minus15vxaxis.max = xaxis.max
                    v15xaxis.min = xaxis.min
                    v15xaxis.max = xaxis.max
                    ma.activezoom = true
                    xstart = false
                    zoomarea.visible = false
                }
            }

            onClicked: {
                var p = Qt.point(mouseX, mouseY)
                var cp = chartchs.mapToValue(p, chartchs.series('sensor'))
                var valuex = cp.x.toFixed(4)
                var valuey = cp.y.toFixed(4)
                if (mouse.button === Qt.MiddleButton) {
                    chartchs.zoomReset()
                    tempxaxis.min = xaxis.min
                    tempxaxis.max = xaxis.max
                    psxaxis.min = xaxis.min
                    psxaxis.max = xaxis.max
                    minus15vxaxis.min = xaxis.min
                    minus15vxaxis.max = xaxis.max
                    v15xaxis.max = xaxis.max
                    v15xaxis.min = xaxis.min
                    ma.activezoom = false
                }


                else if ((mouse.button === Qt.LeftButton) && (mouse.modifiers & Qt.ControlModifier)){

                    var starlimit = chartchs.createSeries(ChartView.SeriesTypeLine, 'start' + (starttimes.length), xaxis, yaxis)
                    starttimes.push(cp.x)

                    starlimit.color = 'lightgreen'
                    starlimit.style = Qt.DashLine
                    starlimit.append (cp.x, 0)
                    starlimit.append (cp.x, maxynopulses)
                }
                else if ((mouse.button === Qt.RightButton) && (mouse.modifiers & Qt.ControlModifier)){

                    var finishlimit = chartchs.createSeries(ChartView.SeriesTypeLine, 'finish' + (finishtimes.length), xaxis, yaxis)
                    finishtimes.push(cp.x)
                    console.log('name of line: ' + finishlimit.name)
                    finishlimit.color = 'lightsalmon'
                    finishlimit.style = Qt.DashLine
                    finishlimit.append (cp.x, 0)
                    finishlimit.append (cp.x, maxynopulses)
                }
                else if ((mouse.button === Qt.LeftButton) && (mouse.modifiers & Qt.ShiftModifier)){

                    for (var i = 0; i < starttimes.length; i++) {

                        if (cp.x > starttimes[i] - 0.5 && cp.x < starttimes[i] + 0.5){

                            chartchs.removeSeries(chartchs.series('start' + i))
                            starttimes[i] = -1

                        }
                    }

                    for (var j = 0; j < finishtimes.length; j++){

                        if (cp.x > finishtimes[j] - 0.5 && cp.x < finishtimes[j] + 0.5){

                            chartchs.removeSeries(chartchs.series('finish' + j))
                            finishtimes[j] = -1

                        }
                    }
                }
                else if ((mouse.button === Qt.LeftButton) && (mouse.modifiers & Qt.AltModifier)){
                    if (!maxlineflag){
                        var maxline = chartchs.createSeries(ChartView.SeriesTypeLine, 'maxline', xaxis, yaxis)
                        maxline.color = 'lightsalmon'
                        maxline.style = Qt.DashLine
                        maxline.append(0, cp.y)
                        maxline.append(1200, cp.y)
                        var halfline = chartchs.createSeries(ChartView.SeriesTypeLine, 'halfline', xaxis, yaxis)
                        halfline.color = 'lightgreen'
                        halfline.style = Qt.DashLine
                        halfline.append(0, cp.y/2)
                        halfline.append(1200, cp.y/2)
                        maxlineflag = true
                    }
                    else {
                        chartchs.removeSeries(chartchs.series('maxline'))
                        chartchs.removeSeries(chartchs.series('halfline'))
                        maxlineflag = false
                    }
                }
            }
        }
    }

    Item {
        id: chartpowersholder
        anchors.left: parent.left
        anchors.right: resultsholder.left
        height: (parent.height - 50)/2
        y: noneradiobutton.checked ? parent.height : parent.height / 2

        ChartView{
            id: chartps
            theme: ChartView.ChartThemeDark
            anchors.fill: parent
            visible: psradiobutton.checked

            ValueAxis{
                id: psyaxis
                min: 56
                max: 60
                titleText: "Voltage (V)"
            }


            ValueAxis{
                id: psxaxis
                min: 0
                max: 60
                titleText: "Time (s)"
            }

            LineSeries{
                id: psserie
                name: "PS"
                axisX: psxaxis
                axisY: psyaxis

            }
        }

        ChartView{
            id: chartminus15v
            theme: ChartView.ChartThemeDark
            anchors.fill: parent
            visible: minus15vradiobutton.checked

            ValueAxis{
                id: minus15vyaxis
                min: 4
                max: 6
                titleText: "Voltage (V)"
            }


            ValueAxis{
                id: minus15vxaxis
                min: 0
                max: 60
                titleText: "Time (s)"
            }

            LineSeries{
                id: minus15vserie
                name: "-15V"
                axisX: minus15vxaxis
                axisY: minus15vyaxis

            }
        }

        ChartView{
            id: chartv15
            theme: ChartView.ChartThemeDark
            anchors.fill: parent
            visible: v15radiobutton.checked

            ValueAxis{
                id: v15yaxis
                min: 14
                max: 16
                titleText: "Voltage (V)"
            }


            ValueAxis{
                id: v15xaxis
                min: 0
                max: 60
                titleText: "Time (s)"
            }

            LineSeries{
                id: v15serie
                name: "15V"
                axisX: v15xaxis
                axisY: v15yaxis

            }
        }

        ChartView{
            id: chartv5
            theme: ChartView.ChartThemeDark
            anchors.fill: parent
            visible: v5radiobutton.checked

            ValueAxis{
                id: v5yaxis
                min: 4
                max: 6
                titleText: "Voltage (V)"
            }


            ValueAxis{
                id: v5xaxis
                min: 0
                max: 60
                titleText: "Time (s)"
            }

            LineSeries{
                id: v5serie
                name: "5V"
                axisX: v5xaxis
                axisY: v5yaxis

            }
        }

        ChartView {
            id: charttemp
            theme: ChartView.ChartThemeDark
            visible: tempradiobutton.checked
            anchors.fill: parent

            ValueAxis {
                id: tempyaxis
                min: 22
                max: 26
                titleText: "Temp. (C)"
            }

            ValueAxis {
                id: tempxaxis
                min: 0
                max: 60
                titleText: "Time (s)"
            }

            LineSeries {
                id: tempserie
                name: "Temperature"
                axisX: tempxaxis
                axisY: tempyaxis
            }
        }
    }

    Connections {
        target: myseries

       function onSignalshowdialogerror(textmessage) {
            dialogerror.title = textmessage
            dialogerror.visible = true
        }

        function onMysignalfirstaxis(lfirstaxis) {
            console.log("firstaxis: " + lfirstaxis)
            tempyaxis.min = lfirstaxis[0] - 0.5
            tempyaxis.max = lfirstaxis[0] + 0.5
            minus15vyaxis.min = lfirstaxis[2] - 0.1
            minus15vyaxis.max = lfirstaxis[2] + 0.1
            psyaxis.min = lfirstaxis[1] + 0.02
            psyaxis.max = lfirstaxis[1] - 0.02
            v15yaxis.min = lfirstaxis[3] - 0.1
            v15yaxis.max = lfirstaxis[3] + 0.1
         }


        function onSignallimits(starttimes, finishtimes) {
            console.log('starttimes when receiving from python: ' + starttimes)
            ma.starttimes = starttimes
            ma.finishtimes = finishtimes
            for (var i = 0; i < starttimes.length; i++){
                var starlimit = chartchs.createSeries(ChartView.SeriesTypeLine, 'start' + i, xaxis, yaxis)
                starlimit.color = 'lightgreen'
                starlimit.style = Qt.DashLine
                starlimit.append (starttimes[i], xaxis.min)
                starlimit.append (starttimes[i], yaxis.max)
            }

            for (var j = 0; j < finishtimes.length; j++){
                var finishlimit = chartchs.createSeries(ChartView.SeriesTypeLine, 'finish' + j, xaxis, yaxis)
                finishlimit.color = 'lightsalmon'
                finishlimit.style = Qt.DashLine
                finishlimit.append (finishtimes[j], xaxis.min)
                finishlimit.append (finishtimes[j], yaxis.max)
            }
        }

        function onSignalfullintegrals(fullintegrals) {
            fullintegralsnow = fullintegrals
            console.log('fullintegrals: ' + fullintegralsnow)
            autodetect.enabled = true
            calcshotsbutton.enabled = true
            deletelimits.enabled = true
            yaxis.titleText = pulsescheck.checked ? "<p>cumulative charge every 750 &mu;s (nC)</p>" : "cumulative charge every 300 ms (nC)"
            yaxis.max = pulsescheck.checked ? maxypulses : maxynopulses
            for (var k = 0; k < numberofchannels; k++){
                myseries.updateserieanalyze(chartchs.series('ch' + k), 'ch' + k + 'c', pulsescheck.checked)
            }
            myseries.updateserieanalyze(chartchs.series('chargedose'), 'chargedose0', pulsescheck.checked)
            if (pulsescheck.checked) {
                myseries.updateserie(chartchs.series('pulse'), 'pulsetoplot', pulsescheck.checked)
            }


            if (settingsview.cartridgeincomboboxindex == 0) {
                allshotspulsestext.text = fullintegralsnow[5]
                ch2box.title = '--'
                ch3box.title = '--'
                ch4box.title = '--'
                ch5box.title = '--'
                ch6box.title = '--'
                ch7box.title = '--'
                ch2units.text = '--'
                ch3units.text = '--'
                ch4units.text = '--'
                ch5units.text = '--'
                ch6units.text = '--'
                ch7units.text = '--'
                allshotsch2text.text = '--'
                allshotsch3text.text = '--'
                allshotsch4text.text = '--'
                allshotsch5text.text = '--'
                allshotsch6text.text = '--'
                allshotsch7text.text = '--'
                if (charge.checked) {
                    allshotsch0text.text = fullintegralsnow[0]
                    ch0box.title = 'ch0'
                    allshotsch1text.text = fullintegralsnow[1]
                    ch1box.title = 'ch1'
                    ch0units.text = 'nC'
                    ch1units.text = 'nC'
                }
                if (chargepropdose.checked) {
                    ch0box.title = 'SENSOR 0'
                    ch1box.title = '--'
                    allshotsch0text.text = fullintegralsnow[2]
                    allshotsch1text.text = '--'
                    ch0units.text = 'nC'
                    ch1units.text = '--'
                }
                if (dose.checked & centigrays.checked) {
                    ch0box.title = 'SENSOR 0'
                    allshotsch1text.text = '--'
                    ch1box.title = '--'
                    ch1units.text = '--'
                    allshotsch0text.text = fullintegralsnow[3]
                    ch0units.text = 'cGy'
                    ch1units.text = '--'
                }
                if (dose.checked & grays.checked) {
                    ch0box.title = 'SENSOR 0'
                    allshotsch1text.text = '--'
                    ch1box.title = '--'
                    ch1units.text = '--'
                    allshotsch0text.text = fullintegralsnow[4]
                    ch0units.text = 'Gy'
                }
            }
            if (settingsview.cartridgeincomboboxindex == 1) {
                allshotspulsestext.text = fullintegralsnow[20]
                if (charge.checked) {
                    allshotsch0text.text = fullintegralsnow[0]
                    ch0box.title = 'ch0'
                    allshotsch1text.text = fullintegralsnow[1]
                    ch1box.title = 'ch1'
                    allshotsch2text.text = fullintegralsnow[2]
                    ch2box.title = 'ch2'
                    allshotsch3text.text = fullintegralsnow[3]
                    ch3box.title = 'ch3'
                    allshotsch4text.text = fullintegralsnow[4]
                    ch4box.title = 'ch4'
                    allshotsch5text.text = fullintegralsnow[5]
                    ch5box.title = 'ch5'
                    allshotsch6text.text = fullintegralsnow[6]
                    ch6box.title = 'ch6'
                    allshotsch7text.text = fullintegralsnow[7]
                    ch7box.title = 'ch7'
                    ch0units.text = 'nC'
                    ch1units.text = 'nC'
                    ch2units.text = 'nC'
                    ch3units.text = 'nC'
                    ch4units.text = 'nC'
                    ch5units.text = 'nC'
                    ch6units.text = 'nC'
                    ch7units.text = 'nC'

                }
                if (chargepropdose.checked) {
                    ch0box.title = 'SENSOR 0'
                    ch1box.title = '--'
                    ch2box.title = 'SENSOR 1'
                    ch3box.title = '--'
                    ch4box.title = 'SENSOR 2'
                    ch5box.title = '--'
                    ch6box.title = 'SENSOR 3'
                    ch7box.title = '--'
                    allshotsch0text.text = fullintegralsnow[8]
                    ch0units.text = 'nC'
                    allshotsch2text.text = fullintegralsnow[9]
                    ch2units.text = 'nC'
                    allshotsch4text.text = fullintegralsnow[10]
                    ch4units.text = 'nC'
                    allshotsch6text.text = fullintegralsnow[11]
                    ch6units.text = 'nC'
                    allshotsch1text.text = '--'
                    ch1units.text = '--'
                    allshotsch3text.text = '--'
                    ch3units.text = '--'
                    allshotsch5text.text = '--' 
                    ch5units.text = '--'
                    allshotsch7text.text = '--'
                    ch7units.text = '--'
                }
                if (dose.checked & centigrays.checked) {
                    ch0box.title = 'SENSOR 0'
                    ch1box.title = '--'
                    ch2box.title = 'SENSOR 1'
                    ch3box.title = '--'
                    ch4box.title = 'SENSOR 2'
                    ch5box.title = '--'
                    ch6box.title = 'SENSOR 3'
                    ch7box.title = '--'
                    allshotsch0text.text = fullintegralsnow[12]
                    ch0units.text = 'cGy'
                    allshotsch2text.text = fullintegralsnow[13]
                    ch2units.text = 'cGy'
                    allshotsch4text.text = fullintegralsnow[14]
                    ch4units.text = 'cGy'
                    allshotsch6text.text = fullintegralsnow[15]
                    ch6units.text = 'cGy'
                    allshotsch1text.text = '--'
                    ch1units.text = '--'
                    allshotsch3text.text = '--'
                    ch3units.text = '--'
                    allshotsch5text.text = '--' 
                    ch5units.text = '--'
                    allshotsch7text.text = '--'
                    ch7units.text = '--'
                }
                if (dose.checked & grays.checked) {
                    ch0box.title = 'SENSOR 0'
                    ch1box.title = '--'
                    ch2box.title = 'SENSOR 1'
                    ch3box.title = '--'
                    ch4box.title = 'SENSOR 2'
                    ch5box.title = '--'
                    ch6box.title = 'SENSOR 3'
                    ch7box.title = '--'
                    allshotsch0text.text = fullintegralsnow[16]
                    ch0units.text = 'Gy'
                    allshotsch2text.text = fullintegralsnow[17]
                    ch2units.text = 'Gy'
                    allshotsch4text.text = fullintegralsnow[18]
                    ch4units.text = 'Gy'
                    allshotsch6text.text = fullintegralsnow[19]
                    ch6units.text = 'Gy'
                    allshotsch1text.text = '--'
                    ch1units.text = '--'
                    allshotsch3text.text = '--'
                    ch3units.text = '--'
                    allshotsch5text.text = '--' 
                    ch5units.text = '--'
                    allshotsch7text.text = '--'
                    ch7units.text = '--'
                }

            }

            if (settingsview.cartridgeincomboboxindex == 2) {
                console.log('catridgein now is ' + settingsview.cartridgeincomboboxindex) 
                allshotspulsestext.text = fullintegralsnow[29]
                if (charge.checked) {
                    allshotsch0text.text = fullintegralsnow[0]
                    ch0box.title = 'ch0'
                    allshotsch1text.text = fullintegralsnow[1]
                    ch1box.title = 'ch1'
                    allshotsch2text.text = fullintegralsnow[2]
                    ch2box.title = 'ch2'
                    allshotsch3text.text = fullintegralsnow[3]
                    ch3box.title = 'ch3'
                    allshotsch4text.text = fullintegralsnow[4]
                    ch4box.title = 'ch4'
                    allshotsch5text.text = fullintegralsnow[5]
                    ch5box.title = 'ch5'
                    allshotsch6text.text = fullintegralsnow[6]
                    ch6box.title = 'ch6'
                    allshotsch7text.text = fullintegralsnow[7]
                    ch7box.title = 'ch7'
                    ch0units.text = 'nC'
                    ch1units.text = 'nC'
                    ch2units.text = 'nC'
                    ch3units.text = 'nC'
                    ch4units.text = 'nC'
                    ch5units.text = 'nC'
                    ch6units.text = 'nC'
                    ch7units.text = 'nC'

                }
                if (chargepropdose.checked) {
                    ch0box.title = 'SENSOR 0'
                    allshotsch1text.text = '--'
                    ch1box.title = '--'
                    ch1units.text = '--'
                    ch2box.title = 'SENSOR 1'
                    ch3box.title = 'SENSOR 2'
                    ch4box.title = 'SENSOR 3'
                    ch5box.title = 'SENSOR 4'
                    ch6box.title = 'SENSOR 5'
                    ch7box.title = 'SENSOR 6'
                    allshotsch0text.text = fullintegralsnow[8]
                    ch0units.text = 'nC'
                    allshotsch2text.text = fullintegralsnow[9]
                    ch2units.text = 'nC'
                    allshotsch3text.text = fullintegralsnow[10]
                    ch3units.text = 'nC'
                    allshotsch4text.text = fullintegralsnow[11]
                    ch4units.text = 'nC'
                    allshotsch5text.text = fullintegralsnow[12]
                    ch5units.text = 'nC'
                    allshotsch6text.text = fullintegralsnow[13]
                    ch6units.text = 'nC'
                    allshotsch7text.text = fullintegralsnow[14]
                    ch7units.text = 'nC'
                }
                if (dose.checked & centigrays.checked) {
                    ch0box.title = 'SENSOR 0'
                    allshotsch1text.text = '--'
                    ch1box.title = '--'
                    ch1units.text = '--'
                    ch2box.title = 'SENSOR 1'
                    ch3box.title = 'SENSOR 2'
                    ch4box.title = 'SENSOR 3'
                    ch5box.title = 'SENSOR 4'
                    ch6box.title = 'SENSOR 5'
                    ch7box.title = 'SENSOR 6'
                    allshotsch0text.text = fullintegralsnow[15]
                    ch0units.text = 'cGy'
                    allshotsch2text.text = fullintegralsnow[16]
                    ch2units.text = 'cGy'
                    allshotsch3text.text = fullintegralsnow[17]
                    ch3units.text = 'cGy'
                    allshotsch4text.text = fullintegralsnow[18]
                    ch4units.text = 'cGy'
                    allshotsch5text.text = fullintegralsnow[19]
                    ch5units.text = 'cGy'
                    allshotsch6text.text = fullintegralsnow[20]
                    ch6units.text = 'cGy'
                    allshotsch7text.text = fullintegralsnow[21]
                    ch7units.text = 'cGy'
                }
                if (dose.checked & grays.checked) {
                    ch0box.title = 'SENSOR 0'
                    allshotsch1text.text = '--'
                    ch1box.title = '--'
                    ch1units.text = '--'
                    ch2box.title = 'SENSOR 1'
                    ch3box.title = 'SENSOR 2'
                    ch4box.title = 'SENSOR 3'
                    ch5box.title = 'SENSOR 4'
                    ch6box.title = 'SENSOR 5'
                    ch7box.title = 'SENSOR 6'
                    allshotsch0text.text = fullintegralsnow[22]
                    ch0units.text = 'Gy'
                    allshotsch2text.text = fullintegralsnow[23]
                    ch2units.text = 'Gy'
                    allshotsch3text.text = fullintegralsnow[24]
                    ch3units.text = 'Gy'
                    allshotsch4text.text = fullintegralsnow[25]
                    ch4units.text = 'Gy'
                    allshotsch5text.text = fullintegralsnow[26]
                    ch5units.text = 'Gy'
                    allshotsch6text.text = fullintegralsnow[27]
                    ch6units.text = 'Gy'
                    allshotsch7text.text = fullintegralsnow[28]
                    ch7units.text = 'Gy'
                }
            }
        }

        function onSignalpartialintegrals(starttimes, finishtimes, partialintegrals) {
            console.log('partial integrals: ' + partialintegrals)
            //console.log('partial integrals second value: ' + partialintegrals[1][1])
            ma.sortedstarttimes = starttimes
            ma.sortedfinishtimes = finishtimes
            ma.partialintegralscalculated = true
            ma.partialintegrals = partialintegrals
            if (pulsescheck.checked) {
                myseries.updateserie(chartchs.series('pulse'), 'pulsetoplot', pulsescheck.checked)
            }
        }

        function onSignalreadytoplot(limits) {
            dataanalyzed = true
            xaxis.min = 0
            xaxis.max = limits[0]
            psxaxis.min = 0
            psxaxis.max = limits[0]
            tempxaxis.min = 0
            tempxaxis.max = limits[0]
            minus15vxaxis.max = limits[0]
            v15xaxis.max = limits[0]
            yaxis.max = limits[2]
            maxynopulses = limits[2]
            maxypulses = limits[1]
            yaxis.min = 0
            tempyaxis.min = limits[3]-0.1
            tempyaxis.max = limits[4]+0.1
            psyaxis.min = limits[5]-0.01
            psyaxis.max = limits[6]+0.01
            minus15vyaxis.min = limits[7]-0.01
            minus15vyaxis.max = limits[8]+0.01
            v15yaxis.min = limits[9]-0.01
            v15yaxis.max = limits[10]+0.01
            v5yaxis.min = limits[11]-0.01
            v5yaxis.max = limits[12]+0.01
            myseries.updateserieanalyze(psserie, 'PS0', pulsescheck.checked)
            myseries.updateserieanalyze(tempserie, 'temp', pulsescheck.checked)
            myseries.updateserieanalyze(minus15vserie, '-15V', pulsescheck.checked)
            myseries.updateserieanalyze(v15serie, '15V', pulsescheck.checked)
            myseries.updateserieanalyze(v5serie, '5V', pulsescheck.checked)
        }

        function onMysignalpulses(tnowpulses, meantemp, meanPS0, meanminus15V, mean15V, mean5V) {
            xaxis.max = tnowpulses
            xaxis.min = tnowpulses - 0.3
            psxaxis.min = tnowpulses - 0.3
            psxaxis.max = tnowpulses
            minus15vxaxis.min = tnowpulses - 0.3
            minus15vxaxis.max = tnowpulses
            v15xaxis.min = tnowpulses - 0.3
            v15xaxis.max = tnowpulses
            v5xaxis.min = tnowpulses - 0.3
            v5xaxis.max = tnowpulses
            tempxaxis.max = tnowpulses
            tempxaxis.min = tnowpulses - 0.3
            tempyaxis.max = meantemp + 0.5
            tempyaxis.min = meantemp - 0.5
            yaxis.max = 12
            yaxis.min = -12
            psyaxis.min = meanPS0 - 0.02
            psyaxis.max = meanPS0 + 0.02
            minus15vyaxis.min = meanminus15V - 0.1
            minus15vyaxis.max = meanminus15V + 0.1
            v15yaxis.min = mean15V - 0.1
            v15yaxis.max = mean15V + 0.1
            v5yaxis.min = mean5V - 0.1
            v5yaxis.max = mean5V + 0.1
            myseries.updateseriepulsesrealtime(tempserie, 'temp')
            myseries.updateseriepulsesrealtime(psserie, 'PS0')
            myseries.updateseriepulsesrealtime(minus15vserie, '-15V')
            myseries.updateseriepulsesrealtime(v15serie, '15V')
            myseries.updateseriepulsesrealtime(v5serie, '5V')
            //model10 2, model9 8
            for (var i = 0; i < numberofchannels; i++){
                myseries.updateseriepulsesrealtime(chartchs.series('ch' + i), 'ch' + i)
            }
        }

        function onMysignal(measnow) {
            //console.log(measnow)
            if (measnow[0] > 60){
                xaxis.max = measnow[0]
                psxaxis.max = measnow[0]
                tempxaxis.max = measnow[0]
                minus15vxaxis.max = measnow[0]
                v15xaxis.max = measnow[0]
                v5xaxis.max = measnow[0]
            }

            if (measnow[1] > yaxis.max) {yaxis.max = measnow[1] + 0.1}
            if (measnow[1] < yaxis.min) {yaxis.min = measnow[1] - 0.1}
            if (measnow[2] > tempyaxis.max) {
                tempyaxis.max = measnow[2] + 0.5
                tempyaxis.min = tempyaxis.max - 1
            }
            if (measnow[2] < tempyaxis.min) {
                tempyaxis.min = measnow[2] - 0.5
                tempyaxis.max = tempyaxis.min + 1
            }
            if (measnow[4] > minus15vyaxis.max) {
                minus15vyaxis.max = measnow[4] + 1
                minus15vyaxis.min = minus15vyaxis.max - 1
            }
            if (measnow[4] < minus15vyaxis.min) {
                minus15vyaxis.min = measnow[1] - 1
                minus15vyaxis.max = minus15vyaxis.min + 1
            }
            if (measnow[3] > psyaxis.max) {
                psyaxis.max = measnow[3] + 0.01
                psyaxis.min = psyaxis.max - 0.04
            }
            if (measnow[3] < psyaxis.min) {
                psyaxis.min = measnow[3] - 0.01
                psyaxis.max = psyaxis.min + 0.04
            }
            if (measnow[5] > v15yaxis.max) {
                v15yaxis.max = measnow[5] + 0.01
                v15yaxis.min = v15yaxis.max - 0.04
            }
            if (measnow[5] < v15yaxis.min) {
                v15yaxis.min = measnow[5] - 0.01
                v15yaxis.max = v15yaxis.min + 0.04
            }

            myseries.updateserierealtime(tempserie, 'temp')
            myseries.updateserierealtime(minus15vserie, '-15V')
            myseries.updateserierealtime(psserie, 'PS0')
            myseries.updateserierealtime(v15serie, '15V')
            myseries.updateserierealtime(v5serie, '5V')
            for (var i = 0; i < numberofchannels; i++){
                myseries.updateserierealtime(chartchs.series('ch' + i), 'ch' + i)
            }
            myseries.updateserierealtime(chartchs.series('chargedose'), 'chargedose0')
        }
    }
}
