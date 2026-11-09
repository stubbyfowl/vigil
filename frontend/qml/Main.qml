import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: win
    property bool kiosk: false
    property bool groundOpen: false
    title: "Vigil"
    width: 1280
    height: 800
    minimumWidth: 1024
    minimumHeight: 700
    visible: true
    visibility: kiosk ? Window.FullScreen : Window.AutomaticVisibility
    color: Theme.bg

    readonly property var screens: ({
        "": "HomeScreen.qml", alert: "AlertScreen.qml", system: "SystemScreen.qml", checkin: "CheckInScreen.qml",
        radiation: "RadiationScreen.qml", crew: "CrewScreen.qml", ground: "GroundScreen.qml", earth: "EarthScreen.qml",
        sensors: "SensorsScreen.qml", timeline: "TimelineScreen.qml", explainer: "ExplainerScreen.qml", delay: "DelayScreen.qml",
        results: "ResultsScreen.qml", about: "AboutScreen.qml", admin: "AdminScreen.qml"
    })
    readonly property string section: vigil.route.split("/")[1] || ""

    Shortcut { sequence: "Ctrl+Z"; onActivated: vigil.undo() }
    Shortcut { sequence: "Esc"; onActivated: { if (menu.opened) menu.close(); else vigil.back() } }
    Shortcut { sequence: "F11"; onActivated: win.kiosk = !win.kiosk }
    Shortcut { sequence: "Ctrl+D"; onActivated: Api.ask("demo_start") }
    Shortcut { sequence: "Ctrl+Right"; enabled: vigil.demo.active; onActivated: Api.ask("demo_next") }
    Shortcut { sequence: "Ctrl+."; enabled: vigil.demo.active; onActivated: Api.ask("demo_stop") }
    Shortcut { sequence: "Ctrl+G"; onActivated: win.groundOpen = true }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        TopBar { Layout.fillWidth: true; onMenuRequested: menu.open() }
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Loader {
                id: page
                objectName: "page"
                anchors { fill: parent; margins: 16; leftMargin: Theme.gutter; rightMargin: Theme.gutter; bottomMargin: vigil.demo.active ? 100 : 16 }
                source: win.screens[win.section] || "NotFoundScreen.qml"
            }
        }
    }

    // Demo Director: a guided flow, so it is always easy to skip or stop.
    Rectangle {
        visible: vigil.demo.active
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: 96
        color: Theme.ink
        RowLayout {
            anchors { fill: parent; leftMargin: Theme.gutter; rightMargin: Theme.gutter }
            spacing: 14
            Placard { color: Theme.bg; text: "Demo " + ((vigil.demo.index || 0) + 1) + " of " + vigil.demo.total }
            Text {
                Layout.fillWidth: true
                text: vigil.demo.caption || ""
                wrapMode: Text.WordWrap
                font.family: Theme.body; font.bold: true; font.pixelSize: 24; color: Theme.bg
                Accessible.role: Accessible.StaticText
                Accessible.name: text
            }
            VButton { text: "Next beat"; onClicked: Api.ask("demo_next") }
            VButton { text: "Stop"; onClicked: Api.ask("demo_stop") }
        }
    }

    // Undo: every action on an alert can be taken back for a few seconds, or with Ctrl+Z.
    Rectangle {
        visible: vigil.undoText.length > 0 && !vigil.demo.active
        anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: 110 }
        width: undoRow.implicitWidth + 32
        height: 76
        radius: 4
        color: Theme.panel2
        border.color: Theme.rule
        RowLayout {
            id: undoRow
            anchors.centerIn: parent
            spacing: 18
            Body { text: vigil.undoText; Layout.fillWidth: false }
            VButton { text: "Undo"; onClicked: vigil.undo() }
        }
    }

    Popup {
        id: menu
        objectName: "menu"
        x: parent.width - width
        y: 76
        width: 420
        modal: true
        padding: 16
        background: Rectangle { color: Theme.panel; border.color: Theme.rule }
        ColumnLayout {
            anchors.fill: parent
            spacing: 8
            VButton { Layout.fillWidth: true; kind: "primary"; text: "Play demo"; onClicked: { Api.ask("demo_start"); menu.close() } }
            Repeater {
                model: [["/", "Home"], ["/timeline", "Mission timeline"], ["/explainer", "Why personal baselines"], ["/sensors", "Sensors"], ["/delay", "Delay Theater"], ["/results", "Results"], ["/about", "About and honesty"]]
                VButton {
                    required property var modelData
                    Layout.fillWidth: true
                    text: modelData[1]
                    onClicked: { vigil.navigate(modelData[0]); menu.close() }
                }
            }
            VButton { Layout.fillWidth: true; text: "Open Mission Control"; onClicked: { win.groundOpen = true; menu.close() } }
            Placard { text: "Display" }
            RowLayout {
                Repeater {
                    model: ["dark", "light", "night"]
                    VButton {
                        required property string modelData
                        Layout.fillWidth: true
                        text: modelData
                        selected: vigil.theme === modelData
                        onClicked: vigil.theme = modelData
                    }
                }
            }
            Toggle { text: "Reduce motion"; checked: vigil.reduceMotion; onToggled: vigil.reduceMotion = checked }
        }
    }

    // Say what this software does and does not do, before anything else.
    Popup {
        objectName: "welcome"
        anchors.centerIn: parent
        width: 720
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: !vigil.welcomed && !vigil.demo.active
        padding: 28
        background: Rectangle { color: Theme.panel; border.color: Theme.rule; radius: 4 }
        ColumnLayout {
            anchors.fill: parent
            spacing: 14
            BigTitle { text: "Before you start" }
            Body { text: "Vigil learns your own normal and tells you when something drifts. It explains why, and it decides when to call Earth." }
            Body { text: "Every reading here is simulated. The crew are invented. Thresholds are starting values, not clinical limits. Vigil gives decision support, not a diagnosis." }
            Body { text: "Everything runs on this computer. Vigil opens no network connections. Your journal words are not stored unless you choose to keep them." }
            VButton { Layout.fillWidth: true; kind: "primary"; text: "I understand"; onClicked: vigil.acknowledgeWelcome() }
        }
    }

    // Mission Control opens as its own window, for a second screen.
    Window {
        id: groundWindow
        objectName: "groundWindow"
        title: "Vigil Mission Control"
        width: 1280
        height: 800
        visible: win.groundOpen
        color: Theme.bg
        onClosing: win.groundOpen = false
        Loader {
            anchors { fill: parent; margins: 16 }
            active: groundWindow.visible
            source: "GroundScreen.qml"
            onLoaded: item.standalone = true
        }
    }
}
