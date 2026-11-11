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
            RowLayout {
                spacing: 14
                Text { text: "Vigil"; font.family: Theme.body; font.weight: Font.DemiBold; font.pixelSize: 28; font.letterSpacing: -0.9; color: Theme.ink }
                Placard { text: screen.ground ? "Mission Control station" : screen.info.name }
                Placard { visible: !screen.ground; text: "Day " + screen.info.day + " of " + screen.info.length_days; font.features: { "tnum": 1 } }
            }
            Statement {
                Layout.topMargin: 18
                size: 44
                lead: screen.ground ? "Mission Control." : "Who is signing in?"
                detail: screen.ground ? "Sign in to see what the crew has sent." : "Tap your name."
            }
            Banner {
                visible: !!screen.info.demo_pin
                text: screen.info.demo_pin ? "This is the demo mission with simulated crew. Every PIN is " + screen.info.demo_pin + ". Sign in as the Presenter to play the guided demo." : ""
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
                            color: tile.current ? Theme.panel : Theme.panel2
                            border.width: tile.current || tile.visualFocus ? 2 : 0
                            border.color: Theme.action
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
                text: screen.ground ? "No Mission Control accounts yet. The Commander adds them on the vehicle under Accounts." : "No accounts yet."
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
            radius: Theme.radius
            color: Theme.panel
            border.color: Theme.isLight ? "transparent" : Theme.rule
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
                    text: screen.chosen ? screen.chosen.name : "Choose your name"
                    font.family: Theme.body; font.weight: Font.Medium; font.pixelSize: 24; color: Theme.ink
                }
                Note { Layout.alignment: Qt.AlignHCenter; Layout.fillWidth: false; text: screen.chosen ? "Enter your PIN" : "Your PIN keeps your health data yours." }
                PinPad {
                    id: pad
                    Layout.alignment: Qt.AlignHCenter
                    enabled: screen.chosen !== null
                    opacity: enabled ? 1 : 0.4
                    onSubmitted: function (pin) { screen.signIn(pin) }
                }
                Item { Layout.fillHeight: true }
            }
        }
    }
}
