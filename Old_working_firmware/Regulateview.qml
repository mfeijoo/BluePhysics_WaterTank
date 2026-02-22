import QtQuick 2.0
import QtQuick.Controls 2.3
import QtQuick.Layouts 1.3


Item {
    id: regulateview
    anchors.fill: parent
    visible: true
    property alias psrealvalue: psspinbox.realValue
    property alias psvalue: psspinbox.value

    ToolBar {
        id: regulatetoolbar
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
                text: "REGULATE"
                font.pixelSize: 20
                font.bold: true
            }

        }
    }
    Label {
        text: "SET POWER SUPPLY TO (V):"
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: psspinbox.top
        anchors.bottomMargin: 50
    }

    SpinBox {
        id: psspinbox
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.verticalCenter
        anchors.bottomMargin: 50
        from: 4000
        value: 5656
        to: 6000
        stepSize: 1
        font.pointSize: 20
        editable: true
        enabled: true

        property int decimals: 2
        property real realValue: value / 100

        validator: DoubleValidator {
            bottom: Math.min(psspinbox.from, psspinbox.to)
            top: Math.max(psspinbox.from, psspinbox.to)
        }

        textFromValue: function(value, locale) {
            return Number(value / 100).toLocaleString(locale, 'f', psspinbox.decimals)
        }

        valueFromText: function(txt, locale) {
            return Number.fromLocaleString(locale, txt) * 100
        }

        onValueModified: {regulatethread.setvoltage(realValue)}

    }


    Button {
        id: startregulatebutton
        width: 100
        anchors.top: parent.verticalCenter
        anchors.topMargin: 50
        anchors.horizontalCenter: parent.horizontalCenter
        text: "START"
        icon.source: "icons/play.png"
        display: AbstractButton.TextBesideIcon
        objectName: "startregulatebutton"
        onClicked: {
            startregulatebutton.enabled = false
            regulatethread.startregulating(psspinbox.realValue)
            stopregulatebutton.enabled = true
        }
    }

    ProgressBar {
        id: regulateprogressbar
        width: 200
        height: 30
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: startregulatebutton.bottom
        anchors.topMargin: 85
        from: 4000
        to: psspinbox.realValue * 100
    }

    Button {
        id: stopregulatebutton
        enabled: false
        width: 100
        anchors.top: regulateprogressbar.bottom
        anchors.topMargin: 50
        anchors.horizontalCenter: parent.horizontalCenter
        objectName:'stopregulatebutton'
        text: "STOP"
        icon.source: "icons/stop.png"
        display: AbstractButton.TextBesideIcon
        onClicked: { regulatethread.stopping()
                     startregulatebutton.enabled = true
                     enabled = false
                   }
    }

    Connections {
        target: regulatethread
        function onVoltagechanged(voltagenow) {
            regulateprogressbar.value = voltagenow
        }
        function onRegulatefinished() {
            startregulatebutton.enabled = true
            stopregulatebutton.enabled = false
        }
    }
}


