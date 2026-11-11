import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// A keypad sized for gloves. Keyboard digits, Backspace and Enter work too.
FocusScope {
    id: pad
    property string pin: ""
    property int minLength: 4
    property int maxLength: 8
    property string error: ""
    property string submitText: "Sign in"
    signal submitted(string pin)
    implicitWidth: 3 * 92 + 2 * 12
    implicitHeight: column.implicitHeight
    focus: true

    function press(key) {
        error = ""
        if (key === "back") pin = pin.slice(0, -1)
        else if (key === "clear") pin = ""
        else if (pin.length < maxLength) pin += key
    }
    function submit() {
        if (pin.length >= minLength) { var typed = pin; pin = ""; submitted(typed) }
    }

    Keys.onPressed: function (event) {
        if (event.text.length === 1 && event.text >= "0" && event.text <= "9") { press(event.text); event.accepted = true }
        else if (event.key === Qt.Key_Backspace) { press("back"); event.accepted = true }
        else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) { submit(); event.accepted = true }
    }

    ColumnLayout {
        id: column
        anchors.fill: parent
        spacing: 12
        Row {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredHeight: 28
            spacing: 14
            Accessible.role: Accessible.StaticText
            Accessible.name: pad.pin.length + " digits entered"
            Repeater {
                model: Math.max(pad.minLength, pad.pin.length)
                Rectangle {
                    required property int index
                    width: 16; height: 16; radius: 8
                    anchors.verticalCenter: parent.verticalCenter
                    color: index < pad.pin.length ? Theme.ink : "transparent"
                    border.color: Theme.ink2
                    border.width: 2
                }
            }
        }
        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            visible: pad.error.length > 0
            spacing: 8
            StatusIcon { status: "red"; tint: Theme.warning }
            Note { text: pad.error; color: Theme.warning; Layout.maximumWidth: pad.implicitWidth - 30 }
        }
        GridLayout {
            Layout.alignment: Qt.AlignHCenter
            columns: 3
            rowSpacing: 12
            columnSpacing: 12
            Repeater {
                model: ["1", "2", "3", "4", "5", "6", "7", "8", "9", "clear", "0", "back"]
                VButton {
                    required property string modelData
                    implicitWidth: 92
                    implicitHeight: 64
                    textSize: modelData.length === 1 ? 26 : 17
                    kind: modelData.length === 1 ? "normal" : "quiet"
                    text: modelData === "back" ? "Delete" : modelData === "clear" ? "Clear" : modelData
                    focusPolicy: Qt.NoFocus
                    onClicked: pad.press(modelData)
                }
            }
        }
        VButton {
            Layout.fillWidth: true
            kind: "primary"
            text: pad.submitText
            enabled: pad.pin.length >= pad.minLength
            focusPolicy: Qt.NoFocus
            onClicked: pad.submit()
        }
    }
}
