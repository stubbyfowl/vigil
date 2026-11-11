import QtQuick
import QtQuick.Layouts

// One sentence in two tones: the main point first, then the detail.
Text {
    property string lead: ""
    property string detail: ""
    property int size: 44
    Layout.fillWidth: true
    text: "<font color='" + Theme.ink + "'>" + lead + "</font> <font color='" + Theme.ink2 + "'>" + detail + "</font>"
    textFormat: Text.StyledText
    wrapMode: Text.WordWrap
    font.family: Theme.display
    font.weight: Font.DemiBold
    font.pixelSize: size
    font.letterSpacing: -size * 0.022
    lineHeight: 1.08
    elide: Text.ElideRight
    Accessible.role: Accessible.StaticText
    Accessible.name: lead + " " + detail
}
