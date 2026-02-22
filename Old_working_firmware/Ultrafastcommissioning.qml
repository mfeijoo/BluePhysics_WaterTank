import QtQuick 2.0
import QtQuick.Controls 2.3
import QtQuick.Layouts 1.3
import QtCharts 2.2
import QtQuick.Controls.Material 2.0
import QtQuick.Dialogs 1.0

Item {
    id: ultrafastcommissioning
    visible: false
    anchors.fill: parent
    property string fileselected: 'none'
    property var colors: [Material.color(Material.LightBlue), Material.color(Material.LightGreen)]
    property real maxypulses: 1
    property real maxynopulses: 1
    property var fullintegralsnow: []
    property bool pddcalculated: false
    property var pddlimitsglobal: []


    //Settingsview{id: settingsview}

    ToolBar {
        id: analyzetoolbar
        anchors.top: parent.top
        width: parent.width
        height: 50

        RowLayout {
            anchors.fill: parent
            ToolButton{
                icon.source: "icons/menu.png"
                onClicked: {
                    navigationdrawer.open()
                    analyzeview.fileselected = 'none'
                }
            }

            Label {
                text: "ULTRA-FAST COMMISSIONING"
                font.pixelSize: 20
                font.bold: true
            }

            ToolButton {

                id: loadbutton
                icon.source: "icons/file-download-outline.png"
                objectName: "loadbutton"
                onClicked: {
                    chartchs.removeAllSeries()
                    chartchs.createSeries(ChartView.SeriesTypeLine, 'cerenkov', xaxis, yaxis)
                    chartchs.series('cerenkov').useOpenGL = true
                    chartchs.series('cerenkov').color = colors[1]
                    //chartchs.series('cerenkov').style = Qt.DashLine
                    chartchs.createSeries(ChartView.SeriesTypeLine, 'sensor', xaxis, yaxis)
                    chartchs.series('sensor').color = colors[0]
                    chartchs.series('sensor').useOpenGL = true
                    chartchs.series('sensor').z = -1
                    //chartchs.series('sensor').style = Qt.DashLine
                    chartchs.createSeries(ChartView.SeriesTypeScatter, 'pulse', xaxis, yaxis)
                    chartchs.series('pulse').color = Material.color(Material.DeepOrange)
                    chartchs.series('pulse').useOpenGL = true
                    chartchs.series('pulse').markerSize = 5
                    chartchs.series('pulse').markerShape = ScatterSeries.MarkerShapeCircle
                    chartchs.series('pulse').z = 2
                    allshotssensortext.text = '--'
                    allshotscerenkovtext.text = '--'
                    allshotssensorunits.text = '--'
                    allshotscerenkovtext.text = '--'
                    allshotscerenkovunits.text = '--'
                    allshotsnumberofpulsestext.text = '--'
                    singleshotsensortext.text = '--'
                    singleshotsensorunits.text = '--'
                    singleshotcerenkovtext.text = '--'
                    singleshotcerenkovunits.text = '--'
                    singleshotnumberofpulsestext.text = '--'
                    ma.partialintegralscalculated = false
                    pulsescheck.checked = false
                    pulsescheck.enabled = false
                    calcpddbutton.enabled = false
                    deletelimits.enabled = false
                    ma.starttimes = []
                    ma.finishtimes = []
                    pddcalculated = false
                    yaxis.titleText = "<p>cumulative charge every 300 ms (nC)</p>"
                    xaxis.titleText = "time (s)"
                    fileDialog.open()
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

                }
            }

            CheckBox {
                id: pulsescheck
                text: 'Pulses'
                enabled: false
                onClicked: {
                    if (pddcalculated){
                        yaxis.min = pulsescheck.checked ? pddlimitsglobal[2] : pddlimitsglobal[3]
                        yaxis.max = pulsescheck.checked ? pddlimitsglobal[4] : 100
                        yaxis.titleText = pulsescheck.checked ? 'Charge prop. dose (nC)' : 'PDD %'
                        myultrafast.updatepdd(chartchs.series('pdd'), checked)
                    }
                }
            }

            Row{
                Text{
                    text: 'PDD depth (mm): '
                    color: 'lightgrey'
                }
                TextEdit{
                    id: pdddepth
                    text: '140'
                    color: 'white'
                }
            }

            Row{
                Text{
                    text: 'PDD dmax (mm): '
                    color: 'lightgrey'
                }
                TextEdit{
                    id: pdddmax
                    text: '16'
                    color: 'white'
                }
            }

            ToolButton {
                id: calcpddbutton
                text: 'Calc. PDD'
                enabled: false
                onClicked: {
                    console.log('start times: ' + ma.starttimes)
                    console.log('finishtimes: ' + ma.finishtimes)
                    myultrafast.calcpdd(ma.starttimes, ma.finishtimes, pdddepth.text, pdddmax.text)
                }
            }




            ToolButton {
                icon.source: "icons/settings.png"
                onClicked: {
                    settingsdrawer.open()
                }
            }
       }
    }

    FileDialog {
        id: fileDialog
        folder: shortcuts.desktop
        nameFilters: ['Data files (*.csv)']
        onAccepted: {
           myultrafast.openfile(fileUrl)
           fileselected = fileUrl
        }
    }

    Dialog {
        id: dialogerror
        visible: false
        width: 300
        height: 150
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        standardButtons: Dialog.Ok
        title: 'Chose a different Cut Off'
        onAccepted: {visible = false}
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
                    text: 'sensor'
                    checked: true

                    onClicked: {
                        chartchs.series('sensor').visible = checked
                    }
                }
                CheckBox {
                    text: 'cerenkov'
                    checked: true

                    onClicked: {
                        chartchs.series('cerenkov').visible = checked
                    }
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
                        if (fileselected != 'none') {
                            if (charge.checked) {
                                allshotssensortext.text = fullintegralsnow[0]
                                allshotscerenkovtext.text = fullintegralsnow[1]
                                allshotssensorunits.text = 'nC'
                                allshotscerenkovunits.text = 'nC'
                            }
                            if (chargepropdose.checked) {
                                allshotssensortext.text = fullintegralsnow[2]
                                allshotssensorunits.text = 'nC'
                                allshotscerenkovtext.text = '--'
                                allshotscerenkovunits.text = '--'
                            }
                            if (dose.checked) {
                                if (grays.checked) {
                                    allshotssensortext.text = fullintegralsnow[4]
                                    allshotssensorunits.text = 'Gy'
                                }
                                else {
                                    allshotssensortext.text = fullintegralsnow[3]
                                    allshotssensorunits.text = 'cGy'
                                    }
                                allshotscerenkovtext.text = '--'
                                allshotscerenkovunits.text = '--'
                            }
                        }
                    }
                }

                RadioButton {
                    id: chargepropdose
                    text: '~chdose'
                    autoExclusive: true
                    onClicked: {
                        if (fileselected != 'none') {
                            if (charge.checked) {
                                allshotssensortext.text = fullintegralsnow[0]
                                allshotscerenkovtext.text = fullintegralsnow[1]
                                allshotssensorunits.text = 'nC'
                                allshotscerenkovunits.text = 'nC'
                            }
                            if (chargepropdose.checked) {
                                allshotssensortext.text = fullintegralsnow[2]
                                allshotssensorunits.text = 'nC'
                                allshotscerenkovtext.text = '--'
                                allshotscerenkovunits.text = '--'
                            }
                            if (dose.checked) {
                                if (grays.checked) {
                                    allshotssensortext.text = fullintegralsnow[4]
                                    allshotssensorunits.text = 'Gy'
                                }
                                else {
                                    allshotssensortext.text = fullintegralsnow[3]
                                    allshotssensorunits.text = 'cGy'
                                    }
                                allshotscerenkovtext.text = '--'
                                allshotscerenkovunits.text = '--'
                            }
                        }
                    }
                }

                RadioButton {
                    id: dose
                    text: 'dose'
                    autoExclusive: true
                    onClicked: {
                        if (fileselected != 'none') {
                            if (charge.checked) {
                                allshotssensortext.text = fullintegralsnow[0]
                                allshotscerenkovtext.text = fullintegralsnow[1]
                                allshotssensorunits.text = 'nC'
                                allshotscerenkovunits.text = 'nC'
                            }
                            if (chargepropdose.checked) {
                                allshotssensortext.text = fullintegralsnow[2]
                                allshotssensorunits.text = 'nC'
                                allshotscerenkovtext.text = '--'
                                allshotscerenkovunits.text = '--'
                            }
                            if (dose.checked) {
                                if (grays.checked) {
                                    allshotssensortext.text = fullintegralsnow[4]
                                    allshotssensorunits.text = 'Gy'
                                }
                                else {
                                    allshotssensortext.text = fullintegralsnow[3]
                                    allshotssensorunits.text = 'cGy'
                                    }
                                allshotscerenkovtext.text = '--'
                                allshotscerenkovunits.text = '--'
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
                    onClicked: {
                        if (fileselected != 'none') {
                            if (charge.checked) {
                                allshotssensortext.text = fullintegralsnow[0]
                                allshotscerenkovtext.text = fullintegralsnow[1]
                                allshotssensorunits.text = 'nC'
                                allshotscerenkovunits.text = 'nC'
                            }
                            if (chargepropdose.checked) {
                                allshotssensortext.text = fullintegralsnow[2]
                                allshotssensorunits.text = 'nC'
                                allshotscerenkovtext.text = '--'
                                allshotscerenkovunits.text = '--'
                            }
                            if (dose.checked) {
                                if (grays.checked) {
                                    allshotssensortext.text = fullintegralsnow[4]
                                    allshotssensorunits.text = 'Gy'
                                }
                                else {
                                    allshotssensortext.text = fullintegralsnow[3]
                                    allshotssensorunits.text = 'cGy'
                                    }
                                allshotscerenkovtext.text = '--'
                                allshotscerenkovunits.text = '--'
                            }
                        }
                    }
                }
                RadioButton {
                    id: centigrays
                    text: 'cGy'
                    autoExclusive: true
                    checked: true
                    onClicked: {
                        if (fileselected != 'none') {
                            if (charge.checked) {
                                allshotssensortext.text = fullintegralsnow[0]
                                allshotscerenkovtext.text = fullintegralsnow[1]
                                allshotssensorunits.text = 'nC'
                                allshotscerenkovunits.text = 'nC'
                            }
                            if (chargepropdose.checked) {
                                allshotssensortext.text = fullintegralsnow[2]
                                allshotssensorunits.text = 'nC'
                                allshotscerenkovtext.text = '--'
                                allshotscerenkovunits.text = '--'
                            }
                            if (dose.checked) {
                                if (grays.checked) {
                                    allshotssensortext.text = fullintegralsnow[4]
                                    allshotssensorunits.text = 'Gy'
                                }
                                else {
                                    allshotssensortext.text = fullintegralsnow[3]
                                    allshotssensorunits.text = 'cGy'
                                    }
                                allshotscerenkovtext.text = '--'
                                allshotscerenkovunits.text = '--'
                            }
                        }
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
                    id: v5radiobutton
                    text: "5V"
                    autoExclusive: true
                }
                RadioButton {
                    id: minus15vradiobutton
                    text: "-15V"
                    autoExclusive: true
                }

             }
        }
    }

    Item {
        id: resultsholder
        anchors.top: analyzetoolbar.bottom
        anchors.right: parent.right
        width: 250
        anchors.bottom: parent.bottom

            GroupBox {
                id: coordbox
                anchors.top: parent.top
                anchors.topMargin: 10
                anchors.right: parent.right
                anchors.rightMargin: 5
                anchors.left: parent.left
                anchors.leftMargin: 5
                height: 100
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
            GroupBox {

                id: allshotsbox
                title: 'ALL SHOTS RESULTS'
                anchors.top: coordbox.bottom
                anchors.topMargin: 20
                anchors.left: parent.left
                anchors.leftMargin: 5
                anchors.right: parent.right
                anchors.rightMargin: 5
                height: 400
                GroupBox {
                    id: allshotssensorbox
                    title: 'SENSOR'
                    anchors.top: parent.top
                    anchors.topMargin: 10
                    anchors.left: parent.left
                    anchors.leftMargin: 5
                    anchors.right: parent.right
                    anchors.rightMargin: 5
                    height: 100


                    Text {
                        id: allshotssensortext
                        anchors.right: allshotssensorunits.left
                        anchors.rightMargin: 5
                        color: colors[0]
                        font.pixelSize: 40
                        font.bold: true
                        text: '--'
                    }

                    Text {
                        id: allshotssensorunits
                        anchors.right: parent.right
                        anchors.bottom: allshotssensortext.bottom
                        anchors.bottomMargin: 5
                        color: colors[0]
                        font.pixelSize: 20
                        font.bold: true
                        text: '--'
                    }



                }
                GroupBox {
                    title: 'CERENKOV'
                    id: allshotscerenkovbox
                    anchors.top: allshotssensorbox.bottom
                    anchors.topMargin: 10
                    anchors.left: parent.left
                    anchors.leftMargin: 5
                    anchors.right: parent.right
                    anchors.rightMargin: 5
                    height: 100
                    Text {
                        id: allshotscerenkovtext
                        anchors.right: allshotscerenkovunits.left
                        anchors.rightMargin: 10
                        color: colors[1]
                        font.pixelSize: 40
                        font.bold: true
                        text: '--'
                    }

                    Text {
                        id: allshotscerenkovunits
                        anchors.right: parent.right
                        anchors.bottom: allshotscerenkovtext.bottom
                        anchors.bottomMargin: 5
                        color: colors[1]
                        font.pixelSize: 20
                        font.bold: true
                        text: '--'
                    }
                }
                GroupBox {
                    title: 'NUMBER OF PULSES'
                    anchors.top: allshotscerenkovbox.bottom
                    anchors.topMargin: 10
                    anchors.left: parent.left
                    anchors.leftMargin: 5
                    anchors.right: parent.right
                    anchors.rightMargin: 5
                    height: 100
                    Text {
                        id: allshotsnumberofpulsestext
                        anchors.right: parent.right
                        anchors.rightMargin: 20
                        color: Material.color(Material.DeepOrange)
                        font.pixelSize: 40
                        font.bold: true
                    }
                }
            }

            GroupBox {
                title: 'SINGLE SHOT RESULTS'
                anchors.top: allshotsbox.bottom
                anchors.topMargin: 20
                anchors.left: parent.left
                anchors.leftMargin: 5
                anchors.right: parent.right
                anchors.rightMargin: 5
                height: 400
                GroupBox {
                    id: singleshotsensorbox
                    title: 'SENSOR'
                    anchors.top: parent.top
                    anchors.topMargin: 10
                    anchors.left: parent.left
                    anchors.leftMargin: 5
                    anchors.right: parent.right
                    anchors.rightMargin: 5
                    height: 100
                    Text {
                        id: singleshotsensortext
                        anchors.right: singleshotsensorunits.left
                        anchors.rightMargin: 10
                        color: colors[0]
                        font.pixelSize: 40
                        font.bold: true
                        text: '--'
                    }

                    Text {
                        id: singleshotsensorunits
                        anchors.right: parent.right
                        anchors.bottom: singleshotsensortext.bottom
                        anchors.bottomMargin: 5
                        color: colors[0]
                        font.pixelSize: 20
                        font.bold: true
                        text: '--'
                    }
                }
                GroupBox {
                    id: singleshotcerenkovbox
                    title: 'CERENKOV'
                    anchors.top: singleshotsensorbox.bottom
                    anchors.topMargin: 10
                    anchors.left: parent.left
                    anchors.leftMargin: 5
                    anchors.right: parent.right
                    anchors.rightMargin: 5
                    height: 100
                    Text {
                        id: singleshotcerenkovtext
                        anchors.right: singleshotcerenkovunits.left
                        anchors.rightMargin: 10
                        color: colors[1]
                        font.pixelSize: 40
                        font.bold: true
                        text: '--'
                    }

                    Text {
                        id: singleshotcerenkovunits
                        anchors.right: parent.right
                        anchors.bottom: singleshotcerenkovtext.bottom
                        anchors.bottomMargin: 5
                        color: colors[1]
                        font.pixelSize: 20
                        font.bold: true
                        text: '--'
                    }
                }
                GroupBox {
                    id: singleshotnumberofpulses
                    title: 'NUMBER OF PULSES'
                    anchors.top: singleshotcerenkovbox.bottom
                    anchors.topMargin: 10
                    anchors.left: parent.left
                    anchors.leftMargin: 5
                    anchors.right: parent.right
                    anchors.rightMargin: 5
                    height: 100
                    Text {
                        id: singleshotnumberofpulsestext
                        anchors.right: parent.right
                        anchors.rightMargin: 20
                        color: Material.color(Material.DeepOrange)
                        font.pixelSize: 40
                        font.bold: true
                    }
                }

            }
    }


    ChartView {
        id: chartchs
        theme: ChartView.ChartThemeDark
        anchors.left: parent.left
        anchors.right: resultsholder.left
        anchors.top: analyzetoolbar.bottom
        anchors.bottom: chartpowersholder.top
        legend.visible: false


        ValueAxis {
            id: yaxis
            min: 0
            max: 1
            titleText: "<p>cumulative charge every 300 ms (nC)</p>"
        }

        ValueAxis {
            id: xaxis
            min: 0
            max: 60
            titleText: "time (s)"
        }

        ScatterSeries {
            id: pulseseries
            name: 'pulse'
            color: Material.color(Material.DeepOrange)
            useOpenGL: true
            axisX: xaxis
            axisY: yaxis
        }

        LineSeries {
            id: cerenkovseries
            name: 'cerenkov'
            useOpenGL: true
            color: Material.color(Material.DeepPurple)
            axisX: xaxis
            axisY: yaxis
        }

        LineSeries {
            id: sensorseries
            name: 'sensor'
            useOpenGL: true
            color: Material.color(Material.LightBlue)
            axisX: xaxis
            axisY: yaxis
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

            onPositionChanged: {
                var p = Qt.point(mouseX, mouseY)
                var cp = chartchs.mapToValue(p, chartchs.series('sensor'))

                //console.log(partialintegralscalculated)

                if (partialintegralscalculated) {

                    for (var i = 0; i < sortedstarttimes.length; i++) {
                        //console.log('step: ' + i)

                        if ( cp.x > sortedstarttimes[i] & cp.x < sortedfinishtimes[i]){
                            //console.log('shot found')
                            singleshotnumberofpulsestext.text = partialintegrals[i][5]
                            if (charge.checked){
                                singleshotsensortext.text = partialintegrals[i][0]
                                singleshotcerenkovtext.text = partialintegrals[i][1]
                                singleshotsensorunits.text = 'nC'
                                singleshotcerenkovunits.text = 'nC'
                            }
                            if (chargepropdose.checked){
                                singleshotsensortext.text = partialintegrals[i][2]
                                singleshotsensorunits.text = 'nC'
                                singleshotcerenkovtext.text = '--'
                                singleshotcerenkovunits.text = '--'
                            }
                            if (dose.checked){
                                    if (grays.checked) {
                                        singleshotsensortext.text = partialintegrals[i][4]
                                        singleshotsensorunits.text = 'Gy'
                                    }
                                    else {
                                       singleshotsensortext.text = partialintegrals[i][3]
                                       singleshotsensorunits.text = 'cGy'
                                    }
                                    singleshotcerenkovtext.text = '--'
                                    singleshotcerenkovunits.text = '--'
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



            onPressAndHold:{
                if ((mouse.button === Qt.MiddleButton)){
                    xstart = mouseX
                    ystart = mouseY
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
                    v5xaxis.min = xaxis.min
                    v5xaxis.max = xaxis.max
                    minus15vxaxis.max = xaxis.max
                    minus15vxaxis.min = xaxis.min
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
                    v5xaxis.min = xaxis.min
                    v5xaxis.max = xaxis.max
                    minus15vxaxis.max = xaxis.max
                    minus15vxaxis.min = xaxis.min
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
            }
        }
    }

    Item {
        id: chartpowersholder
        anchors.right: resultsholder.left
        anchors.left: parent.left
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
            id: chart5v
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

        ChartView{
            id: chartminus15v
            theme: ChartView.ChartThemeDark
            anchors.fill: parent
            visible: minus15vradiobutton.checked

            ValueAxis{
                id: minus15vyaxis
                min: -16
                max: -14
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
        target: myultrafast

        function onSignalshowdialogerror(textdialog) {
            dialogerror.title = textdialog
            dialogerror.visible = true
        }

        function onSignaltonotes(notesfromfile) {
            console.log('notes from file: ' + notesfromfile)
            settingsview.notes = notesfromfile
        }

        function onSignallimits(starttimes, finishtimes) {
            console.log('starttimes: ' + starttimes)
            ma.starttimes = starttimes
            ma.finishtimes = finishtimes
            for (var i = 0; i < starttimes.length; i++){
                var starlimit = chartchs.createSeries(ChartView.SeriesTypeLine, 'start' + i, xaxis, yaxis)
                starlimit.color = 'lightgreen'
                starlimit.style = Qt.DashLine
                starlimit.append (starttimes[i], 0)
                starlimit.append (starttimes[i], maxynopulses)
            }

            for (var j = 0; j < finishtimes.length; j++){
                var finishlimit = chartchs.createSeries(ChartView.SeriesTypeLine, 'finish' + j, xaxis, yaxis)
                finishlimit.color = 'lightsalmon'
                finishlimit.style = Qt.DashLine
                finishlimit.append (finishtimes[j], 0)
                finishlimit.append (finishtimes[j], maxynopulses)
            }
        }

        function onSignalfullintegrals(fullintegrals) {
            console.log('fullintegrals: ' + fullintegrals)
            fullintegralsnow = fullintegrals
            pulsescheck.enabled = true
            calcpddbutton.enabled = true
            deletelimits.enabled = true
            yaxis.max = pulsescheck.checked ? maxypulses : maxynopulses
            myultrafast.updateserie(chartchs.series('sensor'), 'chargesensor', pulsescheck.checked)
            myultrafast.updateserie(chartchs.series('cerenkov'), 'chargecerenkov', pulsescheck.checked)
            allshotsnumberofpulsestext.text = fullintegralsnow[5]
            if (charge.checked) {
                allshotssensortext.text = fullintegralsnow[0]
                allshotscerenkovtext.text = fullintegralsnow[1]
                allshotssensorunits.text = 'nC'
                allshotscerenkovunits.text = 'nC'
            }
            if (chargepropdose.checked) {
                allshotssensortext.text = fullintegralsnow[2]
                allshotssensorunits.text = 'nC'
                allshotscerenkovtext.text = '--'
                allshotscerenkovunits.text = '--'
            }
            if (dose.checked) {
                if (grays.checked) {
                    allshotssensortext.text = fullintegralsnow[4]
                    allshotssensorunits.text = 'Gy'
                }
                else {
                    allshotssensortext.text = fullintegralsnow[3]
                    allshotssensorunits.text = 'cGy'
                    }
                allshotscerenkovtext.text = '--'
                allshotscerenkovunits.text = '--'
            }

        }

        function onSignalpartialintegrals(sortedstarttimes, sortedfinishtimes, partialintegrals){
            ma.partialintegralscalculated = true
            ma.sortedstarttimes = sortedstarttimes
            ma.sortedfinishtimes = sortedfinishtimes
            ma.partialintegrals = partialintegrals
            if (pulsescheck.checked) {
                myanalyzew.updateserie(chartchs.series('pulse'), 'pulsetoplot', pulsescheck.checked)
            }

        }

        function onSignalreadytoplot(limits) {
            //console.log('limits: ' + limits)
            xaxis.max = limits[0] + 1
            xaxis.min = 0
            yaxis.min = 0
            psxaxis.max = limits[0] + 1
            tempxaxis.max = limits[0] + 1
            v5xaxis.max = limits[0] + 1
            minus15vxaxis.max = limits[0] + 1
            maxynopulses = limits[1]
            maxypulses = limits[2]
            tempyaxis.min = limits[3]
            tempyaxis.max = limits[4]
            psyaxis.min = limits[7]
            psyaxis.max = limits[8]
            v5yaxis.min = limits[5]
            v5yaxis.max = limits[6]
            minus15vyaxis.min = limits[9]
            minus15vyaxis.max = limits[10]
            myultrafast.updateserie(psserie, 'PS', pulsescheck.checked)
            myultrafast.updateserie(tempserie, 'temp', pulsescheck.checked)
            myultrafast.updateserie(v5serie, '5V', pulsescheck.checked)
            myultrafast.updateserie(minus15vserie, '-15V', pulsescheck.checked)

        }

        function onSignalpddfinished(pddlimits) {
            pddcalculated = true
            pddlimitsglobal = pddlimits
            console.log('pddlimits: ' + pddlimits)
            chartchs.removeAllSeries()
            chartchs.createSeries(ChartView.SeriesTypeScatter, 'pdd', xaxis, yaxis)
            chartchs.series('pdd').color = colors[0]
            chartchs.series('pdd').useOpenGL = true
            chartchs.series('pdd').markerSize = 5
            xaxis.min = pddlimits[0]
            xaxis.max = pddlimits[1]
            yaxis.min = pulsescheck.checked ? pddlimits[2] : pddlimits[3]
            yaxis.max = pulsescheck.checked ? pddlimits[4] : 100
            yaxis.titleText = pulsescheck.checked ? 'Charge prop. dose (nC)' : 'PDD %'
            xaxis.titleText = 'Depth (mm)'
            myultrafast.updatepdd(chartchs.series('pdd'), pulsescheck.checked)

        }

    }
}
