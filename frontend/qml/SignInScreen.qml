import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Tap your name, then enter your PIN. Each person sees only their own health data.
Item {
    id: screen
    objectName: "signin"
    readonly property bool ground: vigil.stationName === "ground"
    readonly property var info: Api.ask("mission_info", { v: [vigil.version, vigil.mode] })
    readonly property var members: Api.ask("members", { station: vigil.stationName, v: [vigil.version, vigil.mode, refresh] }).members
    property int refresh: 0
    property var chosen: null

    function signIn(pin) {
        var err = vigil.signIn(chosen.id, pin)
        pad.error = err
        refresh += 1
    }

    RowLayout {
        anchors { fill: parent; margins: Theme.gutter; topMargin: 32; bottomMargin: 24 }
        spacing: 48

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 14
            Wordmark { size: 64 }
            RowLayout {
                spacing: 10
                Placard { text: screen.ground ? "Ground station" : screen.info.name }
                Placard { visible: !screen.ground; text: "·  Day " + screen.info.day + " / " + screen.info.length_days; font.features: { "tnum": 1 } }
            }
            Text {
                Layout.topMargin: 14
                text: screen.ground ? "Mission Control" : "Crew sign-in"
                font.family: Theme.display; font.weight: Font.ExtraBold; font.pixelSize: 40; font.letterSpacing: -1.2; color: Theme.ink
            }
            Banner {
                visible: !!screen.info.demo_pin
                text: screen.info.demo_pin ? "Demo mission with five simulated crew. Every PIN is " + screen.info.demo_pin + ". The Presenter account plays the guided demo." : ""
            }
            GridLayout {
                Layout.fillWidth: true
                Layout.topMargin: 8
                columns: 3
                rowSpacing: 14
                columnSpacing: 14
                Repeater {
                    model: screen.members
                    AbstractButton {
                        id: tile
                        required property var modelData
                        readonly property bool current: screen.chosen !== null && screen.chosen.id === modelData.id
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        implicitHeight: 104
                        focusPolicy: Qt.StrongFocus
                        Accessible.role: Accessible.Button
                        Accessible.name: modelData.name + ", " + modelData.role_name + (modelData.locked ? ", locked" : "")
                        onClicked: { screen.chosen = modelData; pad.error = ""; pad.pin = ""; pad.forceActiveFocus() }
                        background: Rectangle {
                            radius: Theme.radius
                            color: tile.current ? Theme.panel2 : Theme.panel
                            border.width: tile.current || tile.visualFocus ? 2 : 1
                            border.color: tile.current || tile.visualFocus ? Theme.ink : Theme.rule
                            opacity: tile.down ? 0.85 : 1
                        }
                        contentItem: RowLayout {
                            spacing: 14
                            Avatar { Layout.leftMargin: 16; size: 60; name: tile.modelData.name; initials: tile.modelData.tag }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text { Layout.fillWidth: true; text: tile.modelData.name; elide: Text.ElideRight; font.family: Theme.body; font.weight: Font.Medium; font.pixelSize: 19; color: Theme.ink }
                                Note { text: tile.modelData.locked ? "Locked for " + tile.modelData.locked_seconds + " s" : tile.modelData.role_name }
                            }
                        }
                    }
                }
            }
            Banner {
                visible: screen.members.length === 0
                tone: "caution"
                text: screen.ground ? "There are no Mission Control accounts yet. The Commander adds them on the vehicle, under Accounts." : "There are no accounts yet."
            }
            Item { Layout.fillHeight: true }
            RowLayout {
                visible: !screen.ground
                spacing: 8
                VButton {
                    kind: "quiet"
                    visible: !vigil.isDemo
                    text: "Open the demo mission"
                    onClicked: vigil.openMission("demo")
                }
                VButton {
                    kind: "quiet"
                    visible: vigil.isDemo && screen.info.live_exists
                    text: "Open our mission"
                    onClicked: vigil.openMission("live")
                }
                VButton {
                    kind: "quiet"
                    visible: vigil.isDemo && !screen.info.live_exists
                    text: "Set up a real mission"
                    onClicked: vigil.startSetup()
                }
            }
        }

        Rectangle {
            Layout.preferredWidth: 420
            Layout.fillHeight: true
            opacity: screen.chosen !== null ? 1 : 0
            visible: opacity > 0
            Behavior on opacity { enabled: !vigil.reduceMotion; NumberAnimation { duration: 160 } }
            radius: Theme.radius
            color: Theme.panel
            border.color: Theme.rule
            SoftShadow { visible: Theme.isLight }
            ColumnLayout {
                anchors { fill: parent; margins: 28 }
                spacing: 18
                Item { Layout.fillHeight: true }
                Avatar {
                    Layout.alignment: Qt.AlignHCenter
                    visible: screen.chosen !== null
                    size: 84
                    name: screen.chosen ? screen.chosen.name : ""
                    initials: screen.chosen ? screen.chosen.tag : ""
                }
                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: screen.chosen ? screen.chosen.name : "Sign in"
                    font.family: Theme.body; font.weight: Font.DemiBold; font.pixelSize: 24; color: Theme.ink
                }
                Placard { Layout.alignment: Qt.AlignHCenter; text: screen.chosen ? "Enter PIN" : "Select your name" }
                PinPad {
                    id: pad
                    Layout.alignment: Qt.AlignHCenter
                    visible: screen.chosen !== null
                    onSubmitted: function (pin) { screen.signIn(pin) }
                }
                Item { Layout.fillHeight: true }
            }
        }
    }
}
