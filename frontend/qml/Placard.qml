import QtQuick

// A label in the style of nasa.gov: small monospaced capitals with wide spacing.
Text {
    font.family: Theme.mono
    font.weight: Font.Medium
    font.pixelSize: 13
    font.letterSpacing: 2.4
    font.capitalization: Font.AllUppercase
    color: Theme.ink2
}
