import QtQuick

// Initials in a circle. The same person gets the same tint everywhere.
Rectangle {
    id: avatar
    property string name: ""
    property string initials: ""
    property int size: 72
    readonly property var tints: [Theme.action, Theme.nominal, Theme.caution, Theme.flag, Theme.ink2]
    width: size
    height: size
    radius: size / 2
    color: Theme.panel2
    border.width: 2
    border.color: tints[Math.abs(name.split("").reduce(function (h, c) { return (h * 31 + c.charCodeAt(0)) | 0 }, 7)) % tints.length]
    Text {
        anchors.centerIn: parent
        text: avatar.initials.slice(0, 3)
        font.family: Theme.body
        font.weight: Font.DemiBold
        font.pixelSize: avatar.size * 0.34
        color: Theme.ink
    }
}
