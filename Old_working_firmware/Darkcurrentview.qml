import QtQuick 2.0
import QtQuick.Controls 2.3
import QtQuick.Layouts 1.3

Item {
    id: darkcurrentview
    anchors.fill: parent
    visible: false

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
                text: "SET ZERO"
                font.pixelSize: 20
                font.bold: true
            }
        }
    }

    Button{
        id: startdarkcurrent
        width: 100
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: -200
        icon.source: "icons/play.png"
        text: "START"
        display: AbstractButton.TextBesideIcon
        onClicked: {mydarkcurrentthread.startdarkcurrent()
                    enabled = false
                    stopdarkcurrent.enabled = true
                    ch0darkcurrentprogressbar.value = 0
                    ch1darkcurrentprogressbar.value = 0
                    ch2darkcurrentprogressbar.value = 0
                    ch3darkcurrentprogressbar.value = 0
                    ch4darkcurrentprogressbar.value = 0
                    ch5darkcurrentprogressbar.value = 0
                    ch6darkcurrentprogressbar.value = 0
                    ch7darkcurrentprogressbar.value = 0}
    }

    Button{
        id: stopdarkcurrent
        width: 100
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: startdarkcurrent.bottom
        anchors.topMargin: 20
        icon.source: "icons/stop.png"
        text: "STOP"
        display: AbstractButton.TextBesideIcon
        enabled: false
        onClicked: {mydarkcurrentthread.stopping()
                    startdarkcurrent.enabled = true}
    }

    ProgressBar {
        id: ch0darkcurrentprogressbar
        width: 200
        height: 30
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: stopdarkcurrent.bottom
        anchors.topMargin: 20
        from: 0
        to: -10
        
    }

    Label {
        anchors.verticalCenter: ch0darkcurrentprogressbar.verticalCenter
        anchors.right: ch0darkcurrentprogressbar.left
        width: 50
        height: 20
        text: "CH0"
    }

    ProgressBar {
        id: ch1darkcurrentprogressbar
        width: 200
        height: 30
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: ch0darkcurrentprogressbar.bottom
        anchors.topMargin: 20
        from: 0
        to: -10
    }

    Label {
        anchors.verticalCenter: ch1darkcurrentprogressbar.verticalCenter
        anchors.right: ch1darkcurrentprogressbar.left
        width: 50
        height: 20
        text: "CH1"
    }

    ProgressBar {
        id: ch2darkcurrentprogressbar
        width: 200
        height: 30
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: ch1darkcurrentprogressbar.bottom
        anchors.topMargin: 20
        from: 0
        to: -10
    }

    Label {
        anchors.verticalCenter: ch2darkcurrentprogressbar.verticalCenter
        anchors.right: ch2darkcurrentprogressbar.left
        width: 50
        height: 20
        text: "CH2"
    }

    ProgressBar {
        id: ch3darkcurrentprogressbar
        width: 200
        height: 30
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: ch2darkcurrentprogressbar.bottom
        anchors.topMargin: 20
        from: 0
        to: -10
    }

    Label {
        anchors.verticalCenter: ch3darkcurrentprogressbar.verticalCenter
        anchors.right: ch3darkcurrentprogressbar.left
        width: 50
        height: 20
        text: "CH3"
    }

    ProgressBar {
        id: ch4darkcurrentprogressbar
        width: 200
        height: 30
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: ch3darkcurrentprogressbar.bottom
        anchors.topMargin: 20
        from: 0
        to: -10
    }

    Label {
        anchors.verticalCenter: ch4darkcurrentprogressbar.verticalCenter
        anchors.right: ch4darkcurrentprogressbar.left
        width: 50
        height: 20
        text: "CH4"
    }

    ProgressBar {
        id: ch5darkcurrentprogressbar
        width: 200
        height: 30
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: ch4darkcurrentprogressbar.bottom
        anchors.topMargin: 20
        from: 0
        to: -10
    }

    Label {
        anchors.verticalCenter: ch5darkcurrentprogressbar.verticalCenter
        anchors.right: ch5darkcurrentprogressbar.left
        width: 50
        height: 20
        text: "CH5"
    }

    ProgressBar {
        id: ch6darkcurrentprogressbar
        width: 200
        height: 30
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: ch5darkcurrentprogressbar.bottom
        anchors.topMargin: 20
        from: 0
        to: -10
    }

    Label {
        anchors.verticalCenter: ch6darkcurrentprogressbar.verticalCenter
        anchors.right: ch6darkcurrentprogressbar.left
        width: 50
        height: 20
        text: "CH6"
    }

    ProgressBar {
        id: ch7darkcurrentprogressbar
        width: 200
        height: 30
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: ch6darkcurrentprogressbar.bottom
        anchors.topMargin: 20
        from: 0
        to: -10
    }

    Label {
        anchors.verticalCenter: ch7darkcurrentprogressbar.verticalCenter
        anchors.right: ch7darkcurrentprogressbar.left
        width: 50
        height: 20
        text: "CH7"
    }

    Connections {
        target: mydarkcurrentthread

        function onCh0dcchanged(ch0dcvalue) {ch0darkcurrentprogressbar.value = ch0dcvalue
                         console.log('ch0 darkcurrent value now: ' + ch0dcvalue)}
        function onCh1dcchanged(ch1dcvalue) {ch1darkcurrentprogressbar.value = ch1dcvalue}
        function onCh2dcchanged(ch2dcvalue) {ch2darkcurrentprogressbar.value = ch2dcvalue}
        function onCh3dcchanged(ch3dcvalue) {ch3darkcurrentprogressbar.value = ch3dcvalue}
        function onCh4dcchanged(ch4dcvalue) {ch4darkcurrentprogressbar.value = ch4dcvalue}
        function onCh5dcchanged(ch5dcvalue) {ch5darkcurrentprogressbar.value = ch5dcvalue}
        function onCh6dcchanged(ch6dcvalue) {ch6darkcurrentprogressbar.value = ch6dcvalue}
        function onCh7dcchanged(ch7dcvalue) {ch7darkcurrentprogressbar.value = ch7dcvalue}
        function onDarkcurrentend() {stopdarkcurrent.enabled = false
                           startdarkcurrent.enabled = true}
    }
}
