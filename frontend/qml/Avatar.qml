import QtQuick

// A plain crew patch: initials in a ring.
Rectangle {
    id: avatar
    property string name: ""
    property string initials: ""
    property int size: 72
    width: size
    height: size
    implicitWidth: size
    implicitHeight: size
    radius: size / 2
    color: Theme.panel2
    border.width: Math.max(2, Math.round(size * 0.035))
    border.color: Theme.ink
    Text {
        anchors.centerIn: parent
        text: avatar.initials.slice(0, 3)
        font.family: Theme.display
        font.weight: Font.ExtraBold
        font.pixelSize: avatar.size * (avatar.initials.length > 2 ? 0.26 : 0.32)
        font.letterSpacing: 0.5
        color: Theme.ink
    }
}
