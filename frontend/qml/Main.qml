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
        accounts: "AccountsScreen.qml", audit: "AuditScreen.qml", log: "LogScreen.qml",
        chat: "ChatScreen.qml", replay: "ReplayScreen.qml", album: "AlbumScreen.qml", gut: "GutCityScreen.qml"
    })
    readonly property string section: vigil.route.split("/")[1] || ""
    readonly property bool inApp: vigil.stage === "app"
    readonly property bool crewRole: ["commander", "medical", "crew", "presenter"].indexOf(vigil.role) >= 0
    readonly property bool commands: vigil.role === "commander" || vigil.role === "presenter"
    readonly property var stages: ({ welcome: "WelcomeScreen.qml", setup: "SetupScreen.qml", signin: "SignInScreen.qml" })
    // The Menu, grouped by body area and by task, so every view sits next to the readings it comes from.
    readonly property var sections: {
        var out = []
        if (crewRole) {
            var today = [["/", "Home"], ["/checkin", "Check in"]]
            if (!vigil.isDemo) today.push(["/log", "Log readings"])
            today.push(["/chat", "Organ chat"], ["/earth", "Call Earth"])
            out.push({ title: "Today", items: today })
            out.push({ title: "Heart", items: [["/system/heart", "Heart readings"], ["/album", "Heart rate album"]] })
            out.push({ title: "Immune", items: [["/system/immune", "Immune readings"], ["/replay", "Immune replay"]] })
            out.push({ title: "Bone and muscle", items: [["/system/bone", "Bone and muscle readings"]] })
            out.push({ title: "Behavior and food", items: [["/system/behavior", "Behavior readings"], ["/gut", "Gut City"], ["/chat/future", "Texts from you at 70"]] })
            out.push({ title: "Radiation and crew", items: [["/radiation", "Radiation"], ["/crew", "Crew"], ["/sensors", vigil.isDemo ? "Sensors" : "Data sources"]] })
        } else {
            out.push({ title: "Today", items: [["/", "Home"]] })
        }
        if (vigil.role === "ground" || vigil.role === "presenter") out.push({ title: "Earth", items: [["/ground", "Mission Control"]] })
        if (vigil.isDemo) out.push({ title: "Demo and results", items: [["/timeline", "Timeline"], ["/explainer", "Baselines explained"], ["/delay", "Delay Theater"], ["/results", "Results"]] })
        if (commands) out.push({ title: "Commander", items: [["/accounts", "Accounts"], ["/audit", "Audit log"], ["/admin", "Thresholds"]] })
        out.push({ title: "You", items: [["/profile", "My account"], ["/about", "About Vigil"]] })
        return out
    }
    readonly property var links: [].concat.apply([], sections.map(function (s) { return s.items }))
    readonly property var zoomSteps: [1.0, 1.15, 1.3]
    function zoomBy(step) {
        var i = zoomSteps.indexOf(vigil.zoom)
        vigil.zoom = zoomSteps[Math.max(0, Math.min(zoomSteps.length - 1, (i < 0 ? 0 : i) + step))]
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
    Shortcut { sequences: [StandardKey.ZoomIn, "Ctrl+="]; enabled: win.inApp; onActivated: win.zoomBy(1) }
    Shortcut { sequences: [StandardKey.ZoomOut]; enabled: win.inApp; onActivated: win.zoomBy(-1) }
    Shortcut { sequence: "Ctrl+0"; enabled: win.inApp; onActivated: vigil.zoom = 1.0 }

    ColumnLayout {
        anchors.fill: parent
        visible: win.inApp
        spacing: 0
        TopBar { Layout.fillWidth: true; onMenuRequested: menu.open() }
        Item {
            id: pageArea
            Layout.fillWidth: true
            Layout.fillHeight: true
            // Larger text scales the whole page and lets it reflow into the narrower space, like zoom in a browser.
            Loader {
                id: page
                objectName: "page"
                x: Theme.gutter
                y: 10
                width: (pageArea.width - 2 * Theme.gutter) / vigil.zoom
                height: (pageArea.height - 10 - (vigil.demo.active ? 112 : 18)) / vigil.zoom
                scale: vigil.zoom
                transformOrigin: Item.TopLeft
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
        width: Math.min(720, win.width - 2 * Theme.gutter)
        modal: true
        padding: 16
        // A short window scrolls the menu instead of cutting off the bottom items.
        height: Math.min(implicitHeight, win.height - y - 16)
        background: Rectangle { color: Theme.panel; radius: Theme.radius; border.color: Theme.rule; SoftShadow {} }
        contentItem: Flickable {
            id: menuFlick
            clip: true
            implicitHeight: menuColumn.implicitHeight
            contentHeight: menuColumn.implicitHeight
            boundsBehavior: Flickable.StopAtBounds
            readonly property bool scrolls: menuColumn.implicitHeight > height + 1
            ScrollBar.vertical: ScrollBar { policy: menuFlick.scrolls ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff }
        ColumnLayout {
            id: menuColumn
            width: menuFlick.width - (menuFlick.scrolls ? 18 : 0)
            spacing: 4
            VButton { visible: vigil.role === "presenter"; Layout.fillWidth: true; kind: "primary"; text: "Play the demo"; onClicked: { Api.ask("demo_start"); menu.close() } }
            Repeater {
                model: win.sections
                ColumnLayout {
                    id: group
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: 0
                    Placard { text: group.modelData.title; Layout.topMargin: 8; Layout.leftMargin: 12 }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 3
                        columnSpacing: 4
                        rowSpacing: 0
                        Repeater {
                            model: group.modelData.items
                            VButton {
                                required property var modelData
                                Layout.fillWidth: true
                                Layout.preferredWidth: 1
                                kind: "quiet"
                                textAlign: Text.AlignLeft
                                text: modelData[1]
                                selected: vigil.route === modelData[0]
                                onClicked: { vigil.navigate(modelData[0]); menu.close() }
                            }
                        }
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
            Placard { text: "Text size" }
            RowLayout {
                Repeater {
                    model: [[1.0, "Standard"], [1.15, "Large"], [1.3, "Largest"]]
                    VButton {
                        required property var modelData
                        Layout.fillWidth: true
                        text: modelData[1]
                        selected: vigil.zoom === modelData[0]
                        Accessible.name: "Text size " + modelData[1]
                        onClicked: vigil.zoom = modelData[0]
                    }
                }
            }
            Toggle { text: "Reduce motion"; checked: vigil.reduceMotion; onToggled: vigil.reduceMotion = checked }
            Toggle { text: "Documentary narrator"; checked: vigil.narrator; onToggled: vigil.narrator = checked }
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                VButton { Layout.fillWidth: true; text: "Lock screen"; onClicked: { menu.close(); vigil.lock() } }
                VButton { Layout.fillWidth: true; text: "Sign out"; onClicked: { menu.close(); vigil.signOut() } }
            }
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
        // The PIN box follows the session: it closes on sign-out or lock, so the next person never sees it.
        function onSessionChanged() { win.syncPinBox() }
        function onLockedChanged() { if (vigil.locked) menu.close(); win.syncPinBox() }
    }
    function syncPinBox() {
        if (vigil.signedIn && !vigil.locked && vigil.session.must_change) { if (!forcedPin.opened) forcedPin.open() }
        else if (forcedPin.opened) forcedPin.close()
    }
}
