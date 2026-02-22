import QtQuick 2.7
import QtQuick.Controls 2.3
import QtQuick.Layouts 1.3
import QtQuick.Controls.Material 2.0
import QtQuick.VirtualKeyboard 2.1


Item {
    id: settingsview
    anchors.fill: parent
    visible: false
    property int numberofsensors: 4
    property alias acr0: acr0.value
    property alias calib0: calib0.value
    property alias acr1: acr1.value
    property alias calib1: calib1.value
    property alias acr2: acr2.value
    property alias calib2: calib2.value
    property alias acr3: acr3.value
    property alias calib3: calib3.value
    property alias acr4: acr4.value
    property alias calib4: calib4.value
    property alias acr5: acr5.value
    property alias calib5: calib5.value
    property alias acr6: acr6.value
    property alias calib6: calib6.value
    property alias acr7: acr7.value
    property alias calib7: calib7.value
    property alias filename: filename.text
    property alias notes: notes.text
    property alias cartridgeincomboboxindex: cartridgeincombobox.currentIndex
    property alias functionch0index: functionch0.currentIndex
    property alias functionch1index: functionch1.currentIndex
    property alias functionch2index: functionch2.currentIndex
    property alias functionch3index: functionch3.currentIndex
    property alias functionch4index: functionch4.currentIndex
    property alias functionch5index: functionch5.currentIndex
    property alias functionch6index: functionch6.currentIndex
    property alias functionch7index: functionch7.currentIndex
    property bool rank0rb: rank0rb.checked
    

    InputPanel {
        id: inputpanel
        y: Qt.inputMethod.visible ? parent.height - inputpanel.height : parent.height
        anchors.left: parent.left
        anchors.right: parent.right
    }

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
        id: settingstoolbar
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
                text: "SETTINGS"
                font.pixelSize: 20
                font.bold: true
            }

        }
    }
    GroupBox {
        id: integrationtimegroupbox
        title: "INTEGRATION TIME"
        width: 500
        height: 250
        anchors.top: settingstoolbar.bottom
        anchors.topMargin: 10
        x: 10

        Text {
           anchors.verticalCenter: integrationtimespinbox.verticalCenter
           anchors.right: integrationtimespinbox.left
           anchors.rightMargin: 10
           text: qsTr("Integration Time: ")
           color: 'lightgrey'

        }

        SpinBox{
            id: integrationtimespinbox
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 10
            font.pointSize: 20
            from: 0
            to: 300000
            value: 700
            editable: true
            onValueChanged: controllerbutton.enabled = true
        }

        Text {
            anchors.verticalCenter: integrationtimespinbox.verticalCenter
            anchors.left: integrationtimespinbox.right
            anchors.leftMargin: 10
            text: qsTr('(micro seconds)')
            color: 'lightgrey'
        }


        Button {
            id: controllerbutton
            text: "SEND TO CONTROLLER"
            width: 200
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: integrationtimespinbox.bottom
            anchors.topMargin: 10
            enabled: false
            onClicked: {
                mysettingsw.sendtocontroller(integrationtimespinbox.value)
                enabled = false
            }
        }
    }
    GroupBox{
        id: saveasgroupbox
        anchors.top: settingstoolbar.bottom
        anchors.topMargin: 10
        anchors.left: integrationtimegroupbox.right
        anchors.leftMargin: 10
        width: 250
        height: 100
        title: "SAVE AS:"
        RowLayout{
            anchors.fill: parent

            TextEdit{
                id: filename
                text: 'default'
                color: 'lightgrey'
                width: 200
                onTextChanged: {mysettingsw.filenamein(text)}

            }

            Label {
                text: '.csv'
            }

        }

    }

    GroupBox {
        title: 'NOTES'
        width: 250
        anchors.top: saveasgroupbox.bottom
        anchors.topMargin: 10
        anchors.left: integrationtimegroupbox.right
        anchors.leftMargin: 10
        anchors.bottom: integrationtimegroupbox.bottom
        TextEdit{
            id: notes
            anchors.fill: parent
            text: 'notes'
            color: 'lightgrey'
            wrapMode: TextEdit.WordWrap
            onTextChanged: {mysettingsw.notesin(text)}
        }
    }

    GroupBox {
        id: ranklevelsgroupbox
        title: "CAPACITOR RANK"
        width: 150
        height: 250
        anchors.top: settingstoolbar.bottom
        anchors.topMargin: 10
        anchors.left: saveasgroupbox.right
        anchors.leftMargin: 10
        ColumnLayout{
            anchors.fill: parent
            RadioButton {
                id: rank0rb
                autoExclusive: true
                checked: true
                text: "RANK 0"
                onClicked: mysettingsw.rankselection(0)
            }

            RadioButton {
                id: rank1rb
                autoExclusive: true
                text: "RANK 1"
                onClicked: mysettingsw.rankselection(1)
            }
         }
        //comment if emulator
        Component.onCompleted: mysettingsw.readrank()
      }

    Button {
        id: readrankbutoon
        anchors.top: ranklevelsgroupbox.bottom
        anchors.left: ranklevelsgroupbox.left
        anchors.topMargin: 10
        text: "Read Rank"
        onClicked: mysettingsw.readrank()
    }

    Text {
        id: ranknowtext
        text: '0'
        anchors.top: ranklevelsgroupbox.bottom
        anchors.topMargin:  10
        anchors.left: readrankbutoon.right
        anchors.leftMargin: 10
        color: Material.color(Material.LightBlue)
        font.pixelSize: 30
    }

    GroupBox {
        id: cartridgeinbox
        title: 'CARTRIDGE IN'
        anchors.top: settingstoolbar.bottom
        anchors.topMargin: 10
        anchors.left: ranklevelsgroupbox.right
        anchors.leftMargin: 10
        width: 200
        ComboBox {
            id: cartridgeincombobox
            anchors.fill: parent
            model: ['1 sensor', '4 sensors', '7 sen. RTSafe']
            currentIndex: 2
            onCurrentIndexChanged:{
                console.log('cartridge in: ' + currentIndex)
                mysettingsw.cartridgeinboxchange(currentIndex)
            }
        }

    }



    GroupBox {
        id: sensorsinfo
        title: qsTr("SENSORS INFORMATION")
        anchors.top: settingstoolbar.bottom
        anchors.topMargin: 10
        anchors.left: cartridgeinbox.right
        anchors.leftMargin: 10
        width: 600
        property var functions: ['N/A', 'sensor0', 'cerenkov0', 'sensor1', 'cerenkov1',
                                'sensor2', 'cerenkov2', 'sensor3', 'cerenkov3',
                                'sensor4', 'sensor5', 'sensor6',
                                'sensor7']

        ScrollView {
        anchors.fill: parent
        clip: true

            GridLayout {
                anchors.top: parent.top
                anchors.horizontalCenter: parent.horizontalCenter
                columns: 4


                Rectangle {
                    width: 120
                    height: 40
                    color: 'transparent'
                    border.color: 'lightgrey'
                    Text {
                        text: qsTr("Channel")
                        color: 'lightgrey'
                        anchors.centerIn: parent
                    }
                }

                Rectangle {
                    width: 120
                    height: 40
                    color: 'transparent'
                    border.color: 'lightgrey'
                    Text {
                        text: qsTr("Function")
                        color: 'lightgrey'
                        anchors.centerIn: parent
                    }
                }

                Rectangle {
                    width: 150
                    height: 40
                    color: 'transparent'
                    border.color: 'lightgrey'
                    Text {
                        text: qsTr("ACR")
                        color: 'lightgrey'
                        anchors.centerIn: parent
                    }

                }
                Rectangle {
                    width: 150
                    height: 40
                    color: 'transparent'
                    border.color: 'lightgrey'
                    Text {
                        text: qsTr("Calib. (cGy/nC)")
                        color: 'lightgrey'
                        anchors.centerIn: parent
                    }
                }

                Rectangle {
                    id: ch0
                    width: 120
                    height: 40
                    color: 'transparent'
                    border.color: 'lightgrey'
                    Text {
                        text: 'ch0'
                        color: 'lightgrey'
                        anchors.centerIn: parent
                    }
                }

                ComboBox {
                    id: functionch0
                    width: 120
                    height: 40
                    model: sensorsinfo.functions
                    currentIndex: 0
                    onCurrentIndexChanged: {
                        console.log('current index: ' + currentIndex)
                        myseries.functionch0change(currentIndex)
                        //myanalyzew.cerenkov0change(currentIndex)
                    }
                }

                Rectangle {
                    width: 150
                    height: 40
                    color: 'transparent'
                    SpinBox {
                        id: acr0
                        from: 0
                        value: 10000000
                        to: 40000000
                        stepSize: 1
                        editable: true
                        anchors.fill: parent
                        font.pointSize: 10

                        property int decimals: 7
                        property real realValue: value / 10000000

                        validator: DoubleValidator {
                            bottom: Math.min(this.from, this.to)
                            top: Math.max(this.from, this.to)
                        }

                        textFromValue: function(value, locale) {
                            return Number(value / 10000000).toLocaleString(locale, 'f', decimals)
                        }
                        valueFromText: function(text, locale) {
                            return Number.fromLocaleString(locale, text) * 10000000
                        }
                        onValueChanged: {
                            myseries.acr0change(value)
                            //mysettingsw.acr0(value)
                        }
                     }
                }
                Rectangle {
                    width: 150
                    height: 40
                    color: 'transparent'
                    SpinBox {
                        id: calib0
                        from: 0
                        value: 10000000
                        to: 50000000
                        stepSize: 1
                        editable: true
                        anchors.fill: parent
                        font.pointSize: 10

                        property int decimals: 7
                        property real realValue: value / 10000000


                        validator: DoubleValidator {
                            bottom: Math.min(this.from, this.to)
                            top: Math.max(this.from, this.to)
                        }

                        textFromValue: function(value, locale) {
                            return Number(value / 10000000).toLocaleString(locale, 'f', decimals)
                        }

                        valueFromText: function(text, locale) {
                            return Number.fromLocaleString(locale, text) * 10000000
                        }
                        onValueChanged: {
                            myseries.calib0change(value)
                            //mysettingsw.calib0(value)
                        }
                     }
                }

                
                Rectangle {
                    id: ch1
                    width: 120
                    height: 40
                    color: 'transparent'
                    border.color: 'lightgrey'
                    Text {
                        text: 'ch1'
                        color: 'lightgrey'
                        anchors.centerIn: parent
                    }
                }

                ComboBox {
                    id: functionch1
                    width: 120
                    height: 40
                    model: sensorsinfo.functions
                    currentIndex: 0
                    onCurrentIndexChanged: {
                        myseries.functionch1change(currentIndex)
                        //myanalyzew.cerenkov0change(currentIndex)
                    }
                }

                Rectangle {
                    width: 150
                    height: 40
                    color: 'transparent'
                    SpinBox {
                        id: acr1
                        from: 0
                        value: 10000000
                        to: 40000000
                        stepSize: 1
                        editable: true
                        anchors.fill: parent
                        font.pointSize: 10

                        property int decimals: 7
                        property real realValue: value / 10000000

                        validator: DoubleValidator {
                            bottom: Math.min(this.from, this.to)
                            top: Math.max(this.from, this.to)
                        }

                        textFromValue: function(value, locale) {
                            return Number(value / 10000000).toLocaleString(locale, 'f', decimals)
                        }
                        valueFromText: function(text, locale) {
                            return Number.fromLocaleString(locale, text) * 10000000
                        }
                        onValueChanged: {
                            myseries.acr1change(value)
                            //mysettingsw.acr0(value)
                        }
                     }
                }
                Rectangle {
                    width: 150
                    height: 40
                    color: 'transparent'
                    SpinBox {
                        id: calib1
                        from: 0
                        value: 10000000
                        to: 50000000
                        stepSize: 1
                        editable: true
                        anchors.fill: parent
                        font.pointSize: 10

                        property int decimals: 7
                        property real realValue: value / 10000000


                        validator: DoubleValidator {
                            bottom: Math.min(this.from, this.to)
                            top: Math.max(this.from, this.to)
                        }

                        textFromValue: function(value, locale) {
                            return Number(value / 10000000).toLocaleString(locale, 'f', decimals)
                        }

                        valueFromText: function(text, locale) {
                            return Number.fromLocaleString(locale, text) * 10000000
                        }
                        onValueChanged: {
                            myseries.calib1change(value)
                            //mysettingsw.calib0(value)
                        }
                     }
                }

                
                Rectangle {
                    id: ch2
                    width: 120
                    height: 40
                    color: 'transparent'
                    border.color: 'lightgrey'
                    Text {
                        text: 'ch2'
                        color: 'lightgrey'
                        anchors.centerIn: parent
                    }
                }

                ComboBox {
                    id: functionch2
                    width: 120
                    height: 40
                    model: sensorsinfo.functions
                    currentIndex: 0
                    onCurrentIndexChanged: {
                        console.log('function ch2 changed')
                        myseries.functionch2change(currentIndex)
                        //myanalyzew.cerenkov0change(currentIndex)
                    }
                }

                Rectangle {
                    width: 150
                    height: 40
                    color: 'transparent'
                    SpinBox {
                        id: acr2
                        from: 0
                        value: 10000000
                        to: 40000000
                        stepSize: 1
                        editable: true
                        anchors.fill: parent
                        font.pointSize: 10

                        property int decimals: 7
                        property real realValue: value / 10000000

                        validator: DoubleValidator {
                            bottom: Math.min(this.from, this.to)
                            top: Math.max(this.from, this.to)
                        }

                        textFromValue: function(value, locale) {
                            return Number(value / 10000000).toLocaleString(locale, 'f', decimals)
                        }
                        valueFromText: function(text, locale) {
                            return Number.fromLocaleString(locale, text) * 10000000
                        }
                        onValueChanged: {
                            myseries.acr2change(value)
                            //mysettingsw.acr0(value)
                        }
                     }
                }
                Rectangle {
                    width: 150
                    height: 40
                    color: 'transparent'
                    SpinBox {
                        id: calib2
                        from: 0
                        value: 10000000
                        to: 50000000
                        stepSize: 1
                        editable: true
                        anchors.fill: parent
                        font.pointSize: 10

                        property int decimals: 7
                        property real realValue: value / 10000000


                        validator: DoubleValidator {
                            bottom: Math.min(this.from, this.to)
                            top: Math.max(this.from, this.to)
                        }

                        textFromValue: function(value, locale) {
                            return Number(value / 10000000).toLocaleString(locale, 'f', decimals)
                        }

                        valueFromText: function(text, locale) {
                            return Number.fromLocaleString(locale, text) * 10000000
                        }
                        onValueChanged: {
                            myseries.calib2change(value)
                            //mysettingsw.calib0(value)
                        }
                     }
                }
                
                Rectangle {
                    id: ch3
                    width: 120
                    height: 40
                    color: 'transparent'
                    border.color: 'lightgrey'
                    Text {
                        text: 'ch3'
                        color: 'lightgrey'
                        anchors.centerIn: parent
                    }
                }

                ComboBox {
                    id: functionch3
                    width: 120
                    height: 40
                    model: sensorsinfo.functions
                    currentIndex: 0
                    onCurrentIndexChanged: {
                        myseries.functionch3change(currentIndex)
                        //myanalyzew.cerenkov0change(currentIndex)
                    }
                }

                Rectangle {
                    width: 150
                    height: 40
                    color: 'transparent'
                    SpinBox {
                        id: acr3
                        from: 0
                        value: 10000000
                        to: 40000000
                        stepSize: 1
                        editable: true
                        anchors.fill: parent
                        font.pointSize: 10

                        property int decimals: 7
                        property real realValue: value / 10000000

                        validator: DoubleValidator {
                            bottom: Math.min(this.from, this.to)
                            top: Math.max(this.from, this.to)
                        }

                        textFromValue: function(value, locale) {
                            return Number(value / 10000000).toLocaleString(locale, 'f', decimals)
                        }
                        valueFromText: function(text, locale) {
                            return Number.fromLocaleString(locale, text) * 10000000
                        }
                        onValueChanged: {
                            myseries.acr3change(value)
                            //mysettingsw.acr0(value)
                        }
                     }
                }
                Rectangle {
                    width: 150
                    height: 40
                    color: 'transparent'
                    SpinBox {
                        id: calib3
                        from: 0
                        value: 10000000
                        to: 50000000
                        stepSize: 1
                        editable: true
                        anchors.fill: parent
                        font.pointSize: 10

                        property int decimals: 7
                        property real realValue: value / 10000000


                        validator: DoubleValidator {
                            bottom: Math.min(this.from, this.to)
                            top: Math.max(this.from, this.to)
                        }

                        textFromValue: function(value, locale) {
                            return Number(value / 10000000).toLocaleString(locale, 'f', decimals)
                        }

                        valueFromText: function(text, locale) {
                            return Number.fromLocaleString(locale, text) * 10000000
                        }
                        onValueChanged: {
                            myseries.calib3change(value)
                            //mysettingsw.calib0(value)
                        }
                     }
                }
                
                Rectangle {
                    id: ch4
                    width: 120
                    height: 40
                    color: 'transparent'
                    border.color: 'lightgrey'
                    Text {
                        text: 'ch4'
                        color: 'lightgrey'
                        anchors.centerIn: parent
                    }
                }

                ComboBox {
                    id: functionch4
                    width: 120
                    height: 40
                    model: sensorsinfo.functions
                    currentIndex: 0
                    onCurrentIndexChanged: {
                        myseries.functionch4change(currentIndex)
                        //myanalyzew.cerenkov0change(currentIndex)
                    }
                }

                Rectangle {
                    width: 150
                    height: 40
                    color: 'transparent'
                    SpinBox {
                        id: acr4
                        from: 0
                        value: 10000000
                        to: 40000000
                        stepSize: 1
                        editable: true
                        anchors.fill: parent
                        font.pointSize: 10

                        property int decimals: 7
                        property real realValue: value / 10000000

                        validator: DoubleValidator {
                            bottom: Math.min(this.from, this.to)
                            top: Math.max(this.from, this.to)
                        }

                        textFromValue: function(value, locale) {
                            return Number(value / 10000000).toLocaleString(locale, 'f', decimals)
                        }
                        valueFromText: function(text, locale) {
                            return Number.fromLocaleString(locale, text) * 10000000
                        }
                        onValueChanged: {
                            myseries.acr4change(value)
                            //mysettingsw.acr0(value)
                        }
                     }
                }
                Rectangle {
                    width: 150
                    height: 40
                    color: 'transparent'
                    SpinBox {
                        id: calib4
                        from: 0
                        value: 10000000
                        to: 50000000
                        stepSize: 1
                        editable: true
                        anchors.fill: parent
                        font.pointSize: 10

                        property int decimals: 7
                        property real realValue: value / 10000000


                        validator: DoubleValidator {
                            bottom: Math.min(this.from, this.to)
                            top: Math.max(this.from, this.to)
                        }

                        textFromValue: function(value, locale) {
                            return Number(value / 10000000).toLocaleString(locale, 'f', decimals)
                        }

                        valueFromText: function(text, locale) {
                            return Number.fromLocaleString(locale, text) * 10000000
                        }
                        onValueChanged: {
                            myseries.calib4change(value)
                            //mysettingsw.calib0(value)
                        }
                     }
                }

                Rectangle {
                    id: ch5
                    width: 120
                    height: 40
                    color: 'transparent'
                    border.color: 'lightgrey'
                    Text {
                        text: 'ch5'
                        color: 'lightgrey'
                        anchors.centerIn: parent
                    }
                }

                ComboBox {
                    id: functionch5
                    width: 120
                    height: 40
                    model: sensorsinfo.functions
                    currentIndex: 0
                    onCurrentIndexChanged: {
                        myseries.functionch5change(currentIndex)
                        //myanalyzew.cerenkov0change(currentIndex)
                    }
                }

                Rectangle {
                    width: 150
                    height: 40
                    color: 'transparent'
                    SpinBox {
                        id: acr5
                        from: 0
                        value: 10000000
                        to: 40000000
                        stepSize: 1
                        editable: true
                        anchors.fill: parent
                        font.pointSize: 10

                        property int decimals: 7
                        property real realValue: value / 10000000

                        validator: DoubleValidator {
                            bottom: Math.min(this.from, this.to)
                            top: Math.max(this.from, this.to)
                        }

                        textFromValue: function(value, locale) {
                            return Number(value / 10000000).toLocaleString(locale, 'f', decimals)
                        }
                        valueFromText: function(text, locale) {
                            return Number.fromLocaleString(locale, text) * 10000000
                        }
                        onValueChanged: {
                            myseries.acr5change(value)
                            //mysettingsw.acr0(value)
                        }
                     }
                }
                Rectangle {
                    width: 150
                    height: 40
                    color: 'transparent'
                    SpinBox {
                        id: calib5
                        from: 0
                        value: 10000000
                        to: 50000000
                        stepSize: 1
                        editable: true
                        anchors.fill: parent
                        font.pointSize: 10

                        property int decimals: 7
                        property real realValue: value / 10000000


                        validator: DoubleValidator {
                            bottom: Math.min(this.from, this.to)
                            top: Math.max(this.from, this.to)
                        }

                        textFromValue: function(value, locale) {
                            return Number(value / 10000000).toLocaleString(locale, 'f', decimals)
                        }

                        valueFromText: function(text, locale) {
                            return Number.fromLocaleString(locale, text) * 10000000
                        }
                        onValueChanged: {
                            myseries.calib5change(value)
                            //mysettingsw.calib0(value)
                        }
                     }
                }

                Rectangle {
                    id: ch6
                    width: 120
                    height: 40
                    color: 'transparent'
                    border.color: 'lightgrey'
                    Text {
                        text: 'ch6'
                        color: 'lightgrey'
                        anchors.centerIn: parent
                    }
                }

                ComboBox {
                    id: functionch6
                    width: 120
                    height: 40
                    model: sensorsinfo.functions
                    currentIndex: 0
                    onCurrentIndexChanged: {
                        myseries.functionch6change(currentIndex)
                        //myanalyzew.cerenkov6change(currentIndex)
                    }
                }

                Rectangle {
                    width: 150
                    height: 40
                    color: 'transparent'
                    SpinBox {
                        id: acr6
                        from: 0
                        value: 10000000
                        to: 40000000
                        stepSize: 1
                        editable: true
                        anchors.fill: parent
                        font.pointSize: 10

                        property int decimals: 7
                        property real realValue: value / 10000000

                        validator: DoubleValidator {
                            bottom: Math.min(this.from, this.to)
                            top: Math.max(this.from, this.to)
                        }

                        textFromValue: function(value, locale) {
                            return Number(value / 10000000).toLocaleString(locale, 'f', decimals)
                        }
                        valueFromText: function(text, locale) {
                            return Number.fromLocaleString(locale, text) * 10000000
                        }
                        onValueChanged: {
                            myseries.acr6change(value)
                            //mysettingsw.acr0(value)
                        }
                     }
                }
                Rectangle {
                    width: 150
                    height: 40
                    color: 'transparent'
                    SpinBox {
                        id: calib6
                        from: 0
                        value: 10000000
                        to: 50000000
                        stepSize: 1
                        editable: true
                        anchors.fill: parent
                        font.pointSize: 10

                        property int decimals: 7
                        property real realValue: value / 10000000


                        validator: DoubleValidator {
                            bottom: Math.min(this.from, this.to)
                            top: Math.max(this.from, this.to)
                        }

                        textFromValue: function(value, locale) {
                            return Number(value / 10000000).toLocaleString(locale, 'f', decimals)
                        }

                        valueFromText: function(text, locale) {
                            return Number.fromLocaleString(locale, text) * 10000000
                        }
                        onValueChanged: {
                            myseries.calib6change(value)
                            //mysettingsw.calib0(value)
                        }
                     }
                }

                Rectangle {
                    id: ch7
                    width: 120
                    height: 40
                    color: 'transparent'
                    border.color: 'lightgrey'
                    Text {
                        text: 'ch7'
                        color: 'lightgrey'
                        anchors.centerIn: parent
                    }
                }

                ComboBox {
                    id: functionch7
                    width: 120
                    height: 40
                    model: sensorsinfo.functions
                    currentIndex: 0
                    onCurrentIndexChanged: {
                        myseries.functionch7change(currentIndex)
                        //myanalyzew.cerenkov0change(currentIndex)
                    }
                }

                Rectangle {
                    width: 150
                    height: 40
                    color: 'transparent'
                    SpinBox {
                        id: acr7
                        from: 0
                        value: 10000000
                        to: 40000000
                        stepSize: 1
                        editable: true
                        anchors.fill: parent
                        font.pointSize: 10

                        property int decimals: 7
                        property real realValue: value / 10000000

                        validator: DoubleValidator {
                            bottom: Math.min(this.from, this.to)
                            top: Math.max(this.from, this.to)
                        }

                        textFromValue: function(value, locale) {
                            return Number(value / 10000000).toLocaleString(locale, 'f', decimals)
                        }
                        valueFromText: function(text, locale) {
                            return Number.fromLocaleString(locale, text) * 10000000
                        }
                        onValueChanged: {
                            myseries.acr7change(value)
                            //mysettingsw.acr0(value)
                        }
                     }
                }
                Rectangle {
                    width: 150
                    height: 40
                    color: 'transparent'
                    SpinBox {
                        id: calib7
                        from: 0
                        value: 10000000
                        to: 50000000
                        stepSize: 1
                        editable: true
                        anchors.fill: parent
                        font.pointSize: 10

                        property int decimals: 7
                        property real realValue: value / 10000000


                        validator: DoubleValidator {
                            bottom: Math.min(this.from, this.to)
                            top: Math.max(this.from, this.to)
                        }

                        textFromValue: function(value, locale) {
                            return Number(value / 10000000).toLocaleString(locale, 'f', decimals)
                        }

                        valueFromText: function(text, locale) {
                            return Number.fromLocaleString(locale, text) * 10000000
                        }
                        onValueChanged: {
                            myseries.calib7change(value)
                            //mysettingsw.calib0(value)
                        }
                     }
                }
        }
      }
     }

    Button {
        id: checkacquisitionbt
        anchors.left: sensorsinfo.left
        anchors.top: sensorsinfo.bottom
        anchors.topMargin: 10
        text: 'Check Acquistion Unit'
        onClicked: myseries.checkacqucartridge()
    }



    Button {
        id: checkPS0bt
        anchors.left: checkacquisitionbt.right
        anchors.leftMargin: 10
        anchors.top: sensorsinfo.bottom
        anchors.topMargin: 10
        text: 'CHECK PS0'
        onClicked: mysettingsw.checkPS0()
    }

    Text {
        id: ps0value
        anchors.left: checkPS0bt.right
        anchors.leftMargin: 10
        anchors.top: sensorsinfo.bottom
        anchors.topMargin: 10
        height: checkPS0bt.height
        color: Material.color(Material.LightBlue)
        text: '0.00'
        font.pixelSize: 30

    }

    Connections {
        target: mysettingsw

       function  onSignalshowdialogerror(textmessage) {
            dialogerror.title = textmessage
            dialogerror.visible = true
        }

        function onSignalrankread(rankchip) {
            ranknowtext.text = rankchip
            if (rankchip == '0'){
                rank0rb.checked = true
            }
            if (rankchip == '1'){
                rank1rb.checked = true
            }

        }

        function onSignalsendPS0(PS0value) {
            ps0value.text = PS0value + "V"
        }
    }
}


