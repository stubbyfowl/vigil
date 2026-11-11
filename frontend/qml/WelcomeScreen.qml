import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// First run on this computer: start a real mission, or look around the demo.
Item {
    objectName: "welcomeStage"
    ColumnLayout {
        anchors { fill: parent; margins: Theme.gutter; topMargin: 56 }
        spacing: 18
        Text { text: "Vigil"; font.family: Theme.body; font.weight: Font.DemiBold; font.pixelSize: 28; font.letterSpacing: -0.9; color: Theme.ink }
        Statement {
            Layout.maximumWidth: 900
            size: 52
            lead: "Your own normal, watched every day."
            detail: "Vigil learns each crew member's baseline, spots drift across many signals, and decides when to call Earth."
        }
        RowLayout {
            Layout.topMargin: 24
            Layout.fillWidth: true
            spacing: 18
            Repeater {
                model: [
                    { title: "Set up a mission", body: "Create the mission, then add each crew member with their own PIN. Readings you enter stay on this computer.", action: "Set up", primary: true },
                    { title: "Explore the demo", body: "A 180-day mission with five simulated crew and planted health events. Nothing you do there touches a real mission.", action: "Open the demo", primary: false }
                ]
                Panel {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    surface: true
                    Text { text: modelData.title; font.family: Theme.body; font.weight: Font.Medium; font.pixelSize: 28; font.letterSpacing: -0.6; color: Theme.ink }
                    Body { text: modelData.body; color: Theme.ink2 }
                    VButton {
                        Layout.topMargin: 8
                        kind: modelData.primary ? "primary" : "normal"
                        text: modelData.action
                        onClicked: modelData.primary ? vigil.startSetup() : vigil.chooseDemo()
                    }
                }
            }
        }
        Item { Layout.fillHeight: true }
        Note { text: "Vigil gives decision support, not a diagnosis. It opens no network connections." }
    }
}
