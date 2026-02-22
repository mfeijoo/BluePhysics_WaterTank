import QtQuick 2.0
import QtQuick.Window 2.10
import QtQuick.Controls 2.3
import QtQuick.Controls.Material 2.0
import QtQuick.Layouts 1.3
import Qt.labs.settings 1.0


ApplicationWindow {
    id: mainapplication
    visible: true
    title: analyzeview.fileselected === 'none' ? "BlueSoft v11.21 file: " + settingsview.filename : "BlueSoft v11.21 file: " + analyzeview.fileselected
    Material.theme: Material.Dark
    Material.accent: Material.Blue

    Settingsview{id: settingsview}
    Measureview{id: measureview}
    Darkcurrentview{id: darkcurrentview}
    Regulateview{id: regulateview}
    Cartridgeview{id: cartridgeview}
    Analyzeview{id: analyzeview}
    Ultrafastcommissioning{id: ultrafastcommissioning}

    Component.onCompleted: mainapplication.showMaximized()


    Settings {
        id: mysettings
        property alias powersupply: regulateview.psvalue
        property alias filename: settingsview.filename
        property alias acr0: settingsview.acr0
        property alias calib0: settingsview.calib0
        property alias acr1: settingsview.acr1
        property alias calib1: settingsview.calib1
        property alias acr2: settingsview.acr2
        property alias calib2: settingsview.calib2
        property alias acr3: settingsview.acr3
        property alias calib3: settingsview.calib3
        property alias acr4: settingsview.acr4
        property alias calib4: settingsview.calib4
        property alias acr5: settingsview.acr5
        property alias calib5: settingsview.calib5
        property alias acr6: settingsview.acr6
        property alias calib6: settingsview.calib6
        property alias acr7: settingsview.acr7
        property alias calib7: settingsview.calib7
        property alias notes: settingsview.notes
        //property alias cartridgeincomboboxindex: settingsview.cartridgeincomboboxindex
        //property alias functionch0index: settingsview.functionch0index
        //property alias functionch1index: settingsview.functionch1index
        //property alias functionch2index: settingsview.functionch2index
        //property alias functionch3index: settingsview.functionch3index
        //property alias functionch4index: settingsview.functionch4index
        //property alias functionch5index: settingsview.functionch5index
        //property alias functionch6index: settingsview.functionch6index
        //property alias functionch7index: settingsview.functionch7index
    }


    Drawer {
        id: navigationdrawer
        width: 240
        height: parent.height

        Image {
            id: logo
            source: "icons/logo-bluephysics-transparent.svg"
            width: parent.width
            anchors.top: parent.top
            fillMode:  Image.PreserveAspectFit
        }

        Label {
            id: version
            text: "    BlueSoft v11.21"
            width: parent.width
            anchors.top: logo.bottom
        }

        Button {
            id: regulatebutton
            width: parent.width
            anchors.top: version.bottom
            display: AbstractButton.TextBesideIcon
            icon.source: "icons/regulate.png"
            text: "REGULATE"
            leftPadding: -50
            spacing: 50
            onClicked: {
                regulateview.visible = true
                cartridgeview.visible = false
                darkcurrentview.visible = false
                measureview.visible = false
                settingsview.visible = false
                analyzeview.visible = false
                ultrafastcommissioning.visible = false
                navigationdrawer.close()
            }
        }

        Button {
            id: drawsettingsbutton
            width: parent.width
            anchors.top: regulatebutton.bottom
            display: AbstractButton.TextBesideIcon
            icon.source: "icons/settings.png"
            text: "SETTINGS"
            leftPadding: -50
            spacing: 50
            onClicked: {
                settingsview.visible = true
                cartridgeview.visible = false
                darkcurrentview.visible = false
                measureview.visible = false
                regulateview.visible = false
                analyzeview.visible = false
                ultrafastcommissioning.visible = false
                navigationdrawer.close()
            }
        }


        Button {
            id: darkcurrentbutton
            width: parent.width
            anchors.top: drawsettingsbutton.bottom
            display: AbstractButton.TextBesideIcon
            icon.source: "icons/darkcurrent.png"
            text: " SET ZERO       "
            leftPadding: -20
            spacing: 50
            onClicked: {
                darkcurrentview.visible = true
                cartridgeview.visible = false
                measureview.visible = false
                regulateview.visible = false
                settingsview.visible = false
                analyzeview.visible = false
                ultrafastcommissioning.visible = false
                navigationdrawer.close()
            }
        }

        Button {
            id: measurebutton
            width: parent.width
            anchors.top: darkcurrentbutton.bottom
            display: AbstractButton.TextBesideIcon
            icon.source: "icons/measure1.png"
            text: "MEASURE"
            leftPadding: -50
            spacing: 50
            onClicked: {
                measureview.visible = true
                cartridgeview.visible = false
                darkcurrentview.visible = false
                regulateview.visible = false
                settingsview.visible = false
                analyzeview.visible = false
                ultrafastcommissioning.visible = false
                navigationdrawer.close()
            }
        }




        Button {
            id: cartridgebutton
            width: parent.width
            anchors.top: measurebutton.bottom
            display: AbstractButton.TextBesideIcon
            icon.source: "icons/cartridgeicon.png"
            text: "CARTRIDGE"
            leftPadding: -50
            spacing: 50
            enabled: false
            onClicked: {
                cartridgeview.visible = true
                settingsview.visible = false
                darkcurrentview.visible = false
                measureview.visible = false
                regulateview.visible = false
                analyzeview.visible = false
                ultrafastcommissioning.visible = false
                navigationdrawer.close()
            }
        }



        Button {
            id: drawanalyzebutton
            width: parent.width
            anchors.top: cartridgebutton.bottom
            display: AbstractButton.TextBesideIcon
            icon.source: "icons/chart-bar.png"
            text: "ANALYZE"
            leftPadding: -50
            spacing: 50
            onClicked: {
                analyzeview.visible = true
                settingsview.visible = false
                cartridgeview.visible = false
                darkcurrentview.visible = false
                measureview.visible = false
                regulateview.visible = false
                ultrafastcommissioning.visible = false
                navigationdrawer.close()
            }
        }

        Button {
            id: ultrafastcommissioningbutton
            width: parent.width
            anchors.top: drawanalyzebutton.bottom
            display: AbstractButton.TextBesideIcon
            icon.source: "icons/clock-fast.png"
            text: "ULTRAFAST"
            leftPadding: -50
            spacing: 50
            enabled: false
            onClicked: {
                analyzeview.visible = false
                settingsview.visible = false
                cartridgeview.visible = false
                darkcurrentview.visible = false
                measureview.visible = false
                regulateview.visible = false
                ultrafastcommissioning.visible = true
                navigationdrawer.close()
            }
        }

        Button {
            id: powerdownbutton
            width: parent.width
            anchors.top: ultrafastcommissioningbutton.bottom
            display: AbstractButton.TextBesideIcon
            icon.source: "icons/power-standby.png"
            text: "QUIT"
            leftPadding: -70
            spacing: 70
           onClicked: Qt.quit()
        }

    }
  

}

