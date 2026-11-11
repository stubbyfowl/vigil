import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// A form field: label above, input, then help or an error attached underneath.
ColumnLayout {
    id: field
    property string label: ""
    property alias text: input.text
    property alias input: input
    property string placeholder: ""
    property string helper: ""
    property string error: ""
    property bool secret: false
    property bool digits: false
    property int maxLength: 80
    signal accepted
    spacing: 6
    Layout.fillWidth: true

    Text { text: field.label; font.family: Theme.body; font.weight: Font.DemiBold; font.pixelSize: 16; color: Theme.ink; visible: text.length > 0 }
    TextField {
        id: input
        Layout.fillWidth: true
        implicitHeight: Theme.touch
        placeholderText: field.placeholder
        placeholderTextColor: Theme.ink2
        maximumLength: field.maxLength
        echoMode: field.secret ? TextInput.Password : TextInput.Normal
        inputMethodHints: field.digits ? Qt.ImhDigitsOnly : Qt.ImhNone
        validator: field.digits ? digitsOnly : null
        font.family: Theme.body
        font.pixelSize: 19
        color: Theme.ink
        leftPadding: 14
        Accessible.name: field.label
        Accessible.description: field.error || field.helper
        onAccepted: field.accepted()
        background: Rectangle {
            radius: Theme.controlRadius
            color: Theme.panel2
            border.width: input.activeFocus || field.error ? 2 : 1
            border.color: field.error ? Theme.warning : input.activeFocus ? Theme.link : Theme.rule
        }
    }
    RegularExpressionValidator { id: digitsOnly; regularExpression: /[0-9]*/ }
    RowLayout {
        visible: field.error.length > 0 || field.helper.length > 0
        spacing: 8
        StatusIcon { visible: field.error.length > 0; status: "red"; tint: Theme.warning; Layout.alignment: Qt.AlignTop; Layout.topMargin: 3 }
        Note { text: field.error || field.helper; color: field.error ? Theme.warning : Theme.ink2 }
    }
}
