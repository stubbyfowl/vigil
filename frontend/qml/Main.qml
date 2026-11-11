import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: win
    property bool kiosk: false
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
        results: "ResultsScreen.qml", about: "AboutScreen.qml", admin: "AdminScreen.qml", profile: "ProfileScreen.qml",
        accounts: "AccountsScreen.qml", audit: "AuditScreen.qml", log: "LogScreen.qml"
    })
    readonly property string section: vigil.route.split("/")[1] || ""
    readonly property bool inApp: vigil.stage === "app"
    readonly property bool crewRole: ["commander", "medical", "crew", "presenter"].indexOf(vigil.role) >= 0
    readonly property bool commands: vigil.role === "commander" || vigil.role === "presenter"
    readonly property var stages: ({ welcome: "WelcomeScreen.qml", setup: "SetupScreen.qml", signin: "SignInScreen.qml" })
    readonly property var links: {
        var out = [["/", "Home"]]
        if (crewRole) {
            out.push(["/checkin", "Check in"])
            if (!vigil.isDemo) out.push(["/log", "Log readings"])
            out.push(["/crew", "Crew"], ["/radiation", "Radiation"], ["/earth", "Call Earth"], ["/sensors", vigil.isDemo ? "Sensors" : "Data sources"])
        }
        if (vigil.role === "ground" || vigil.role === "presenter") out.push(["/ground", "Mission Control"])
        out.push(["/profile", "My account"])
        if (commands) out.push(["/accounts", "Accounts"], ["/audit", "Audit log"], ["/admin", "Thresholds"])
        if (vigil.isDemo) out.push(["/timeline", "Timeline"], ["/explainer", "Baselines explained"], ["/delay", "Delay Theater"], ["/results", "Results"])
        out.push(["/about", "About Vigil"])
        return out
    }

    Backdrop { anchors.fill: parent; decor: !win.inApp }

    // Before anyone signs in: first run, mission setup, or the sign-in screen.
    Loader {
        anchors.fill: parent
        active: !win.inApp
        visible: active
        source: win.stages[vigil.stage] || ""
    }

    Shortcut { sequence: "Ctrl+Z"; enabled: win.inApp; onActivated: vigil.undo() }
    Shortcut { sequence: "Esc"; enabled: win.inApp && !vigil.locked; onActivated: { if (menu.opened) menu.close(); else vigil.back() } }
    Shortcut { sequence: "F11"; onActivated: win.kiosk = !win.kiosk }
    Shortcut { sequence: "Ctrl+L"; enabled: win.inApp; onActivated: vigil.lock() }
    Shortcut { sequence: "Ctrl+D"; enabled: vigil.role === "presenter"; onActivated: Api.ask("demo_start") }
    Shortcut { sequence: "Ctrl+Right"; enabled: vigil.demo.active; onActivated: Api.ask("demo_next") }
    Shortcut { sequence: "Ctrl+."; enabled: vigil.demo.active; onActivated: Api.ask("demo_stop") }
    Shortcut { sequence: "Ctrl+G"; onActivated: vigil.openGround() }

    ColumnLayout {
        anchors.fill: parent
        visible: win.inApp
        spacing: 0
        TopBar { Layout.fillWidth: true; onMenuRequested: menu.open() }
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Loader {
                id: page
                objectName: "page"
                anchors { fill: parent; topMargin: 10; leftMargin: Theme.gutter; rightMargin: Theme.gutter; bottomMargin: vigil.demo.active ? 112 : 18 }
                active: win.inApp
                source: !win.inApp ? "" : !win.crewRole && win.section === "" ? "GroundScreen.qml" : win.screens[win.section] || "NotFoundScreen.qml"
            }
        }
    }

    // Demo Director: a guided flow, so it is always easy to skip or stop.
    Rectangle {
        visible: win.inApp && vigil.demo.active
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom; leftMargin: Theme.gutter; rightMargin: Theme.gutter; bottomMargin: 18 }
        height: 88
        radius: Theme.radius
        color: Theme.panel
        border.width: 1
        border.color: Theme.rule
        Rectangle {
            anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
            width: 4
            color: Theme.urgent
        }
        RowLayout {
            anchors { fill: parent; leftMargin: 32; rightMargin: 14 }
            spacing: 18
            Placard { text: "Demo " + ((vigil.demo.index || 0) + 1) + " / " + vigil.demo.total; font.features: { "tnum": 1 } }
            Text {
                Layout.fillWidth: true
                text: vigil.demo.caption || ""
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                font.family: Theme.body; font.weight: Font.DemiBold; font.pixelSize: 21; font.letterSpacing: -0.2; color: Theme.ink
                Accessible.role: Accessible.StaticText
                Accessible.name: text
            }
            VButton { text: "Next"; onClicked: Api.ask("demo_next") }
            VButton { text: "Stop"; kind: "quiet"; onClicked: Api.ask("demo_stop") }
        }
    }

    // Undo: every action on an alert can be taken back for a few seconds, or with Ctrl+Z.
    Rectangle {
        visible: win.inApp && vigil.undoText.length > 0 && !vigil.demo.active
        anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: 110 }
        width: undoRow.implicitWidth + 32
        height: 76
        radius: Theme.radius
        color: Theme.ink
        RowLayout {
            id: undoRow
            anchors.centerIn: parent
            spacing: 18
            Body { text: vigil.undoText; Layout.fillWidth: false; color: Theme.bg }
            VButton { kind: "primary"; text: "Undo"; onClicked: vigil.undo() }
        }
    }

    Popup {
        id: menu
        objectName: "menu"
        x: parent.width - width - Theme.gutter
        y: 72
        width: 560
        modal: true
        padding: 16
        background: Rectangle { color: Theme.panel; radius: Theme.radius; border.color: Theme.rule; SoftShadow {} }
        ColumnLayout {
            anchors.fill: parent
            spacing: 4
            VButton { visible: vigil.role === "presenter"; Layout.fillWidth: true; kind: "primary"; text: "Play the demo"; onClicked: { Api.ask("demo_start"); menu.close() } }
            GridLayout {
                Layout.fillWidth: true
                columns: 2
                columnSpacing: 4
                rowSpacing: 2
                Repeater {
                    model: win.links
                    VButton {
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        kind: "quiet"
                        textAlign: Text.AlignLeft
                        text: modelData[1]
                        onClicked: { vigil.navigate(modelData[0]); menu.close() }
                    }
                }
            }
            VButton { Layout.fillWidth: true; kind: "quiet"; textAlign: Text.AlignLeft; text: "Open Mission Control window"; onClicked: { vigil.openGround(); menu.close() } }
            Placard { text: "Look" }
            RowLayout {
                Repeater {
                    model: [["dark", "Mission"], ["light", "Daylight"], ["night", "Night"]]
                    VButton {
                        required property var modelData
                        Layout.fillWidth: true
                        text: modelData[1]
                        selected: vigil.theme === modelData[0]
                        onClicked: vigil.theme = modelData[0]
                    }
                }
            }
            Toggle { text: "Reduce motion"; checked: vigil.reduceMotion; onToggled: vigil.reduceMotion = checked }
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                VButton { Layout.fillWidth: true; text: "Lock screen"; onClicked: { menu.close(); vigil.lock() } }
                VButton { Layout.fillWidth: true; text: "Sign out"; onClicked: { menu.close(); vigil.signOut() } }
            }
        }
    }

    // Say what this software does and does not do, before anything else.
    Popup {
        objectName: "welcome"
        anchors.centerIn: parent
        width: 720
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: win.inApp && !vigil.welcomed && !vigil.demo.active && !vigil.locked && !vigil.session.must_change
        padding: 28
        background: Rectangle { color: Theme.panel; radius: Theme.radius; border.color: Theme.rule }
        ColumnLayout {
            anchors.fill: parent
            spacing: 14
            BigTitle { text: "Before you start" }
            Body { text: "Vigil learns each person's usual readings, then measures how far every new day moves from them. When something drifts it says what changed and whether to handle it yourself, tell the Medical Officer, or call Earth." }
            Body { text: (vigil.isDemo ? "Everything in the demo mission is simulated, including the five crew members." : "Readings come from what your crew types in or imports.") + " A flight surgeon has not reviewed the thresholds, and Vigil does not diagnose anything." }
            Body { text: "Nothing leaves this computer except the packets you send to Earth. Journal words are deleted after scoring unless you choose to keep them." }
            VButton { Layout.fillWidth: true; kind: "primary"; text: "Continue"; onClicked: vigil.acknowledgeWelcome() }
        }
    }

    // Locked: everything is hidden until the PIN is entered again.
    LockScreen { anchors.fill: parent; visible: win.inApp && vigil.locked; z: 20 }

    ChangePinDialog { id: forcedPin; required: true }
    Connections {
        target: vigil
        function onSessionChanged() { if (vigil.session.must_change && !forcedPin.opened) forcedPin.open() }
        function onLockedChanged() { if (vigil.locked) menu.close() }
    }
}
