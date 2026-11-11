import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Choose a new PIN. Required on first sign-in and after the Commander resets one.
Popup {
    id: dialog
    objectName: "changePin"
    property bool required: false
    property string message: ""
    anchors.centerIn: Overlay.overlay
    width: 520
    modal: true
    closePolicy: required ? Popup.NoAutoClose : Popup.CloseOnEscape | Popup.CloseOnPressOutside
    padding: 28
    background: Rectangle { color: Theme.panel; radius: Theme.radius; border.color: Theme.rule }
    onOpened: { current.text = ""; fresh.text = ""; again.text = ""; message = ""; current.input.forceActiveFocus() }

    function save() {
        if (fresh.text !== again.text) { message = "The two new PINs do not match."; return }
        message = vigil.changePin(current.text, fresh.text)
        if (!message) close()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 14
        BigTitle { text: dialog.required ? "Choose your own PIN" : "Change PIN"; font.pixelSize: 32 }
        Body { visible: dialog.required; color: Theme.ink2; text: "You signed in with a temporary PIN. Pick one only you know." }
        Field { id: current; label: dialog.required ? "Temporary PIN" : "Current PIN"; secret: true; digits: true; maxLength: 8 }
        Field { id: fresh; label: "New PIN"; secret: true; digits: true; maxLength: 8; helper: "4 to 8 digits. Not 1234, not all the same digit." }
        Field { id: again; label: "New PIN again"; secret: true; digits: true; maxLength: 8; onAccepted: dialog.save() }
        Banner { tone: "error"; text: dialog.message }
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            VButton { visible: !dialog.required; text: "Cancel"; onClicked: dialog.close() }
            VButton { visible: dialog.required; kind: "quiet"; text: "Sign out"; onClicked: { dialog.close(); vigil.signOut() } }
            Item { Layout.fillWidth: true }
            VButton { kind: "primary"; text: "Save PIN"; onClicked: dialog.save() }
        }
    }
}
