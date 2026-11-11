import QtQuick
import QtQuick.Layouts

// A message box for things that stay on screen, after Wikipedia's notices: a colored edge, an icon and words.
Rectangle {
    id: banner
    property string tone: "info"   // info, success, caution, error
    property string text: ""
    property string action: ""
    signal actionClicked
    readonly property string status: tone === "success" ? "green" : tone === "caution" ? "yellow" : tone === "error" ? "red" : ""
    readonly property color edge: status ? Theme.statusColor(status) : Theme.link
    Layout.fillWidth: true
    visible: text.length > 0
    radius: 2
    color: Theme.panel2
    border.color: Theme.rule
    implicitHeight: Math.max(Theme.touch, row.implicitHeight + 20)
    Accessible.role: Accessible.AlertMessage
    Accessible.name: text

    Rectangle { anchors { left: parent.left; top: parent.top; bottom: parent.bottom } width: 4; color: banner.edge }
    RowLayout {
        id: row
        anchors { fill: parent; leftMargin: 18; rightMargin: 8 }
        spacing: 12
        StatusIcon { visible: banner.status.length > 0; status: banner.status; tint: banner.edge }
        Text { visible: !banner.status; text: "i"; font.family: Theme.display; font.weight: Font.ExtraBold; font.pixelSize: 17; color: banner.edge }
        Body { text: banner.text; Layout.fillWidth: true }
        VButton { visible: banner.action.length > 0; text: banner.action; kind: "quiet"; onClicked: banner.actionClicked() }
    }
}
