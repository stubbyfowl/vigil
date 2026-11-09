import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: bar
    signal menuRequested
    implicitHeight: 72
    property int taps: 0
    readonly property var crew: Api.ask("crew", {}).crew
    readonly property bool onHome: vigil.route === "/"

    Rectangle { anchors.fill: parent; color: Theme.bg; visible: !bar.onHome }
    Rectangle { anchors { left: parent.left; right: parent.right; bottom: parent.bottom } height: 1; color: Theme.rule; visible: !bar.onHome }

    RowLayout {
        anchors { fill: parent; leftMargin: Theme.gutter; rightMargin: Theme.gutter }
        spacing: 8

        AbstractButton {
            implicitWidth: word.implicitWidth + 24
            implicitHeight: Theme.touch
            Accessible.name: "Vigil home"
            Accessible.role: Accessible.Button
            // Five taps open the hidden Admin screen.
            onClicked: {
                bar.taps += 1
                if (bar.taps >= 5) { bar.taps = 0; vigil.navigate("/admin") } else vigil.navigate("/")
            }
            contentItem: Text { id: word; text: "Vigil"; font.family: Theme.body; font.weight: Font.DemiBold; font.pixelSize: 28; font.letterSpacing: -0.9; color: Theme.ink; verticalAlignment: Text.AlignVCenter }
            background: Item {}
        }

        Repeater {
            model: bar.crew
            AbstractButton {
                id: tab
                required property var modelData
                readonly property bool current: modelData.id === vigil.astronaut
                implicitWidth: Math.max(Theme.touch, name.implicitWidth + 22)
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

        Item { Layout.fillWidth: true }

        Rectangle {
            implicitWidth: badge.implicitWidth + 24
            implicitHeight: 34
            radius: 17
            color: Theme.cautionBg
            Text { id: badge; anchors.centerIn: parent; text: "Simulated data"; color: Theme.caution; font.family: Theme.body; font.weight: Font.Medium; font.pixelSize: 16 }
        }

        Text {
            Layout.leftMargin: 8
            text: (vigil.linkUp ? "Link up" : "Link lost") + ", " + vigil.delayMinutes + " min"
            font.family: Theme.body; font.pixelSize: 16; color: vigil.linkUp ? Theme.ink2 : Theme.warning
        }

        AbstractButton {
            implicitWidth: dayText.implicitWidth + 20
            implicitHeight: Theme.touch
            focusPolicy: Qt.StrongFocus
            Accessible.name: "Mission day " + vigil.day + " of " + vigil.missionDays + ". Open mission timeline."
            Accessible.role: Accessible.Button
            onClicked: vigil.navigate("/timeline")
            background: Item {}
            contentItem: Text {
                id: dayText
                text: "Day " + vigil.day + " of " + vigil.missionDays
                font.family: Theme.body; font.weight: Font.Medium; font.pixelSize: 18; font.features: { "tnum": 1 }
                color: Theme.ink
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }

        VButton { text: "Menu"; onClicked: bar.menuRequested() }
    }
}
