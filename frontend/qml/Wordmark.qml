import QtQuick

// The name, set like a mission title.
Text {
    property int size: 26
    text: "VIGIL"
    font.family: Theme.display
    font.weight: Font.ExtraBold
    font.pixelSize: size
    font.letterSpacing: size * 0.12
    color: Theme.ink
    Accessible.name: "Vigil"
}
