import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: bar
    signal menuRequested
    implicitHeight: 72
    property int taps: 0
    readonly property var crew: vigil.role === "presenter" ? Api.ask("crew", { v: [vigil.version, vigil.mode, vigil.signedIn] }).crew : []
    readonly property bool commands: vigil.role === "commander" || vigil.role === "presenter"
    readonly property bool onHome: vigil.route === "/"
    readonly property bool compact: width < 1240

    Rectangle { anchors.fill: parent; color: Qt.rgba(Theme.bg.r, Theme.bg.g, Theme.bg.b, 0.55); visible: !bar.onHome }
    Rectangle { anchors { left: parent.left; right: parent.right; bottom: parent.bottom } height: 1; color: Theme.rule; visible: !bar.onHome }

    RowLayout {
        anchors { fill: parent; leftMargin: Theme.gutter; rightMargin: Theme.gutter }
        spacing: 8

        AbstractButton {
            implicitWidth: word.implicitWidth + 24
            implicitHeight: Theme.touch
            Accessible.name: "Vigil home"
            Accessible.role: Accessible.Button
            // Five taps open the thresholds screen, for whoever commands.
            onClicked: {
                bar.taps += 1
                if (bar.taps >= 5 && bar.commands) { bar.taps = 0; vigil.navigate("/admin") } else vigil.navigate("/")
            }
            contentItem: Wordmark { id: word; size: 24; verticalAlignment: Text.AlignVCenter }
            background: Item {}
        }

        Repeater {
            model: bar.crew
            AbstractButton {
                id: tab
                required property var modelData
                readonly property bool current: modelData.id === vigil.astronaut
                implicitWidth: Math.max(Theme.touch, name.implicitWidth + (bar.compact ? 12 : 22))
                implicitHeight: Theme.touch
                focusPolicy: Qt.StrongFocus
                Accessible.role: Accessible.Button
                Accessible.name: modelData.name + ", " + modelData.role
                onClicked: vigil.astronaut = modelData.id
                background: Rectangle {
                    anchors { left: parent.left; right: parent.right; bottom: parent.bottom; leftMargin: 11; rightMargin: 11; bottomMargin: 8 }
                    height: 2
                    radius: 1
                    color: Theme.ink
                    visible: tab.current
                }
                contentItem: Text {
                    id: name
                    text: tab.modelData.name.split(" ")[0]
                    font.family: Theme.body
                    font.weight: Font.Medium
                    font.pixelSize: 18
                    color: tab.current || tab.visualFocus ? Theme.ink : Theme.ink2
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }

        AbstractButton {
            visible: vigil.role !== "presenter"
            implicitWidth: me.implicitWidth + 16
            implicitHeight: Theme.touch
            focusPolicy: Qt.StrongFocus
            Accessible.role: Accessible.Button
            Accessible.name: "Signed in as " + (vigil.session.name || "") + ". Open your account."
            onClicked: vigil.navigate("/profile")
            background: Item {}
            contentItem: RowLayout {
                id: me
                spacing: 10
                Avatar { size: 36; name: vigil.session.name || ""; initials: vigil.session.tag || "" }
                Text { text: (vigil.session.name || "").split(" ")[0]; font.family: Theme.display; font.weight: Font.DemiBold; font.pixelSize: 17; color: Theme.ink }
                Note { visible: !bar.compact; Layout.fillWidth: false; text: vigil.session.role_name || "" }
            }
        }

        Item { Layout.fillWidth: true }

        // Plain labels, so nothing that only informs looks like a button.
        Placard { visible: vigil.isDemo; text: "Simulated data"; color: Theme.caution; objectName: "simulated" }
        Placard {
            visible: !bar.compact || !vigil.linkUp
            Layout.leftMargin: 18
            text: vigil.isDemo ? (vigil.linkUp ? "Link up" : "Link lost") + " · " + vigil.delayMinutes + " min" : "Earth · " + vigil.delayMinutes + " min"
            color: vigil.linkUp ? Theme.ink2 : Theme.warning
        }

        // In the demo the day opens the timeline. In a real mission it is a label.
        AbstractButton {
            visible: vigil.isDemo
            Layout.leftMargin: 10
            implicitWidth: dayText.implicitWidth + 20
            implicitHeight: Theme.touch
            focusPolicy: Qt.StrongFocus
            Accessible.name: "Mission day " + vigil.day + " of " + vigil.missionDays + ". Open the timeline."
            Accessible.role: Accessible.Button
            onClicked: vigil.navigate("/timeline")
            background: Item {}
            contentItem: Text {
                id: dayText
                text: "Day " + vigil.day + " / " + vigil.missionDays
                font.family: Theme.display; font.weight: Font.DemiBold; font.pixelSize: 18; font.features: { "tnum": 1 }
                font.underline: parent.hovered
                color: Theme.ink
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }
        Text {
            visible: !vigil.isDemo
            Layout.leftMargin: 10
            text: "Day " + vigil.day + " / " + vigil.missionDays
            font.family: Theme.display; font.weight: Font.DemiBold; font.pixelSize: 18; font.features: { "tnum": 1 }
            color: Theme.ink
        }

        VButton { text: "Lock"; Accessible.name: "Lock the screen"; onClicked: vigil.lock() }
        VButton { text: "Menu"; onClicked: bar.menuRequested() }
    }
}
