import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Rectangle {
    id: bar
    signal menuRequested
    color: Theme.panel
    implicitHeight: 76
    property int taps: 0
    readonly property var crew: Api.ask("crew", {}).crew

    Rectangle { anchors { left: parent.left; right: parent.right; bottom: parent.bottom } height: 1; color: Theme.rule }

    RowLayout {
        anchors { fill: parent; leftMargin: Theme.gutter; rightMargin: Theme.gutter }
        spacing: 10

        AbstractButton {
            implicitWidth: word.implicitWidth + 10
            implicitHeight: Theme.touch
            Accessible.name: "Vigil home"
            Accessible.role: Accessible.Button
            // Five taps open the hidden Admin screen.
            onClicked: {
                bar.taps += 1
                if (bar.taps >= 5) { bar.taps = 0; vigil.navigate("/admin") } else vigil.navigate("/")
            }
            contentItem: Text { id: word; text: "VIGIL"; font.family: Theme.label; font.pixelSize: 32; font.letterSpacing: 7.7; color: Theme.ink; verticalAlignment: Text.AlignVCenter }
            background: Item {}
        }

        Row {
            spacing: 4
            Repeater {
                model: bar.crew
                VButton {
                    required property var modelData
                    text: modelData.tag
                    selected: modelData.id === vigil.astronaut
                    implicitWidth: Math.max(Theme.touch, contentItem.implicitWidth + 20)
                    Accessible.name: modelData.name
                    onClicked: vigil.astronaut = modelData.id
                }
            }
        }

        Item { Layout.fillWidth: true }

        Rectangle {
            implicitWidth: badge.implicitWidth + 20
            implicitHeight: 36
            color: "transparent"
            border.color: Theme.caution
            border.width: 2
            Placard { id: badge; anchors.centerIn: parent; text: "Simulated data"; color: Theme.caution; font.pixelSize: 18 }
        }

        Column {
            Placard { text: vigil.linkUp ? "Link up" : "Link lost"; color: Theme.ink; font.pixelSize: 18 }
            Placard { text: vigil.delayMinutes + " min delay"; font.pixelSize: 18 }
        }

        AbstractButton {
            implicitWidth: dayColumn.implicitWidth + 16
            implicitHeight: Theme.touch
            Accessible.name: "Mission day " + vigil.day + " of " + vigil.missionDays + ". Open mission timeline."
            Accessible.role: Accessible.Button
            onClicked: vigil.navigate("/timeline")
            background: Item {}
            contentItem: Column {
                id: dayColumn
                Placard { anchors.right: parent.right; text: "Mission day"; font.pixelSize: 17 }
                Text {
                    anchors.right: parent.right
                    text: String(vigil.day).padStart(3, "0") + "/" + vigil.missionDays
                    font.family: Theme.mono; font.bold: true; font.pixelSize: 28; color: Theme.ink
                }
            }
        }

        VButton { text: "Menu"; onClicked: bar.menuRequested() }
    }
}
