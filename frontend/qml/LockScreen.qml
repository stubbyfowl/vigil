import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// The screen locks when nobody touches it for a while. Data stays hidden until the PIN is entered again.
Rectangle {
    id: lockScreen
    objectName: "lock"
    color: Theme.bg
    MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons; onClicked: pad.forceActiveFocus() }
    onVisibleChanged: if (visible) { pad.pin = ""; pad.error = ""; pad.forceActiveFocus() }

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 16
        Placard { Layout.alignment: Qt.AlignHCenter; text: "Locked" }
        Avatar { Layout.alignment: Qt.AlignHCenter; size: 84; name: vigil.session.name || ""; initials: vigil.session.tag || "" }
        Text { Layout.alignment: Qt.AlignHCenter; text: vigil.session.name || ""; font.family: Theme.body; font.weight: Font.Medium; font.pixelSize: 26; color: Theme.ink }
        PinPad {
            id: pad
            Layout.alignment: Qt.AlignHCenter
            submitText: "Unlock"
            onSubmitted: function (pin) { pad.error = vigil.unlock(pin) }
        }
        VButton { Layout.alignment: Qt.AlignHCenter; kind: "quiet"; text: "Sign out"; onClicked: vigil.signOut() }
    }
}
