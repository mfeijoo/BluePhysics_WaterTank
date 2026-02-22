import QtQuick 2.0
import QtQuick.Controls 2.3
import QtQuick.Layouts 1.3
import QtQuick.Controls.Material 2.0


Item {
    id: cartridgeview
    anchors.fill: parent
    visible: false


    ToolBar {
        id: cartridgetoolbar
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
                text: "CARTRIDGE"
                font.pixelSize: 20
                font.bold: true
            }

        }
    }


    GroupBox {
        id: datelastupdate
        title: "DATE OF LAST UPDATE"
        anchors.top: cartridgetoolbar.bottom
        anchors.topMargin: 10
        anchors.left: parent.left
        anchors.leftMargin: 10

        Row {
            spacing: 10
            GroupBox {
                title: 'DAY'
                Text {
                    id: datetimelastupdateday
                    font.pixelSize: 30
                    color: Material.color(Material.LightGreen)
                }
            }
            GroupBox {
                title: 'MONTH'
                width: 180
                Text {
                    id: datetimelastupdatemonth
                    font.pixelSize: 30
                    color: Material.color(Material.LightGreen)
                }
            }
            GroupBox {
                title: "YEAR"
                Text {
                    id: datetimelastupdateyear
                    font.pixelSize: 30
                    color: Material.color(Material.LightGreen)

                }
            }
        }

    }

    GroupBox {
        id: timelastupdate
        title: 'TIME OF LAST UPDATE'
        anchors.top: cartridgetoolbar.bottom
        anchors.topMargin: 10
        anchors.left: datelastupdate.right
        anchors.leftMargin: 10
        Row {
            spacing: 10
            GroupBox {
                title: 'HOUR'
                Text {
                    id: datetimelastupdatehour
                    font.pixelSize: 30
                    color: Material.color(Material.LightGreen)
                }
            }
            GroupBox {
                title: 'MINUTES'
                Text {
                    id: datetimelastupdateminute
                    font.pixelSize: 30
                    color: Material.color(Material.LightGreen)
                }
            }

        }
    }

    GroupBox {
        id: model
        title: 'CARTRIDGE MODEL'
        anchors.top: cartridgetoolbar.bottom
        anchors.topMargin: 10
        anchors.left: timelastupdate.right
        anchors.leftMargin: 10
        anchors.bottom: timelastupdate.bottom
        width: 220
        Text {
            id: cartridgemodel
            font.pixelSize: 30
            color: Material.color(Material.LightRed)
        }
    }

    GroupBox {
        id: serial
        title: 'SERIAL NUMBER'
        anchors.top: cartridgetoolbar.bottom
        anchors.topMargin: 10
        anchors.left: model.right
        anchors.leftMargin: 10
        anchors.bottom: timelastupdate.bottom
        width: 220
        Text {
            id: serialnumber
            font.pixelSize: 30
            color: Material.color(Material.LightRed)
        }
    }

    GroupBox {
        id: manufacturedate
        title: "MANUFACTURE DATE"
        anchors.top: cartridgetoolbar.bottom
        anchors.topMargin: 10
        anchors.left: serial.right
        anchors.leftMargin: 10

        Row {
            spacing: 10
            GroupBox {
                title: 'DAY'
                Text {
                    id: datetimemanufactureday
                    font.pixelSize: 30
                    color: Material.color(Material.LightGreen)
                }
            }
            GroupBox {
                title: 'MONTH'
                width: 180
                Text {
                    id: datetimemanufacturemonth
                    font.pixelSize: 30
                    color: Material.color(Material.LightGreen)
                }
            }
            GroupBox {
                title: "YEAR"
                Text {
                    id: datetimemanufactureyear
                    font.pixelSize: 30
                    color: Material.color(Material.LightGreen)
                }
            }
        }

    }

    GroupBox {
        id: fiberlength
        title: "FIBER LENGTH (m)"
        anchors.top: datelastupdate.bottom
        anchors.topMargin: 10
        anchors.left: parent.left
        anchors.leftMargin: 10
        height: datelastupdate.height
        Text {
            id: fiberlengthtext
            font.pixelSize: 30
            color: Material.color(Material.LightBlue)
        }
    }

    GroupBox {
        id: sensorlength
        title: "SENSOR LENGTH (mm)"
        anchors.top: datelastupdate.bottom
        anchors.topMargin: 10
        anchors.left: fiberlength.right
        anchors.leftMargin: 10
        height: datelastupdate.height
        Text {
            id: sensorlengthtext
            font.pixelSize: 30
            color: Material.color(Material.LightBlue)
        }
    }

    GroupBox {
        id: sensordiameter
        title: "SENSOR DIAMETER (mm)"
        anchors.top: datelastupdate.bottom
        anchors.topMargin: 10
        anchors.left: sensorlength.right
        anchors.leftMargin: 10
        height: datelastupdate.height
        Text {
            id: sensordiametertext
            font.pixelSize: 30
            color: Material.color(Material.LightBlue)
        }
    }

    GroupBox {
        id: sensortype
        title: "SENSOR TYPE"
        anchors.top: datelastupdate.bottom
        anchors.topMargin: 10
        anchors.left: sensordiameter.right
        anchors.leftMargin: 10
        height: datelastupdate.height
        width: 220
        Text {
            id: sensortypetext
            font.pixelSize: 30
            color: Material.color(Material.LightBlue)
        }
    }

    GroupBox {
        id: connectortype
        title: "FIBER CONNECTOR TYPE"
        anchors.top: datelastupdate.bottom
        anchors.topMargin: 10
        anchors.left: sensortype.right
        anchors.leftMargin: 10
        height: datelastupdate.height
        width: 220
        Text {
            id: fiberconnectortypetext
            font.pixelSize: 30
            color: Material.color(Material.LightBlue)
        }
    }

    GroupBox {
        id: fiberconnectorversion
        title: "FIBER CONNECTOR VERSION"
        anchors.top: datelastupdate.bottom
        anchors.topMargin: 10
        anchors.left: connectortype.right
        anchors.leftMargin: 10
        height: datelastupdate.height
        Text {
            id: fiberconnectorversiontext
            font.pixelSize: 30
            color: Material.color(Material.LightBlue)
        }
    }

    GroupBox {
        id: fiberconnectorserialnumber
        title: "FIBER CONNECTOR SERIAL NUMBER"
        anchors.top: datelastupdate.bottom
        anchors.topMargin: 10
        anchors.left: fiberconnectorversion.right
        anchors.leftMargin: 10
        height: datelastupdate.height
        Text {
            id: fiberconnectorserialnumbertext
            font.pixelSize: 30
            color: Material.color(Material.LightBlue)
        }
    }

    GroupBox {
        id: fiberconnectorlastupdatedate
        title: "FIBER CONNECTOR LAST UPDATE DATE"
        anchors.top: fiberlength.bottom
        anchors.topMargin: 10
        anchors.left: parent.left
        anchors.leftMargin: 10

        Row {
            spacing: 10
            GroupBox {
                title: 'DAY'
                Text {
                    id: fiberconnectorlastupdatedateday
                    font.pixelSize: 30
                    color: Material.color(Material.LightGreen)
                }
            }
            GroupBox {
                title: 'MONTH'
                width: 180
                Text {
                    id: fiberconnectorlastupdatedatemonth
                    font.pixelSize: 30
                    color: Material.color(Material.LightGreen)
                }
            }
            GroupBox {
                title: "YEAR"
                Text {
                    Text {
                        id: fiberconnectorlastupdatedateyear
                        font.pixelSize: 30
                        color: Material.color(Material.LightGreen)
                    }
                }
            }
        }

    }

    GroupBox {
        id: transducerused
        title: "TRANSDUCER USED"
        anchors.top: fiberlength.bottom
        anchors.topMargin: 10
        anchors.left: fiberconnectorlastupdatedate.right
        anchors.leftMargin: 10
        height: datelastupdate.height
        width: 220
        Text {
            id: transducerusedtext
            font.pixelSize: 30
            color: Material.color(Material.LightBlue)
        }

    }

    GroupBox {
        id: transducerserials
        title: "TRANSDUCER SERIALS"
        anchors.top: transducerused.bottom
        anchors.topMargin: 10
        anchors.left: parent.left
        anchors.leftMargin: 10
        GridLayout {
            columns: 4
            Text {
                id: transducer0serialtext
                font.pixelSize: 30
                color: Material.color(Material.LightGreen)
            }
            Text {
                id: transducer1serialtext
                font.pixelSize: 30
                color: Material.color(Material.LightGreen)
            }
            Text {
                id: transducer2serialtext
                font.pixelSize: 30
                color: Material.color(Material.LightGreen)
            }
            Text {
                id: transducer3serialtext
                font.pixelSize: 30
                color: Material.color(Material.LightGreen)
            }
            Text {
                id: transducer4serialtext
                font.pixelSize: 30
                color: Material.color(Material.LightGreen)
            }
            Text {
                id: transducer5serialtext
                font.pixelSize: 30
                color: Material.color(Material.LightGreen)
            }
            Text {
                id: transducer6serialtext
                font.pixelSize: 30
                color: Material.color(Material.LightGreen)
            }
            Text {
                id: transducer7serialtext
                font.pixelSize: 30
                color: Material.color(Material.LightGreen)
            }
        }
    }

    Button {
        id: readallbt
        anchors.top: transducerserials.bottom
        anchors.topMargin: 10
        anchors.left: transducerserials.left
        text: "READ MEMORY"
        onClicked: {
            mycartridgew.readallmemory()
        }
        //Component.onCompleted: mycartridgew.readallmemory()
    }

    Connections {

        target: mycartridgew

        function onSignaldisplaymemorydata(listdatamemory) {
            console.log(listdatamemory)
            measureview.numberofchannels = listdatamemory[2]
            settingsview.cartridgeincomboboxindex = listdatamemory[5]
            settingsview.functionch0index = listdatamemory[6]
            settingsview.functionch1index = listdatamemory[7]
            settingsview.functionch2index = listdatamemory[8]
            settingsview.functionch3index = listdatamemory[9]
            settingsview.functionch4index = listdatamemory[10]
            settingsview.functionch5index = listdatamemory[11]
            settingsview.functionch6index = listdatamemory[12]
            settingsview.functionch7index = listdatamemory[13]
            regulateview.psvalue = listdatamemory[3] * 100 + listdatamemory[4]
        }
    }
}


