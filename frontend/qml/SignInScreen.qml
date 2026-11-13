import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Window

// Tap your name, then enter your PIN. Each person sees only their own health data.
Item {
    id: screen
    objectName: "signin"
    readonly property bool ground: vigil.stationName === "ground"
    // Re-read whenever sign-in, lock or mission changes, so a sign-out from the lock screen never shows stale data.
    readonly property var deps: [vigil.version, vigil.mode, vigil.signedIn, vigil.locked, vigil.stage, refresh]
    readonly property var info: {
        var out = Api.ask("mission_info", { v: deps })
        return out.error ? { name: "", day: "", length_days: "", live_exists: false, demo_pin: null } : out
    }
    readonly property var members: Api.ask("members", { station: vigil.stationName, v: deps }).members || []
    readonly property bool anyLocked: members.some(function (m) { return m.locked })
    property int refresh: 0
    property var chosen: null
    property string switchError: ""

    // A locked account's tile counts down to the moment it opens again.
    Timer { interval: 1000; repeat: true; running: screen.visible && screen.anyLocked; onTriggered: screen.refresh += 1 }

    function clock(seconds) { return Math.floor(seconds / 60) + ":" + String(seconds % 60).padStart(2, "0") }
    function openMission(mode) { switchError = vigil.openMission(mode) }

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
                                Note {
                                    text: tile.modelData.locked ? "Locked · opens in " + screen.clock(tile.modelData.locked_seconds) : tile.modelData.role_name
                                    color: tile.modelData.locked ? Theme.warning : Theme.ink2
                                    font.features: { "tnum": 1 }
                                }
                            }
                        }
                    }
                }
            }
            Banner {
                visible: screen.members.length === 0
                tone: "caution"
                text: screen.ground ? "There are no Mission Control accounts on this mission yet. The Commander adds one on the vehicle under Accounts, with the role Mission Control." : "There are no accounts yet."
            }
            VButton {
                visible: screen.ground
                text: "Close this window"
                onClicked: screen.Window.window.close()
            }
            Banner { tone: "error"; text: screen.switchError }
            Item { Layout.fillHeight: true }
            RowLayout {
                visible: !screen.ground
                spacing: 8
                VButton {
                    kind: "quiet"
                    visible: !vigil.isDemo
                    text: "Open the demo mission"
                    onClicked: screen.openMission("demo")
                }
                VButton {
                    kind: "quiet"
                    visible: vigil.isDemo && screen.info.live_exists
                    text: "Open our mission"
                    onClicked: screen.openMission("live")
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
